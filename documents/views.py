"""
Django web views for document library.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, FileResponse, Http404
from django.contrib import messages
from django.db.models import Count
from django.core.paginator import Paginator

from .models import Document, DocumentCategory, DocumentTag, UserStorageQuota
from .utils.compression import decompress_file
import os


@login_required
def dashboard(request):
    """
    Main dashboard view showing document library overview.
    """
    # Get user's documents
    documents = Document.objects.filter(user=request.user).select_related('category').prefetch_related('tags')

    # Get storage quota
    quota, created = UserStorageQuota.objects.get_or_create(user=request.user)

    # Get categories with count
    categories = DocumentCategory.objects.filter(user=request.user).annotate(
        doc_count=Count('documents')
    )

    # Get recent documents
    recent_documents = documents[:10]

    # Statistics
    stats = {
        'total_documents': documents.count(),
        'total_original_size': quota.original_used,
        'total_compressed_size': quota.compressed_used,
        'compression_savings': quota.compression_savings,
        'compressed_count': documents.filter(is_compressed=True).count(),
    }

    context = {
        'documents': recent_documents,
        'categories': categories,
        'quota': quota,
        'stats': stats,
    }

    return render(request, 'documents/dashboard.html', context)


@login_required
def document_list(request):
    """
    Redirect to the unified drive view.
    This maintains backward compatibility with old /documents/list/ URLs.
    """
    return redirect('documents:drive')


@login_required
def document_detail(request, pk):
    """
    View detailed information about a document.
    """
    document = get_object_or_404(Document, id=pk, user=request.user)
    document.increment_view_count()

    share_logs = document.share_logs.all()[:10]

    context = {
        'document': document,
        'share_logs': share_logs,
    }

    return render(request, 'documents/document_detail.html', context)


@login_required
def document_upload(request):
    """
    Upload a new document.
    """
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        
        if not uploaded_file:
            messages.error(request, 'Please select a file to upload.')
            return redirect('documents:document_upload')
        
        title = request.POST.get('title', '').strip() or uploaded_file.name
        description = request.POST.get('description', '').strip()
        category_id = request.POST.get('category_id') or None
        tag_names_str = request.POST.get('tag_names', '').strip()
        
        # Parse tag names
        tag_names = [t.strip() for t in tag_names_str.split(',') if t.strip()] if tag_names_str else []
        
        try:
            # Detect file type
            import tempfile
            import os
            from .utils.file_handler import get_file_type, calculate_checksum
            
            # Handle file path for both memory and disk files
            if hasattr(uploaded_file, 'temporary_file_path'):
                file_path = uploaded_file.temporary_file_path()
                temp_file = None
            else:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1])
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_file.flush()
                file_path = temp_file.name
                temp_file.close()
            
            try:
                file_type, mime_type = get_file_type(file_path)
                checksum = calculate_checksum(file_path)
            finally:
                if temp_file:
                    try:
                        os.unlink(temp_file.name)
                    except:
                        pass
            
            # Create document
            document = Document.objects.create(
                user=request.user,
                title=title,
                description=description,
                file=uploaded_file,
                file_original_name=uploaded_file.name,
                file_type=file_type,
                original_file_size=uploaded_file.size,
                original_file_checksum=checksum,
                category_id=category_id if category_id else None,
                compression_status='pending'
            )
            
            # Create/get tags and assign
            if tag_names:
                tags = []
                for tag_name in tag_names:
                    tag, created = DocumentTag.objects.get_or_create(
                        user=request.user,
                        name=tag_name
                    )
                    tags.append(tag)
                document.tags.set(tags)
            
            messages.success(request, f'Document "{title}" uploaded successfully!')
            return redirect('documents:document_list')
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Document upload error: {e}", exc_info=True)
            messages.error(request, f'Error uploading document: {str(e)}')
            return redirect('documents:document_upload')

    categories = DocumentCategory.objects.filter(user=request.user)
    tags = DocumentTag.objects.filter(user=request.user)

    context = {
        'categories': categories,
        'tags': tags,
    }

    return render(request, 'documents/document_upload.html', context)


@login_required
def document_edit(request, pk):
    """
    Edit document metadata.
    """
    document = get_object_or_404(Document, id=pk, user=request.user)

    if request.method == 'POST':
        # Handle edit via form
        messages.success(request, 'Document edit functionality - use API endpoint')
        return redirect('documents:document_detail', pk=pk)

    categories = DocumentCategory.objects.filter(user=request.user)
    tags = DocumentTag.objects.filter(user=request.user)

    context = {
        'document': document,
        'categories': categories,
        'tags': tags,
    }

    return render(request, 'documents/document_edit.html', context)


@login_required
def document_delete(request, pk):
    """
    Delete a document.
    """
    document = get_object_or_404(Document, id=pk, user=request.user)

    if request.method == 'POST':
        document.delete()
        messages.success(request, f'Document "{document.title}" deleted successfully')
        return redirect('documents:dashboard')

    context = {
        'document': document,
    }

    return render(request, 'documents/document_confirm_delete.html', context)


@login_required
def document_download(request, pk):
    """
    Download a document (with decompression if needed).
    """
    document = get_object_or_404(Document, id=pk, user=request.user)

    # Increment download count
    document.increment_download_count()

    # Check if document is compressed
    if document.is_compressed and document.compression_algorithm != 'none':
        # Decompress to temp location
        from django.conf import settings
        import tempfile

        temp_dir = settings.DECOMPRESSION_TEMP_DIR
        os.makedirs(temp_dir, exist_ok=True)

        temp_path = os.path.join(temp_dir, f"{document.id}_{document.file_original_name}")

        try:
            # Decompress
            decompress_file(
                input_path=document.file.path,
                output_path=temp_path,
                algorithm=document.compression_algorithm
            )

            # Serve file
            response = FileResponse(
                open(temp_path, 'rb'),
                as_attachment=True,
                filename=document.file_original_name
            )
            return response

        except Exception as e:
            messages.error(request, f'Failed to decompress file: {str(e)}')
            return redirect('documents:document_detail', pk=pk)
    else:
        # Serve directly
        response = FileResponse(
            document.file.open('rb'),
            as_attachment=True,
            filename=document.file_original_name
        )
        return response


@login_required
def document_preview(request, pk):
    """
    Preview a document (inline view for images, PDFs, etc.).
    """
    document = get_object_or_404(Document, id=pk, user=request.user)
    document.increment_view_count()

    context = {
        'document': document,
    }

    return render(request, 'documents/document_preview.html', context)


@login_required
def toggle_favorite(request, pk):
    """
    Toggle favorite status.
    """
    if request.method == 'POST':
        document = get_object_or_404(Document, id=pk, user=request.user)
        document.is_favorite = not document.is_favorite
        document.save(update_fields=['is_favorite'])

        # Handle HTMX request
        if request.headers.get('HX-Request'):
            return render(request, 'documents/partials/favorite_button.html', {'document': document})
        
        # Regular redirect - go back to previous page
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if next_url:
            return redirect(next_url)
        return redirect('documents:drive')

    return HttpResponse(status=405)


@login_required
def category_list(request):
    """
    List all categories.
    """
    categories = DocumentCategory.objects.filter(user=request.user).annotate(
        doc_count=Count('documents')
    )

    context = {
        'categories': categories,
    }

    return render(request, 'documents/category_list.html', context)


@login_required
def category_create(request):
    """
    Create a new category.
    """
    if request.method == 'POST':
        messages.success(request, 'Category create functionality - use API endpoint')
        return redirect('documents:category_list')

    return render(request, 'documents/category_form.html')


@login_required
def category_edit(request, pk):
    """
    Edit a category.
    """
    category = get_object_or_404(DocumentCategory, id=pk, user=request.user)

    if request.method == 'POST':
        messages.success(request, 'Category edit functionality - use API endpoint')
        return redirect('documents:category_list')

    context = {
        'category': category,
    }

    return render(request, 'documents/category_form.html', context)


@login_required
def category_delete(request, pk):
    """
    Delete a category.
    """
    category = get_object_or_404(DocumentCategory, id=pk, user=request.user)

    if request.method == 'POST':
        category.delete()
        messages.success(request, f'Category "{category.name}" deleted successfully')
        return redirect('documents:category_list')

    context = {
        'category': category,
    }

    return render(request, 'documents/category_confirm_delete.html', context)


@login_required
def storage_stats(request):
    """
    View storage and quota statistics.
    """
    quota, created = UserStorageQuota.objects.get_or_create(user=request.user)

    # Get documents by file type
    documents_by_type = Document.objects.filter(user=request.user).values('file_type').annotate(
        count=Count('id')
    )

    context = {
        'quota': quota,
        'documents_by_type': documents_by_type,
    }

    return render(request, 'documents/storage_stats.html', context)


@login_required
def compression_stats(request):
    """
    View compression statistics.
    """
    from .models import CompressionStats

    stats = CompressionStats.objects.filter(user=request.user)

    context = {
        'stats': stats,
    }

    return render(request, 'documents/compression_stats.html', context)


def public_share(request, token):
    """
    Public view for shared documents (no login required).
    """
    document = get_object_or_404(Document, share_token=token, is_public=True)

    # Check expiry
    if document.is_share_expired():
        raise Http404("This share link has expired")

    # Check password if required
    if document.share_password:
        # Handle password authentication
        password = request.POST.get('password')
        if not password:
            return render(request, 'documents/share_password.html', {'document': document})

        from django.contrib.auth.hashers import check_password
        if not check_password(password, document.share_password):
            messages.error(request, 'Incorrect password')
            return render(request, 'documents/share_password.html', {'document': document})

    # Increment access count
    document.increment_access_count()

    context = {
        'document': document,
    }

    return render(request, 'documents/public_share.html', context)


# =============================================================================
# FOLDER/DRIVE VIEWS (Google Drive-like functionality)
# =============================================================================

@login_required
def drive(request, folder_id=None):
    """
    Main drive view - browse folders and documents (Google Drive-like).
    If folder_id is None, show root level (My Drive).
    """
    current_folder = None
    if folder_id:
        current_folder = get_object_or_404(DocumentCategory, id=folder_id, user=request.user)
    
    # Get subfolders in current location
    subfolders = DocumentCategory.objects.filter(
        user=request.user,
        parent=current_folder
    ).annotate(
        doc_count=Count('documents')
    ).order_by('name')
    
    # Get documents in current folder
    documents = Document.objects.filter(
        user=request.user,
        category=current_folder
    ).select_related('category').order_by('-upload_date')
    
    # Apply search filter
    search = request.GET.get('search', '').strip()
    if search:
        documents = documents.filter(title__icontains=search)
        subfolders = subfolders.filter(name__icontains=search)
    
    # Get breadcrumbs
    breadcrumbs = []
    if current_folder:
        breadcrumbs = current_folder.breadcrumbs
    
    # Get storage quota
    quota, _ = UserStorageQuota.objects.get_or_create(user=request.user)
    
    # Calculate usage percentage
    usage_percentage = (quota.original_used / quota.original_quota * 100) if quota.original_quota > 0 else 0
    
    # Get all folders for move dialog
    all_folders = DocumentCategory.objects.filter(user=request.user).order_by('path')
    
    context = {
        'current_folder': current_folder,
        'subfolders': subfolders,
        'documents': documents,
        'breadcrumbs': breadcrumbs,
        'quota': quota,
        'usage_percentage': usage_percentage,
        'search_query': search,
        'all_folders': all_folders,
    }
    
    return render(request, 'documents/drive.html', context)


@login_required
def folder_create(request, parent_id=None):
    """
    Create a new folder.
    """
    parent_folder = None
    if parent_id:
        parent_folder = get_object_or_404(DocumentCategory, id=parent_id, user=request.user)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        color = request.POST.get('color', '#3B82F6')
        
        if not name:
            messages.error(request, 'Folder name is required.')
            return redirect('documents:drive' if not parent_folder else 'documents:drive_folder', folder_id=parent_id)
        
        # Check for duplicate name in same parent
        if DocumentCategory.objects.filter(user=request.user, name=name, parent=parent_folder).exists():
            messages.error(request, f'A folder named "{name}" already exists in this location.')
            return redirect('documents:drive' if not parent_folder else 'documents:drive_folder', folder_id=parent_id)
        
        # Create folder
        folder = DocumentCategory.objects.create(
            user=request.user,
            name=name,
            description=description,
            color=color,
            parent=parent_folder
        )
        
        messages.success(request, f'Folder "{name}" created successfully!')
        
        if parent_folder:
            return redirect('documents:drive_folder', folder_id=parent_id)
        return redirect('documents:drive')
    
    context = {
        'parent_folder': parent_folder,
    }
    
    return render(request, 'documents/folder_form.html', context)


@login_required
def folder_edit(request, folder_id):
    """
    Edit folder name/description.
    """
    folder = get_object_or_404(DocumentCategory, id=folder_id, user=request.user)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        color = request.POST.get('color', folder.color)
        
        if not name:
            messages.error(request, 'Folder name is required.')
            return redirect('documents:folder_edit', folder_id=folder_id)
        
        # Check for duplicate name in same parent (excluding self)
        if DocumentCategory.objects.filter(
            user=request.user, 
            name=name, 
            parent=folder.parent
        ).exclude(id=folder.id).exists():
            messages.error(request, f'A folder named "{name}" already exists in this location.')
            return redirect('documents:folder_edit', folder_id=folder_id)
        
        folder.name = name
        folder.description = description
        folder.color = color
        folder.save()
        
        messages.success(request, f'Folder "{name}" updated successfully!')
        
        if folder.parent:
            return redirect('documents:drive_folder', folder_id=folder.parent.id)
        return redirect('documents:drive')
    
    context = {
        'folder': folder,
        'is_edit': True,
    }
    
    return render(request, 'documents/folder_form.html', context)


@login_required
def folder_delete(request, folder_id):
    """
    Delete a folder and optionally its contents.
    """
    folder = get_object_or_404(DocumentCategory, id=folder_id, user=request.user)
    parent_id = folder.parent.id if folder.parent else None
    
    if request.method == 'POST':
        action = request.POST.get('action', 'move_to_root')
        
        if action == 'delete_all':
            # Delete all documents in folder and subfolders
            def delete_folder_contents(f):
                for doc in f.documents.all():
                    doc.file.delete()  # Delete actual file
                    doc.delete()
                for subfolder in f.subfolders.all():
                    delete_folder_contents(subfolder)
                    subfolder.delete()
            
            delete_folder_contents(folder)
            folder.delete()
            messages.success(request, f'Folder "{folder.name}" and all contents deleted.')
        else:
            # Move contents to parent (root if no parent)
            parent = folder.parent
            
            # Move documents to parent
            folder.documents.update(category=parent)
            
            # Move subfolders to parent
            for subfolder in folder.subfolders.all():
                subfolder.parent = parent
                subfolder.save()
            
            folder.delete()
            messages.success(request, f'Folder "{folder.name}" deleted. Contents moved to parent.')
        
        if parent_id:
            return redirect('documents:drive_folder', folder_id=parent_id)
        return redirect('documents:drive')
    
    # Get folder stats
    doc_count = folder.total_document_count
    subfolder_count = len(folder.get_descendants())
    
    context = {
        'folder': folder,
        'doc_count': doc_count,
        'subfolder_count': subfolder_count,
    }
    
    return render(request, 'documents/folder_confirm_delete.html', context)


@login_required
def move_item(request):
    """
    Move document or folder to another location.
    """
    if request.method != 'POST':
        return HttpResponse(status=405)
    
    item_type = request.POST.get('item_type')  # 'document' or 'folder'
    item_id = request.POST.get('item_id')
    target_folder_id = request.POST.get('target_folder_id')  # None/empty for root
    
    target_folder = None
    if target_folder_id:
        target_folder = get_object_or_404(DocumentCategory, id=target_folder_id, user=request.user)
    
    if item_type == 'document':
        document = get_object_or_404(Document, id=item_id, user=request.user)
        document.category = target_folder
        document.save(update_fields=['category'])
        messages.success(request, f'Document "{document.title}" moved successfully!')
        
    elif item_type == 'folder':
        folder = get_object_or_404(DocumentCategory, id=item_id, user=request.user)
        
        # Prevent moving folder into itself or its descendants
        if not folder.can_move_to(target_folder):
            messages.error(request, 'Cannot move folder into itself or its subfolders.')
            return redirect('documents:drive')
        
        folder.parent = target_folder
        folder.save()
        messages.success(request, f'Folder "{folder.name}" moved successfully!')
    
    # Redirect to target folder or root
    if target_folder:
        return redirect('documents:drive_folder', folder_id=target_folder.id)
    return redirect('documents:drive')


@login_required  
def upload_to_folder(request, folder_id=None):
    """
    Upload document to a specific folder.
    """
    folder = None
    if folder_id:
        folder = get_object_or_404(DocumentCategory, id=folder_id, user=request.user)
    
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        
        if not uploaded_file:
            messages.error(request, 'Please select a file to upload.')
            if folder:
                return redirect('documents:drive_folder', folder_id=folder_id)
            return redirect('documents:drive')
        
        title = request.POST.get('title', '').strip() or uploaded_file.name
        description = request.POST.get('description', '').strip()
        
        try:
            import tempfile
            from .utils.file_handler import get_file_type, calculate_checksum
            
            # Handle file path for both memory and disk files
            if hasattr(uploaded_file, 'temporary_file_path'):
                file_path = uploaded_file.temporary_file_path()
                temp_file = None
            else:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1])
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_file.flush()
                file_path = temp_file.name
                temp_file.close()
            
            try:
                file_type, mime_type = get_file_type(file_path)
                checksum = calculate_checksum(file_path)
            finally:
                if temp_file:
                    try:
                        os.unlink(temp_file.name)
                    except:
                        pass
            
            # Create document in the specified folder
            document = Document.objects.create(
                user=request.user,
                title=title,
                description=description,
                file=uploaded_file,
                file_original_name=uploaded_file.name,
                file_type=file_type,
                original_file_size=uploaded_file.size,
                original_file_checksum=checksum,
                category=folder,  # folder = None means root
                compression_status='pending'
            )
            
            messages.success(request, f'Document "{title}" uploaded successfully!')
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Document upload error: {e}", exc_info=True)
            messages.error(request, f'Error uploading document: {str(e)}')
        
        if folder:
            return redirect('documents:drive_folder', folder_id=folder_id)
        return redirect('documents:drive')
    
    # GET request - show upload form
    context = {
        'current_folder': folder,
        'breadcrumbs': folder.breadcrumbs if folder else [],
    }
    
    return render(request, 'documents/upload_to_folder.html', context)
