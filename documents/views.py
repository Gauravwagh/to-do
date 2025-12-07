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
    List all documents with filtering and pagination.
    """
    documents = Document.objects.filter(user=request.user).select_related('category').prefetch_related('tags')

    # Apply filters
    category_id = request.GET.get('category')
    if category_id:
        documents = documents.filter(category_id=category_id)

    file_type = request.GET.get('file_type')
    if file_type:
        documents = documents.filter(file_type=file_type)

    is_favorite = request.GET.get('is_favorite')
    if is_favorite == 'true':
        documents = documents.filter(is_favorite=True)

    search = request.GET.get('search')
    if search:
        documents = documents.filter(title__icontains=search)

    # Ordering
    order_by = request.GET.get('order_by', '-upload_date')
    documents = documents.order_by(order_by)

    # Pagination
    paginator = Paginator(documents, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Get categories for filter
    categories = DocumentCategory.objects.filter(user=request.user)

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'current_category': category_id,
        'current_file_type': file_type,
        'search_query': search,
    }

    return render(request, 'documents/document_list.html', context)


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
        # This would typically be handled by a form
        # For now, just show a placeholder
        messages.success(request, 'Document upload functionality - use API endpoint')
        return redirect('documents:dashboard')

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
    Toggle favorite status via HTMX.
    """
    if request.method == 'POST':
        document = get_object_or_404(Document, id=pk, user=request.user)
        document.is_favorite = not document.is_favorite
        document.save(update_fields=['is_favorite'])

        # Return partial template for HTMX
        return render(request, 'documents/partials/favorite_button.html', {'document': document})

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
