"""
REST API ViewSets for document library.
"""
import os
import tempfile
from datetime import timedelta
from django.utils import timezone
from django.http import FileResponse, HttpResponse
from django.db.models import Q, Count, Sum
from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import (
    DocumentCategory,
    DocumentTag,
    Document,
    DocumentShareLog,
    UserStorageQuota,
    CompressionStats,
)
from .serializers import (
    DocumentCategorySerializer,
    DocumentTagSerializer,
    DocumentListSerializer,
    DocumentDetailSerializer,
    DocumentUploadSerializer,
    DocumentShareLogSerializer,
    ShareDocumentSerializer,
    UserStorageQuotaSerializer,
    CompressionStatsSerializer,
    BulkOperationSerializer,
    FolderTreeSerializer,
    BreadcrumbSerializer,
    FolderContentsSerializer,
    BulkMoveSerializer,
)
from .tasks import (
    compress_document_task,
    bulk_compress_documents_task,
    send_email_share_task,
    decompress_document_task,
    recalculate_user_quota,
)
from .utils.compression import decompress_file


class DocumentCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing document categories.

    list: Get all categories for current user
    create: Create a new category
    retrieve: Get a specific category
    update: Update a category
    destroy: Delete a category (documents will be uncategorized)
    """

    serializer_class = DocumentCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'document_count']
    ordering = ['name']

    def get_queryset(self):
        """Return categories for current user only"""
        return DocumentCategory.objects.filter(
            user=self.request.user
        ).annotate(
            document_count=Count('documents')
        )

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """
        Get hierarchical folder tree for current user.
        GET /api/v1/documents/categories/tree/
        Query params:
          - expand=true: Expand all nested levels
        """
        # Get root folders (those without a parent)
        root_folders = self.get_queryset().filter(parent=None).annotate(
            subfolder_count=Count('subfolders')
        )

        serializer = FolderTreeSerializer(
            root_folders,
            many=True,
            context={'request': request}
        )

        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def contents(self, request, pk=None):
        """
        Get combined contents (subfolders + documents) for a folder.
        GET /api/v1/documents/categories/{id}/contents/
        """
        folder = self.get_object()

        # Get subfolders with counts
        subfolders = folder.subfolders.annotate(
            document_count=Count('documents'),
            subfolder_count=Count('subfolders')
        )

        # Get documents in this folder
        documents = Document.objects.filter(
            user=request.user,
            category=folder
        ).select_related('category').prefetch_related('tags')

        # Get breadcrumbs
        breadcrumbs = folder.breadcrumbs

        # Build response
        data = {
            'folder': DocumentCategorySerializer(folder).data,
            'breadcrumbs': BreadcrumbSerializer(breadcrumbs, many=True).data,
            'subfolders': DocumentCategorySerializer(subfolders, many=True).data,
            'documents': DocumentListSerializer(documents, many=True).data,
            'total_items': subfolders.count() + documents.count()
        }

        return Response(data)

    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        """
        Move a folder to a new parent.
        POST /api/v1/documents/categories/{id}/move/
        Body: {"target_folder_id": "uuid" or null}
        """
        folder = self.get_object()
        target_folder_id = request.data.get('target_folder_id')

        # Get target folder if specified
        target_folder = None
        if target_folder_id:
            try:
                target_folder = DocumentCategory.objects.get(
                    id=target_folder_id,
                    user=request.user
                )
            except DocumentCategory.DoesNotExist:
                return Response(
                    {'error': 'Target folder not found or does not belong to you'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Validate move (prevent circular references)
        if not folder.can_move_to(target_folder):
            return Response(
                {'error': 'Cannot move folder into itself or its descendants'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Perform move
        folder.parent = target_folder
        folder.save()

        return Response({
            'message': 'Folder moved successfully',
            'folder': DocumentCategorySerializer(folder).data
        })


class DocumentTagViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing document tags.

    list: Get all tags for current user
    create: Create a new tag
    retrieve: Get a specific tag
    update: Update a tag
    destroy: Delete a tag
    autocomplete: Autocomplete tag names
    """

    serializer_class = DocumentTagSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at', 'document_count']
    ordering = ['name']

    def get_queryset(self):
        """Return tags for current user only"""
        return DocumentTag.objects.filter(
            user=self.request.user
        ).annotate(
            document_count=Count('documents')
        )

    @action(detail=False, methods=['get'])
    def autocomplete(self, request):
        """
        Autocomplete tag names.
        GET /api/documents/tags/autocomplete/?q=import
        """
        query = request.query_params.get('q', '')
        if not query:
            return Response([])

        tags = self.get_queryset().filter(name__icontains=query)[:10]
        serializer = self.get_serializer(tags, many=True)
        return Response(serializer.data)


class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing documents.

    list: Get all documents for current user
    create: Upload a new document
    retrieve: Get a specific document
    update: Update document metadata
    destroy: Delete a document
    download: Download a document (with decompression)
    preview: Get document preview
    toggle_favorite: Toggle favorite status
    share_email: Share document via email
    share_whatsapp: Share document via WhatsApp
    generate_share_link: Generate public share link
    revoke_share: Revoke public sharing
    share_history: Get sharing history
    bulk_operations: Perform bulk operations
    compression_status: Get compression status
    """

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['file_type', 'category', 'is_favorite', 'compression_status', 'is_compressed']
    search_fields = ['title', 'description', 'file_original_name']
    ordering_fields = ['upload_date', 'title', 'original_file_size', 'download_count']
    ordering = ['-upload_date']

    def get_queryset(self):
        """Return documents for current user only"""
        return Document.objects.filter(
            user=self.request.user
        ).select_related('category').prefetch_related('tags')

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return DocumentUploadSerializer
        elif self.action == 'list':
            return DocumentListSerializer
        else:
            return DocumentDetailSerializer

    def create(self, request, *args, **kwargs):
        """Override create to add better error logging."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.debug(f"Document upload request - FILES: {request.FILES}")
        logger.debug(f"Document upload request - DATA: {request.data}")
        
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Document upload validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Download a document (with automatic decompression).
        GET /api/documents/{id}/download/
        """
        document = self.get_object()

        # Increment download count
        document.increment_download_count()

        # Check if document is compressed
        if document.is_compressed and document.compression_algorithm != 'none':
            # Create temp file for decompressed version
            temp_dir = settings.DECOMPRESSION_TEMP_DIR
            os.makedirs(temp_dir, exist_ok=True)

            temp_path = os.path.join(
                temp_dir,
                f"{document.id}_{document.file_original_name}"
            )

            try:
                # Decompress file
                decompress_file(
                    input_path=document.file.path,
                    output_path=temp_path,
                    algorithm=document.compression_algorithm
                )

                # Serve decompressed file
                response = FileResponse(
                    open(temp_path, 'rb'),
                    as_attachment=True,
                    filename=document.file_original_name
                )
                response['X-Original-Size'] = document.original_file_size
                response['X-Compressed'] = 'true'
                response['X-Compression-Algorithm'] = document.compression_algorithm

                return response

            except Exception as e:
                return Response(
                    {'error': f'Decompression failed: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            # Serve file directly
            response = FileResponse(
                document.file.open('rb'),
                as_attachment=True,
                filename=document.file_original_name
            )
            return response

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """
        Get document preview information.
        GET /api/documents/{id}/preview/
        """
        document = self.get_object()
        document.increment_view_count()

        preview_data = {
            'id': str(document.id),
            'title': document.title,
            'file_type': document.file_type,
            'is_image': document.file_type in ['png', 'jpg', 'jpeg', 'gif'],
            'is_pdf': document.file_type == 'pdf',
            'is_text': document.file_type in ['txt', 'csv'],
        }

        # Add preview URL for images
        if preview_data['is_image']:
            preview_data['preview_url'] = request.build_absolute_uri(document.file.url)

        return Response(preview_data)

    @action(detail=True, methods=['post'])
    def toggle_favorite(self, request, pk=None):
        """
        Toggle favorite status.
        POST /api/documents/{id}/toggle_favorite/
        """
        document = self.get_object()
        document.is_favorite = not document.is_favorite
        document.save(update_fields=['is_favorite'])

        return Response({
            'id': str(document.id),
            'is_favorite': document.is_favorite
        })

    @action(detail=True, methods=['post'])
    def share_email(self, request, pk=None):
        """
        Share document via email.
        POST /api/documents/{id}/share_email/
        Body: {"recipients": ["email@example.com"], "message": "...", "expiry_days": 7}
        """
        document = self.get_object()
        serializer = ShareDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        recipients = data.get('recipients', [])
        expiry_days = data.get('expiry_days', 7)
        message = data.get('message', '')

        expiry_date = timezone.now() + timedelta(days=expiry_days)

        # Create share logs and send emails
        share_logs = []
        for recipient in recipients:
            share_log = DocumentShareLog.objects.create(
                document=document,
                shared_by=request.user,
                share_method='email',
                recipient=recipient,
                recipient_type='email',
                expiry_date=expiry_date,
                status='pending'
            )
            share_logs.append(share_log)

            # Queue email task
            send_email_share_task.delay(str(share_log.id))

        return Response({
            'status': 'queued',
            'recipients_count': len(recipients),
            'share_logs': [str(log.id) for log in share_logs]
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'])
    def share_whatsapp(self, request, pk=None):
        """
        Generate WhatsApp share link.
        POST /api/documents/{id}/share_whatsapp/
        Body: {"phone": "+1234567890", "message": "..."}
        """
        document = self.get_object()

        # Generate share link if not exists
        if not document.is_public:
            document.generate_share_token()

        share_url = request.build_absolute_uri(
            f'/documents/share/{document.share_token}/'
        )

        phone = request.data.get('phone', '').replace('+', '').replace(' ', '')
        message = request.data.get('message', f'Check out this document: {document.title}')

        # Create WhatsApp URL
        whatsapp_url = f"https://api.whatsapp.com/send?phone={phone}&text={message}%0A{share_url}"

        # Create share log
        share_log = DocumentShareLog.objects.create(
            document=document,
            shared_by=request.user,
            share_method='whatsapp',
            recipient=phone,
            recipient_type='phone',
            status='delivered'
        )

        return Response({
            'whatsapp_url': whatsapp_url,
            'share_url': share_url,
            'share_log_id': str(share_log.id)
        })

    @action(detail=True, methods=['post'])
    def generate_share_link(self, request, pk=None):
        """
        Generate public share link.
        POST /api/documents/{id}/generate_share_link/
        Body: {"expiry_days": 7, "require_password": false, "password": "..."}
        """
        document = self.get_object()

        expiry_days = request.data.get('expiry_days', 7)
        require_password = request.data.get('require_password', False)
        password = request.data.get('password', '')

        # Generate token
        document.generate_share_token()

        # Set expiry
        if expiry_days:
            document.share_expiry = timezone.now() + timedelta(days=expiry_days)

        # Set password if required
        if require_password and password:
            from django.contrib.auth.hashers import make_password
            document.share_password = make_password(password)

        document.save()

        share_url = request.build_absolute_uri(
            f'/documents/share/{document.share_token}/'
        )

        return Response({
            'share_token': document.share_token,
            'share_url': share_url,
            'share_expiry': document.share_expiry,
            'is_public': document.is_public
        })

    @action(detail=True, methods=['post'])
    def revoke_share(self, request, pk=None):
        """
        Revoke public sharing.
        POST /api/documents/{id}/revoke_share/
        """
        document = self.get_object()
        document.revoke_share()

        return Response({'message': 'Share revoked successfully'})

    @action(detail=True, methods=['get'])
    def share_history(self, request, pk=None):
        """
        Get sharing history for document.
        GET /api/documents/{id}/share_history/
        """
        document = self.get_object()
        share_logs = document.share_logs.all()

        serializer = DocumentShareLogSerializer(share_logs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def compression_status(self, request, pk=None):
        """
        Get compression status.
        GET /api/documents/{id}/compression_status/
        """
        document = self.get_object()

        return Response({
            'compression_status': document.compression_status,
            'is_compressed': document.is_compressed,
            'compression_algorithm': document.compression_algorithm,
            'compression_ratio': document.compression_ratio,
            'original_size': document.original_file_size,
            'compressed_size': document.compressed_file_size,
            'compression_savings': document.compression_savings,
        })

    @action(detail=False, methods=['post'])
    def bulk_operations(self, request):
        """
        Perform bulk operations on documents.
        POST /api/documents/bulk_operations/
        Body: {"document_ids": [...], "action": "compress|delete|..."}
        """
        serializer = BulkOperationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        document_ids = data['document_ids']
        action_type = data['action']

        # Verify all documents belong to user
        documents = Document.objects.filter(
            id__in=document_ids,
            user=request.user
        )

        if documents.count() != len(document_ids):
            return Response(
                {'error': 'Some documents not found or do not belong to you'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Perform action
        if action_type == 'compress':
            algorithm = data.get('compression_algorithm')
            bulk_compress_documents_task.delay(
                str(request.user.id),
                [str(doc_id) for doc_id in document_ids],
                algorithm
            )
            return Response({
                'status': 'queued',
                'message': f'Compression queued for {len(document_ids)} documents'
            }, status=status.HTTP_202_ACCEPTED)

        elif action_type == 'delete':
            count = documents.count()
            documents.delete()
            return Response({
                'status': 'success',
                'deleted_count': count
            })

        elif action_type == 'add_tag':
            tag_id = data.get('tag_id')
            tag = get_object_or_404(DocumentTag, id=tag_id, user=request.user)
            for doc in documents:
                doc.tags.add(tag)
            return Response({'status': 'success'})

        elif action_type == 'remove_tag':
            tag_id = data.get('tag_id')
            tag = get_object_or_404(DocumentTag, id=tag_id, user=request.user)
            for doc in documents:
                doc.tags.remove(tag)
            return Response({'status': 'success'})

        elif action_type == 'change_category':
            category_id = data.get('category_id')
            if category_id:
                category = get_object_or_404(DocumentCategory, id=category_id, user=request.user)
                documents.update(category=category)
            else:
                documents.update(category=None)
            return Response({'status': 'success'})

        return Response(
            {'error': 'Unknown action'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['post'])
    def bulk_move(self, request):
        """
        Move multiple documents/folders to a target folder.
        POST /api/v1/documents/documents/bulk_move/
        Body: {
            "document_ids": ["uuid1", "uuid2"],
            "folder_ids": ["uuid3"],
            "target_folder_id": "uuid4" or null
        }
        """
        from django.db import transaction

        serializer = BulkMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        document_ids = data.get('document_ids', [])
        folder_ids = data.get('folder_ids', [])
        target_folder_id = data.get('target_folder_id')

        # Get target folder if specified
        target_folder = None
        if target_folder_id:
            try:
                target_folder = DocumentCategory.objects.get(
                    id=target_folder_id,
                    user=request.user
                )
            except DocumentCategory.DoesNotExist:
                return Response(
                    {'error': 'Target folder not found or does not belong to you'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Verify all documents belong to user
        if document_ids:
            documents = Document.objects.filter(
                id__in=document_ids,
                user=request.user
            )
            if documents.count() != len(document_ids):
                return Response(
                    {'error': 'Some documents not found or do not belong to you'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Verify all folders belong to user and validate circular moves
        if folder_ids:
            folders = DocumentCategory.objects.filter(
                id__in=folder_ids,
                user=request.user
            )
            if folders.count() != len(folder_ids):
                return Response(
                    {'error': 'Some folders not found or do not belong to you'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate each folder can be moved to target
            for folder in folders:
                if not folder.can_move_to(target_folder):
                    return Response(
                        {'error': f'Cannot move folder "{folder.name}" into itself or its descendants'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        # Perform bulk move in transaction
        with transaction.atomic():
            if document_ids:
                documents.update(category=target_folder)

            if folder_ids:
                for folder in folders:
                    folder.parent = target_folder
                    folder.save()

        return Response({
            'status': 'success',
            'moved_documents': len(document_ids),
            'moved_folders': len(folder_ids),
            'target_folder': DocumentCategorySerializer(target_folder).data if target_folder else None
        })


class StorageQuotaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing storage quota information.

    retrieve: Get current user's storage quota
    stats: Get detailed storage statistics
    recalculate: Trigger quota recalculation
    """

    serializer_class = UserStorageQuotaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return quota for current user only"""
        return UserStorageQuota.objects.filter(user=self.request.user)

    def get_object(self):
        """Get or create quota for current user"""
        quota, created = UserStorageQuota.objects.get_or_create(
            user=self.request.user
        )
        return quota

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get detailed storage statistics.
        GET /api/storage/stats/
        """
        quota = self.get_object()

        # Get compression stats by file type
        compression_by_type = CompressionStats.objects.filter(
            user=request.user
        ).values('file_type').annotate(
            total_files=Sum('total_files'),
            total_original=Sum('total_original_size'),
            total_compressed=Sum('total_compressed_size')
        )

        return Response({
            'quota': UserStorageQuotaSerializer(quota).data,
            'compression_by_type': list(compression_by_type),
        })

    @action(detail=False, methods=['post'])
    def recalculate(self, request):
        """
        Trigger quota recalculation.
        POST /api/storage/recalculate/
        """
        recalculate_user_quota.delay(str(request.user.id))

        return Response({
            'status': 'queued',
            'message': 'Quota recalculation queued'
        }, status=status.HTTP_202_ACCEPTED)


class CompressionStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing compression statistics.

    list: Get compression stats for current user
    """

    serializer_class = CompressionStatsSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['file_type', 'algorithm']

    def get_queryset(self):
        """Return stats for current user only"""
        return CompressionStats.objects.filter(user=self.request.user)
