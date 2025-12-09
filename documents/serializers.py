"""
REST API Serializers for document library.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import (
    DocumentCategory,
    DocumentTag,
    Document,
    DocumentShareLog,
    UserStorageQuota,
    DocumentBackup,
    CompressionStats,
)
from .utils.compression import calculate_checksum, get_file_type

User = get_user_model()


class DocumentCategorySerializer(serializers.ModelSerializer):
    """Serializer for DocumentCategory model"""

    document_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = DocumentCategory
        fields = [
            'id',
            'name',
            'description',
            'color',
            'icon',
            'document_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value):
        """Ensure category name is unique for the user"""
        user = self.context['request'].user
        queryset = DocumentCategory.objects.filter(user=user, name=value)

        # Exclude current instance when updating
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)

        if queryset.exists():
            raise serializers.ValidationError("You already have a category with this name.")

        return value

    def create(self, validated_data):
        """Automatically set user from request"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class DocumentTagSerializer(serializers.ModelSerializer):
    """Serializer for DocumentTag model"""

    document_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = DocumentTag
        fields = ['id', 'name', 'document_count', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_name(self, value):
        """Ensure tag name is unique for the user"""
        user = self.context['request'].user
        queryset = DocumentTag.objects.filter(user=user, name=value)

        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)

        if queryset.exists():
            raise serializers.ValidationError("You already have a tag with this name.")

        return value

    def create(self, validated_data):
        """Automatically set user from request"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class DocumentListSerializer(serializers.ModelSerializer):
    """Serializer for Document list view (lighter version)"""

    category = DocumentCategorySerializer(read_only=True)
    tags = DocumentTagSerializer(many=True, read_only=True)
    file_size_display = serializers.CharField(read_only=True)
    compression_ratio_percentage = serializers.FloatField(read_only=True)
    compression_savings = serializers.IntegerField(read_only=True)

    class Meta:
        model = Document
        fields = [
            'id',
            'title',
            'file_type',
            'file_original_name',
            'original_file_size',
            'compressed_file_size',
            'compression_ratio',
            'compression_ratio_percentage',
            'compression_savings',
            'compression_algorithm',
            'is_compressed',
            'compression_status',
            'category',
            'tags',
            'is_favorite',
            'upload_date',
            'last_accessed',
            'download_count',
            'view_count',
            'file_size_display',
        ]


class DocumentDetailSerializer(serializers.ModelSerializer):
    """Serializer for Document detail view (full version)"""

    category = DocumentCategorySerializer(read_only=True)
    category_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    tags = DocumentTagSerializer(many=True, read_only=True)
    tag_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    file_size_display = serializers.CharField(read_only=True)
    compression_ratio_percentage = serializers.FloatField(read_only=True)
    compression_savings = serializers.IntegerField(read_only=True)

    class Meta:
        model = Document
        fields = [
            'id',
            'title',
            'description',
            'file',
            'file_original_name',
            'file_type',
            'original_file_size',
            'compressed_file_size',
            'compression_ratio',
            'compression_ratio_percentage',
            'compression_savings',
            'compression_algorithm',
            'is_compressed',
            'original_file_checksum',
            'compressed_file_checksum',
            'compression_timestamp',
            'decompression_failed',
            'compression_status',
            'category',
            'category_id',
            'tags',
            'tag_ids',
            'is_favorite',
            'upload_date',
            'last_modified',
            'last_accessed',
            'is_public',
            'share_token',
            'share_expiry',
            'download_count',
            'view_count',
            'access_count',
            'file_size_display',
        ]
        read_only_fields = [
            'id',
            'file_type',
            'original_file_size',
            'compressed_file_size',
            'compression_ratio',
            'compression_algorithm',
            'is_compressed',
            'original_file_checksum',
            'compressed_file_checksum',
            'compression_timestamp',
            'decompression_failed',
            'compression_status',
            'upload_date',
            'last_modified',
            'last_accessed',
            'download_count',
            'view_count',
            'access_count',
        ]

    def validate_category_id(self, value):
        """Ensure category belongs to the user"""
        if value:
            user = self.context['request'].user
            if not DocumentCategory.objects.filter(id=value, user=user).exists():
                raise serializers.ValidationError("Category not found or does not belong to you.")
        return value

    def validate_tag_ids(self, value):
        """Ensure all tags belong to the user"""
        if value:
            user = self.context['request'].user
            valid_tags = DocumentTag.objects.filter(id__in=value, user=user)
            if valid_tags.count() != len(value):
                raise serializers.ValidationError("One or more tags not found or do not belong to you.")
        return value

    def create(self, validated_data):
        """Handle file upload and compression"""
        import tempfile
        import os

        tag_ids = validated_data.pop('tag_ids', [])
        category_id = validated_data.pop('category_id', None)

        # Set user
        validated_data['user'] = self.context['request'].user

        # Get uploaded file
        uploaded_file = validated_data.get('file')
        if uploaded_file:
            # Store original filename
            validated_data['file_original_name'] = uploaded_file.name

            # Handle file path for both memory and disk files
            if hasattr(uploaded_file, 'temporary_file_path'):
                # File is on disk
                file_path = uploaded_file.temporary_file_path()
                temp_file = None
            else:
                # File is in memory, write to temp file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1])
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_file.flush()
                file_path = temp_file.name
                temp_file.close()

            try:
                # Detect file type
                file_type, mime_type = get_file_type(file_path)
                validated_data['file_type'] = file_type

                # Get file size
                validated_data['original_file_size'] = uploaded_file.size

                # Calculate checksum
                validated_data['original_file_checksum'] = calculate_checksum(file_path)
            finally:
                # Clean up temp file if we created one
                if temp_file:
                    try:
                        os.unlink(temp_file.name)
                    except:
                        pass

            # Set default title from filename if not provided
            if not validated_data.get('title'):
                validated_data['title'] = uploaded_file.name

        # Set category
        if category_id:
            validated_data['category_id'] = category_id

        # Create document
        document = super().create(validated_data)

        # Set tags
        if tag_ids:
            document.tags.set(tag_ids)

        return document

    def update(self, instance, validated_data):
        """Handle updates to document metadata"""
        tag_ids = validated_data.pop('tag_ids', None)
        category_id = validated_data.pop('category_id', None)

        # Update category
        if category_id is not None:
            validated_data['category_id'] = category_id

        # Update document
        instance = super().update(instance, validated_data)

        # Update tags
        if tag_ids is not None:
            instance.tags.set(tag_ids)

        return instance


class DocumentUploadSerializer(serializers.ModelSerializer):
    """Serializer specifically for document upload"""

    title = serializers.CharField(required=False, allow_blank=True)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    tag_names = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Document
        fields = ['file', 'title', 'description', 'category_id', 'tag_names']

    def validate_tag_names(self, value):
        """Convert comma-separated string to list of tag names."""
        if not value:
            return []
        if isinstance(value, list):
            return value
        # Handle comma-separated string
        return [tag.strip() for tag in value.split(',') if tag.strip()]

    def create(self, validated_data):
        """Handle file upload with auto tag creation"""
        import tempfile
        import os

        tag_names = validated_data.pop('tag_names', [])
        category_id = validated_data.pop('category_id', None)

        user = self.context['request'].user
        uploaded_file = validated_data['file']

        # Handle file path for both memory and disk files
        if hasattr(uploaded_file, 'temporary_file_path'):
            # File is on disk
            file_path = uploaded_file.temporary_file_path()
            temp_file = None
        else:
            # File is in memory, write to temp file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1])
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            temp_file.flush()
            file_path = temp_file.name
            temp_file.close()

        try:
            # Detect file type
            file_type, mime_type = get_file_type(file_path)

            # Calculate checksum
            checksum = calculate_checksum(file_path)
        finally:
            # Clean up temp file if we created one
            if temp_file:
                try:
                    os.unlink(temp_file.name)
                except:
                    pass

        # Create document - use filename if title is empty
        title = validated_data.get('title', '').strip()
        if not title:
            title = uploaded_file.name
        
        document = Document.objects.create(
            user=user,
            title=title,
            description=validated_data.get('description', ''),
            file=uploaded_file,
            file_original_name=uploaded_file.name,
            file_type=file_type,
            original_file_size=uploaded_file.size,
            original_file_checksum=checksum,
            category_id=category_id,
            compression_status='pending'
        )

        # Create/get tags and assign
        if tag_names:
            tags = []
            for tag_name in tag_names:
                tag, created = DocumentTag.objects.get_or_create(
                    user=user,
                    name=tag_name
                )
                tags.append(tag)
            document.tags.set(tags)

        return document


class DocumentShareLogSerializer(serializers.ModelSerializer):
    """Serializer for DocumentShareLog model"""

    document = DocumentListSerializer(read_only=True)
    shared_by_username = serializers.CharField(source='shared_by.username', read_only=True)

    class Meta:
        model = DocumentShareLog
        fields = [
            'id',
            'document',
            'shared_by_username',
            'share_method',
            'recipient',
            'recipient_type',
            'shared_at',
            'expiry_date',
            'status',
            'error_message',
            'access_count',
            'last_accessed',
        ]
        read_only_fields = [
            'id',
            'shared_at',
            'status',
            'error_message',
            'access_count',
            'last_accessed',
        ]


class ShareDocumentSerializer(serializers.Serializer):
    """Serializer for sharing a document"""

    share_method = serializers.ChoiceField(choices=['email', 'whatsapp', 'direct_link'])
    recipients = serializers.ListField(
        child=serializers.EmailField(),
        required=False
    )
    phone = serializers.CharField(max_length=20, required=False)
    expiry_days = serializers.IntegerField(default=7, min_value=1, max_value=365)
    require_password = serializers.BooleanField(default=False)
    password = serializers.CharField(required=False, allow_blank=True)
    message = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        """Validate share method requirements"""
        share_method = data['share_method']

        if share_method == 'email' and not data.get('recipients'):
            raise serializers.ValidationError("Recipients required for email sharing")

        if share_method == 'whatsapp' and not data.get('phone'):
            raise serializers.ValidationError("Phone number required for WhatsApp sharing")

        if data.get('require_password') and not data.get('password'):
            raise serializers.ValidationError("Password required when require_password is True")

        return data


class UserStorageQuotaSerializer(serializers.ModelSerializer):
    """Serializer for UserStorageQuota model"""

    original_available = serializers.IntegerField(read_only=True)
    original_used_percentage = serializers.FloatField(read_only=True)
    compression_ratio = serializers.FloatField(read_only=True)

    class Meta:
        model = UserStorageQuota
        fields = [
            'id',
            'original_quota',
            'original_used',
            'original_available',
            'original_used_percentage',
            'compressed_used',
            'compression_savings',
            'compression_ratio',
            'document_count',
            'last_calculated',
        ]
        read_only_fields = [
            'id',
            'original_used',
            'compressed_used',
            'compression_savings',
            'document_count',
            'last_calculated',
        ]


class CompressionStatsSerializer(serializers.ModelSerializer):
    """Serializer for CompressionStats model"""

    class Meta:
        model = CompressionStats
        fields = [
            'id',
            'file_type',
            'algorithm',
            'total_files',
            'avg_compression_ratio',
            'total_original_size',
            'total_compressed_size',
            'avg_compression_time',
            'failure_count',
            'last_updated',
        ]
        read_only_fields = [
            'id',
            'file_type',
            'algorithm',
            'total_files',
            'avg_compression_ratio',
            'total_original_size',
            'total_compressed_size',
            'avg_compression_time',
            'failure_count',
            'last_updated',
        ]


class BulkOperationSerializer(serializers.Serializer):
    """Serializer for bulk operations"""

    document_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1
    )
    action = serializers.ChoiceField(
        choices=['compress', 'delete', 'download', 'add_tag', 'remove_tag', 'change_category']
    )
    # Optional parameters for specific actions
    tag_id = serializers.UUIDField(required=False)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    compression_algorithm = serializers.ChoiceField(
        choices=['zstd', 'brotli', 'deflate'],
        required=False
    )

    def validate(self, data):
        """Validate action-specific requirements"""
        action = data['action']

        if action in ['add_tag', 'remove_tag'] and not data.get('tag_id'):
            raise serializers.ValidationError("tag_id required for tag operations")

        if action == 'change_category' and 'category_id' not in data:
            raise serializers.ValidationError("category_id required for change_category")

        return data


class FolderTreeSerializer(serializers.ModelSerializer):
    """Serializer for folder tree structure with nested children"""

    children = serializers.SerializerMethodField()
    document_count = serializers.IntegerField(read_only=True)
    subfolder_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = DocumentCategory
        fields = [
            'id',
            'name',
            'description',
            'color',
            'icon',
            'parent',
            'path',
            'depth',
            'document_count',
            'subfolder_count',
            'children',
            'created_at',
        ]
        read_only_fields = ['id', 'path', 'depth', 'created_at']

    def get_children(self, obj):
        """Get nested children folders"""
        # Check if we should expand all levels or just direct children
        request = self.context.get('request')
        expand_all = request and request.query_params.get('expand') == 'true'

        if expand_all or not hasattr(obj, '_no_recursion'):
            # Annotate subfolders with counts
            from django.db.models import Count
            subfolders = obj.subfolders.annotate(
                document_count=Count('documents'),
                subfolder_count=Count('subfolders')
            )
            # Recursively serialize children
            return FolderTreeSerializer(
                subfolders,
                many=True,
                context=self.context
            ).data
        return []


class BreadcrumbSerializer(serializers.ModelSerializer):
    """Simple serializer for breadcrumb navigation"""

    class Meta:
        model = DocumentCategory
        fields = ['id', 'name', 'path']


class FolderContentsSerializer(serializers.Serializer):
    """Serializer for combined folder contents (subfolders + documents)"""

    folder = DocumentCategorySerializer(read_only=True)
    breadcrumbs = BreadcrumbSerializer(many=True, read_only=True)
    subfolders = DocumentCategorySerializer(many=True, read_only=True)
    documents = DocumentListSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)


class BulkMoveSerializer(serializers.Serializer):
    """Serializer for bulk move operations"""

    document_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=[]
    )
    folder_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=[]
    )
    target_folder_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, data):
        """Validate that at least one item is being moved"""
        document_ids = data.get('document_ids', [])
        folder_ids = data.get('folder_ids', [])

        if not document_ids and not folder_ids:
            raise serializers.ValidationError("At least one document or folder must be specified")

        return data
