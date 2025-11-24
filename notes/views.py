from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from .models import Note, Notebook, NoteAttachment, SharedNote, Todo
from .forms import NoteForm, NotebookForm, NoteSearchForm, NoteMoveForm, NoteCopyForm, TodoForm, TodoQuickForm, TodoBulkForm, AttachmentForm, MultipleAttachmentForm, StandaloneTodoForm
import json


class DashboardView(LoginRequiredMixin, ListView):
    """Main dashboard view showing user's notes."""
    model = Note
    template_name = 'notes/dashboard.html'
    context_object_name = 'notes'
    paginate_by = 12
    
    def get_queryset(self):
        return Note.objects.filter(
            user=self.request.user,
            is_archived=False
        ).select_related('notebook').prefetch_related('tags')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Note Statistics
        total_notes = user.notes.count()
        total_notebooks = user.notebooks.count()
        pinned_notes = user.notes.filter(is_pinned=True).count()
        archived_notes = user.notes.filter(is_archived=True).count()
        
        # Todo Statistics
        user_todos = Todo.objects.filter(note__user=user)
        total_todos = user_todos.count()
        completed_todos = user_todos.filter(is_completed=True).count()
        pending_todos = user_todos.filter(status='pending').count()
        overdue_todos = user_todos.filter(
            due_date__lt=timezone.now(),
            is_completed=False
        ).count()
        
        # Statistics
        standalone_todos = user.todos.filter(note__isnull=True).count()
        context.update({
            'total_notes': total_notes,
            'total_notebooks': total_notebooks,
            'pinned_notes': pinned_notes,
            'archived_notes': archived_notes,
            'total_todos': total_todos,
            'completed_todos': completed_todos,
            'pending_todos': pending_todos,
            'overdue_todos': overdue_todos,
            'standalone_todos': standalone_todos,
            'recent_notes': user.notes.order_by('-modified')[:5],
            'notebooks': user.notebooks.all()[:10],
        })
        
        return context


class NoteDetailView(LoginRequiredMixin, DetailView):
    """Note detail view."""
    model = Note
    template_name = 'notes/note_detail.html'
    context_object_name = 'note'
    
    def get_queryset(self):
        return Note.objects.filter(
            Q(user=self.request.user) | 
            Q(shares__shared_with=self.request.user)
        ).select_related('user', 'notebook').prefetch_related('tags', 'attachments')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['archived_notes'] = user.notes.filter(is_archived=True).count()
        context['standalone_todos'] = user.todos.filter(note__isnull=True).count()
        return context


class NoteCreateView(LoginRequiredMixin, CreateView):
    """Create new note."""
    model = Note
    form_class = NoteForm
    template_name = 'notes/note_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['archived_notes'] = user.notes.filter(is_archived=True).count()
        context['standalone_todos'] = user.todos.filter(note__isnull=True).count()
        return context
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        
        # Set default notebook if none selected
        if not form.instance.notebook:
            default_notebook, created = Notebook.objects.get_or_create(
                user=self.request.user,
                is_default=True,
                defaults={'name': 'Default', 'description': 'Default notebook'}
            )
            form.instance.notebook = default_notebook
        
        response = super().form_valid(form)
        messages.success(self.request, 'Note created successfully!')
        return response
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class NoteUpdateView(LoginRequiredMixin, UpdateView):
    """Update existing note."""
    model = Note
    form_class = NoteForm
    template_name = 'notes/note_form.html'
    
    def get_queryset(self):
        return Note.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['archived_notes'] = user.notes.filter(is_archived=True).count()
        context['standalone_todos'] = user.todos.filter(note__isnull=True).count()
        return context
    
    def form_valid(self, form):
        # Handle AJAX auto-save requests
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form.save()
            return JsonResponse({'success': True})
        
        response = super().form_valid(form)
        messages.success(self.request, 'Note updated successfully!')
        return response
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class NoteDeleteView(LoginRequiredMixin, DeleteView):
    """Delete note."""
    model = Note
    template_name = 'notes/note_confirm_delete.html'
    success_url = reverse_lazy('notes:dashboard')
    
    def get_queryset(self):
        return Note.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Note deleted successfully!')
        return super().delete(request, *args, **kwargs)


class NotebookListView(LoginRequiredMixin, ListView):
    """List user's notebooks."""
    model = Notebook
    template_name = 'notes/notebook_list.html'
    context_object_name = 'notebooks'
    
    def get_queryset(self):
        return Notebook.objects.filter(user=self.request.user).annotate(
            note_count=Count('notes')
        )


class NotebookDetailView(LoginRequiredMixin, DetailView):
    """Notebook detail view showing its notes."""
    model = Notebook
    template_name = 'notes/notebook_detail.html'
    context_object_name = 'notebook'
    
    def get_queryset(self):
        return Notebook.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        notebook = self.get_object()
        
        notes = notebook.notes.filter(is_archived=False).order_by('-modified')
        paginator = Paginator(notes, 12)
        page_number = self.request.GET.get('page')
        context['notes'] = paginator.get_page(page_number)
        
        return context


class NotebookCreateView(LoginRequiredMixin, CreateView):
    """Create new notebook."""
    model = Notebook
    form_class = NotebookForm
    template_name = 'notes/notebook_form.html'
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Notebook created successfully!')
        return response


class NotebookUpdateView(LoginRequiredMixin, UpdateView):
    """Update existing notebook."""
    model = Notebook
    form_class = NotebookForm
    template_name = 'notes/notebook_form.html'
    
    def get_queryset(self):
        return Notebook.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Notebook updated successfully!')
        return response


class NotebookDeleteView(LoginRequiredMixin, DeleteView):
    """Delete notebook."""
    model = Notebook
    template_name = 'notes/notebook_confirm_delete.html'
    success_url = reverse_lazy('notes:notebook_list')
    
    def get_queryset(self):
        return Notebook.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        notebook = self.get_object()
        
        # Move notes to default notebook
        default_notebook, created = Notebook.objects.get_or_create(
            user=request.user,
            is_default=True,
            defaults={'name': 'Default', 'description': 'Default notebook'}
        )
        
        notebook.notes.update(notebook=default_notebook)
        messages.success(request, f'Notebook deleted. Notes moved to {default_notebook.name}.')
        
        return super().delete(request, *args, **kwargs)


@login_required
def search_notes(request):
    """Search notes functionality."""
    form = NoteSearchForm(request.GET)
    notes = Note.objects.none()
    query = ''
    
    if form.is_valid():
        query = form.cleaned_data['q']
        if query:
            notes = Note.objects.filter(
                Q(user=request.user) | Q(shares__shared_with=request.user),
                Q(title__icontains=query) | 
                Q(content__icontains=query) |
                Q(tags__name__icontains=query)
            ).distinct().select_related('notebook').prefetch_related('tags')
    
    paginator = Paginator(notes, 12)
    page_number = request.GET.get('page')
    notes_page = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'notes': notes_page,
        'query': query,
        'total_results': notes.count() if query else 0,
    }
    
    return render(request, 'notes/search_results.html', context)


@login_required
def toggle_pin_note(request, slug):
    """Toggle note pin status."""
    note = get_object_or_404(Note, slug=slug, user=request.user)
    note.is_pinned = not note.is_pinned
    note.save()
    
    status = 'pinned' if note.is_pinned else 'unpinned'
    messages.success(request, f'Note {status} successfully!')
    
    return redirect(note.get_absolute_url())


@login_required
def toggle_archive_note(request, slug):
    """Toggle note archive status."""
    note = get_object_or_404(Note, slug=slug, user=request.user)
    note.is_archived = not note.is_archived
    note.save()
    
    status = 'archived' if note.is_archived else 'restored'
    messages.success(request, f'Note {status} successfully!')
    
    return redirect('notes:dashboard')


@login_required
def archived_notes(request):
    """View archived notes."""
    notes = Note.objects.filter(
        user=request.user,
        is_archived=True
    ).select_related('notebook').prefetch_related('tags')
    
    paginator = Paginator(notes, 12)
    page_number = request.GET.get('page')
    notes_page = paginator.get_page(page_number)
    
    context = {
        'notes': notes_page,
        'page_title': 'Archived Notes',
    }
    
    return render(request, 'notes/archived_notes.html', context)


@login_required
def move_note(request, slug):
    """Move note to a different notebook."""
    note = get_object_or_404(Note, slug=slug, user=request.user)
    
    if request.method == 'POST':
        form = NoteMoveForm(request.POST, user=request.user, current_notebook=note.notebook)
        if form.is_valid():
            new_notebook = form.cleaned_data['notebook']
            old_notebook = note.notebook
            
            note.notebook = new_notebook
            note.save()
            
            messages.success(
                request, 
                f'Note "{note.title}" moved from "{old_notebook.name}" to "{new_notebook.name}".'
            )
            return redirect(note.get_absolute_url())
    else:
        form = NoteMoveForm(user=request.user, current_notebook=note.notebook)
    
    context = {
        'note': note,
        'form': form,
    }
    
    return render(request, 'notes/note_move.html', context)


@login_required
def copy_note(request, slug):
    """Copy note to create a duplicate."""
    original_note = get_object_or_404(Note, slug=slug, user=request.user)
    
    if request.method == 'POST':
        form = NoteCopyForm(request.POST, user=request.user, original_note=original_note)
        if form.is_valid():
            # Create a new note instance
            new_note = form.save(commit=False)
            new_note.user = request.user
            new_note.content = original_note.content
            new_note.content_html = original_note.content_html
            new_note.is_archived = False  # New copies are not archived
            new_note.save()
            
            # Copy tags from original note
            for tag in original_note.tags.all():
                new_note.tags.add(tag)
            
            messages.success(
                request, 
                f'Note "{new_note.title}" copied successfully!'
            )
            return redirect(new_note.get_absolute_url())
    else:
        form = NoteCopyForm(user=request.user, original_note=original_note)
        # Set default notebook to the same as original
        if original_note.notebook:
            form.fields['notebook'].initial = original_note.notebook
    
    context = {
        'original_note': original_note,
        'form': form,
    }
    
    return render(request, 'notes/note_copy.html', context)


# Todo Views
@login_required
def todo_list(request, note_slug):
    """List todos for a specific note."""
    note = get_object_or_404(Note, slug=note_slug, user=request.user)
    todos = note.todos.all()
    
    # Filter by status
    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all':
        todos = todos.filter(status=status_filter)
    
    # Filter by priority
    priority_filter = request.GET.get('priority', 'all')
    if priority_filter != 'all':
        todos = todos.filter(priority=priority_filter)
    
    # Search todos
    search_query = request.GET.get('q', '')
    if search_query:
        todos = todos.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(tags__name__icontains=search_query)
        ).distinct()
    
    context = {
        'note': note,
        'todos': todos,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'search_query': search_query,
    }
    
    return render(request, 'notes/todo_list.html', context)


@login_required
def todo_create(request, note_slug):
    """Create a new todo for a note."""
    note = get_object_or_404(Note, slug=note_slug, user=request.user)
    
    if request.method == 'POST':
        form = TodoForm(request.POST, note=note)
        if form.is_valid():
            todo = form.save(commit=False)
            todo.note = note
            todo.save()
            form.save_m2m()  # Save tags
            
            messages.success(request, f'Todo "{todo.title}" created successfully!')
            return redirect('notes:todo_list', note_slug=note.slug)
    else:
        form = TodoForm(note=note)
    
    context = {
        'note': note,
        'form': form,
    }
    
    return render(request, 'notes/todo_form.html', context)


@login_required
def todo_edit(request, note_slug, todo_id):
    """Edit an existing todo."""
    note = get_object_or_404(Note, slug=note_slug, user=request.user)
    todo = get_object_or_404(Todo, id=todo_id, note=note)
    
    if request.method == 'POST':
        form = TodoForm(request.POST, instance=todo, note=note)
        if form.is_valid():
            form.save()
            messages.success(request, f'Todo "{todo.title}" updated successfully!')
            return redirect('notes:todo_list', note_slug=note.slug)
    else:
        form = TodoForm(instance=todo, note=note)
    
    context = {
        'note': note,
        'todo': todo,
        'form': form,
    }
    
    return render(request, 'notes/todo_form.html', context)


@login_required
def todo_delete(request, note_slug, todo_id):
    """Delete a todo."""
    note = get_object_or_404(Note, slug=note_slug, user=request.user)
    todo = get_object_or_404(Todo, id=todo_id, note=note)
    
    if request.method == 'POST':
        todo_title = todo.title
        todo.delete()
        messages.success(request, f'Todo "{todo_title}" deleted successfully!')
        return redirect('notes:todo_list', note_slug=note.slug)
    
    context = {
        'note': note,
        'todo': todo,
    }
    
    return render(request, 'notes/todo_confirm_delete.html', context)


@login_required
def todo_toggle(request, note_slug, todo_id):
    """Toggle todo completion status."""
    note = get_object_or_404(Note, slug=note_slug, user=request.user)
    todo = get_object_or_404(Todo, id=todo_id, note=note)
    
    todo.is_completed = not todo.is_completed
    todo.save()
    
    status = 'completed' if todo.is_completed else 'pending'
    messages.success(request, f'Todo "{todo.title}" marked as {status}!')
    
    return redirect('notes:todo_list', note_slug=note.slug)


@login_required
def todo_quick_add(request, note_slug):
    """Quickly add a todo via AJAX."""
    note = get_object_or_404(Note, slug=note_slug, user=request.user)
    
    if request.method == 'POST':
        form = TodoQuickForm(request.POST)
        if form.is_valid():
            todo = Todo.objects.create(
                note=note,
                title=form.cleaned_data['title'],
                priority=form.cleaned_data['priority']
            )
            
            return JsonResponse({
                'success': True,
                'todo': {
                    'id': todo.id,
                    'title': todo.title,
                    'priority': todo.priority,
                    'status': todo.status,
                    'is_completed': todo.is_completed,
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def todo_bulk_action(request, note_slug):
    """Perform bulk actions on todos."""
    note = get_object_or_404(Note, slug=note_slug, user=request.user)
    
    if request.method == 'POST':
        form = TodoBulkForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            todo_ids = form.cleaned_data['todo_ids'].split(',')
            
            todos = Todo.objects.filter(id__in=todo_ids, note=note)
            
            if action == 'complete':
                todos.update(is_completed=True, status='completed')
                message = f'{todos.count()} todos marked as completed!'
            elif action == 'pending':
                todos.update(is_completed=False, status='pending')
                message = f'{todos.count()} todos marked as pending!'
            elif action == 'in_progress':
                todos.update(status='in_progress')
                message = f'{todos.count()} todos marked as in progress!'
            elif action == 'cancelled':
                todos.update(status='cancelled')
                message = f'{todos.count()} todos marked as cancelled!'
            elif action == 'delete':
                count = todos.count()
                todos.delete()
                message = f'{count} todos deleted!'
            
            messages.success(request, message)
    
    return redirect('notes:todo_list', note_slug=note.slug)


# Attachment Views
@login_required
def attachment_upload(request, note_slug):
    """Upload single attachment to a note."""
    note = get_object_or_404(Note, slug=note_slug, user=request.user)
    
    if request.method == 'POST':
        form = AttachmentForm(request.POST, request.FILES, note=note)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.note = note
            attachment.save()
            messages.success(request, f'File "{attachment.original_name}" uploaded successfully!')
            return redirect('notes:note_detail', slug=note.slug)
    else:
        form = AttachmentForm(note=note)
    
    context = {
        'note': note,
        'form': form,
    }
    
    return render(request, 'notes/attachment_upload.html', context)


@login_required
def attachment_multiple_upload(request, note_slug):
    """Upload multiple attachments to a note."""
    note = get_object_or_404(Note, slug=note_slug, user=request.user)
    
    if request.method == 'POST':
        form = MultipleAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            files = request.FILES.getlist('files')
            uploaded_count = 0
            
            for file in files:
                attachment = NoteAttachment.objects.create(
                    note=note,
                    file=file,
                    original_name=file.name
                )
                uploaded_count += 1
            
            messages.success(request, f'{uploaded_count} files uploaded successfully!')
            return redirect('notes:note_detail', slug=note.slug)
    else:
        form = MultipleAttachmentForm()
    
    context = {
        'note': note,
        'form': form,
    }
    
    return render(request, 'notes/attachment_multiple_upload.html', context)


@login_required
def attachment_delete(request, note_slug, attachment_id):
    """Delete an attachment."""
    note = get_object_or_404(Note, slug=note_slug, user=request.user)
    attachment = get_object_or_404(NoteAttachment, id=attachment_id, note=note)
    
    if request.method == 'POST':
        attachment_name = attachment.original_name
        attachment.delete()
        messages.success(request, f'Attachment "{attachment_name}" deleted successfully!')
        return redirect('notes:note_detail', slug=note.slug)
    
    context = {
        'note': note,
        'attachment': attachment,
    }
    
    return render(request, 'notes/attachment_confirm_delete.html', context)


@login_required
def attachment_download(request, note_slug, attachment_id):
    """Download an attachment."""
    note = get_object_or_404(Note, slug=note_slug, user=request.user)
    attachment = get_object_or_404(NoteAttachment, id=attachment_id, note=note)
    
    from django.http import FileResponse
    return FileResponse(attachment.file, as_attachment=True, filename=attachment.original_name)


@login_required
def attachment_preview(request, note_slug, attachment_id):
    """Preview an attachment."""
    note = get_object_or_404(Note, slug=note_slug, user=request.user)
    attachment = get_object_or_404(NoteAttachment, id=attachment_id, note=note)
    
    if not attachment.is_previewable():
        messages.error(request, 'This file type cannot be previewed.')
        return redirect('notes:note_detail', slug=note.slug)
    
    context = {
        'note': note,
        'attachment': attachment,
    }
    
    return render(request, 'notes/attachment_preview.html', context)


@login_required
def attachment_ajax_upload(request, note_slug):
    """AJAX endpoint for drag-and-drop file uploads."""
    note = get_object_or_404(Note, slug=note_slug, user=request.user)
    
    if request.method == 'POST':
        files = request.FILES.getlist('files')
        uploaded_attachments = []
        
        for file in files:
            try:
                attachment = NoteAttachment.objects.create(
                    note=note,
                    file=file,
                    original_name=file.name
                )
                uploaded_attachments.append({
                    'id': attachment.id,
                    'name': attachment.original_name,
                    'size': attachment.get_file_size_human(),
                    'type': attachment.attachment_type,
                    'icon': attachment.get_file_icon(),
                    'is_image': attachment.is_image,
                    'thumbnail_url': attachment.thumbnail.url if attachment.thumbnail else None,
                    'url': attachment.file.url,
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': f'Error uploading {file.name}: {str(e)}'
                })
        
        return JsonResponse({
            'success': True,
            'attachments': uploaded_attachments
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def attachment_serve(request, note_slug, attachment_id):
    """Serve attachment files directly, bypassing debug toolbar."""
    from django.http import FileResponse, Http404
    from django.views.decorators.cache import never_cache
    
    note = get_object_or_404(Note, slug=note_slug, user=request.user)
    attachment = get_object_or_404(NoteAttachment, id=attachment_id, note=note)
    
    try:
        response = FileResponse(
            attachment.file,
            content_type=attachment.file_type,
            as_attachment=False
        )
        response['Content-Disposition'] = f'inline; filename="{attachment.original_name}"'
        return response
    except Exception:
        raise Http404("File not found")


@login_required
def todo_dashboard(request):
    """Global todo dashboard showing all todos with filtering options."""
    from django.utils import timezone
    
    # Get all todos for the user (both note-based and standalone)
    todos = Todo.objects.filter(user=request.user).select_related('note', 'note__notebook')
    
    # Get filter parameters
    notebook_filter = request.GET.get('notebook', 'all')
    note_filter = request.GET.get('note', 'all')
    status_filter = request.GET.get('status', 'all')
    priority_filter = request.GET.get('priority', 'all')
    search_query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', 'created')
    sort_order = request.GET.get('order', 'desc')
    
    # Apply filters
    if notebook_filter == 'standalone':
        todos = todos.filter(note__isnull=True)
    elif notebook_filter != 'all':
        try:
            notebook_id = int(notebook_filter)
            todos = todos.filter(note__notebook__id=notebook_id)
        except (ValueError, TypeError):
            pass  # Invalid notebook filter, ignore it
    
    if note_filter == 'standalone':
        todos = todos.filter(note__isnull=True)
    elif note_filter != 'all':
        try:
            note_id = int(note_filter)
            todos = todos.filter(note__id=note_id)
        except (ValueError, TypeError):
            pass  # Invalid note filter, ignore it
    
    if status_filter != 'all':
        todos = todos.filter(status=status_filter)
    
    if priority_filter != 'all':
        todos = todos.filter(priority=priority_filter)
    
    # Search functionality
    if search_query:
        todos = todos.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(tags__name__icontains=search_query) |
            Q(note__title__icontains=search_query)
        ).distinct()
    
    # Apply sorting
    if sort_order == 'desc':
        sort_by = f'-{sort_by}'
    todos = todos.order_by(sort_by)
    
    # Get filter options
    notebooks = Notebook.objects.filter(user=request.user).order_by('name')
    notes = Note.objects.filter(user=request.user).order_by('title')
    
    # Get statistics
    total_todos = todos.count()
    completed_todos = todos.filter(is_completed=True).count()
    pending_todos = todos.filter(status='pending').count()
    in_progress_todos = todos.filter(status='in_progress').count()
    overdue_todos = todos.filter(
        due_date__lt=timezone.now(),
        is_completed=False
    ).count()
    archived_notes = Note.objects.filter(user=request.user, is_archived=True).count()
    standalone_todos = Todo.objects.filter(user=request.user, note__isnull=True).count()
    
    # Pagination
    paginator = Paginator(todos, 20)
    page_number = request.GET.get('page')
    todos_page = paginator.get_page(page_number)
    
    context = {
        'todos': todos_page,
        'notebooks': notebooks,
        'notes': notes,
        'notebook_filter': notebook_filter,
        'note_filter': note_filter,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'search_query': search_query,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'total_todos': total_todos,
        'completed_todos': completed_todos,
        'pending_todos': pending_todos,
        'in_progress_todos': in_progress_todos,
        'overdue_todos': overdue_todos,
        'archived_notes': archived_notes,
        'standalone_todos': standalone_todos,
    }
    
    return render(request, 'notes/todo_dashboard.html', context)


# Standalone Todo Views
@login_required
def standalone_todo_list(request):
    """List all standalone todos for the current user."""
    todos = Todo.objects.filter(
        user=request.user,
        note__isnull=True
    ).order_by('-created')
    
    # Filtering
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    search_query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', 'created')
    sort_order = request.GET.get('order', 'desc')
    
    if status_filter:
        todos = todos.filter(status=status_filter)
    
    if priority_filter:
        todos = todos.filter(priority=priority_filter)
    
    if search_query:
        todos = todos.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(tags__name__icontains=search_query)
        ).distinct()
    
    # Sorting
    if sort_order == 'desc':
        sort_by = f'-{sort_by}'
    todos = todos.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(todos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    total_todos = todos.count()
    completed_todos = todos.filter(status='completed').count()
    pending_todos = todos.filter(status='pending').count()
    in_progress_todos = todos.filter(status='in_progress').count()
    overdue_todos = todos.filter(
        due_date__lt=timezone.now(),
        status__in=['pending', 'in_progress']
    ).count()
    
    context = {
        'todos': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'search_query': search_query,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'total_todos': total_todos,
        'completed_todos': completed_todos,
        'pending_todos': pending_todos,
        'in_progress_todos': in_progress_todos,
        'overdue_todos': overdue_todos,
    }
    
    return render(request, 'notes/standalone_todo_list.html', context)


@login_required
def standalone_todo_create(request):
    """Create a new standalone todo."""
    if request.method == 'POST':
        form = StandaloneTodoForm(request.POST, user=request.user)
        if form.is_valid():
            todo = form.save()
            messages.success(request, f'Todo "{todo.title}" created successfully!')
            return redirect('notes:standalone_todo_list')
    else:
        form = StandaloneTodoForm(user=request.user)
    
    return render(request, 'notes/standalone_todo_form.html', {'form': form})


@login_required
def standalone_todo_edit(request, pk):
    """Edit a standalone todo."""
    todo = get_object_or_404(Todo, pk=pk, user=request.user, note__isnull=True)
    
    if request.method == 'POST':
        form = StandaloneTodoForm(request.POST, instance=todo, user=request.user)
        if form.is_valid():
            todo = form.save()
            messages.success(request, f'Todo "{todo.title}" updated successfully!')
            return redirect('notes:standalone_todo_list')
    else:
        form = StandaloneTodoForm(instance=todo, user=request.user)
    
    return render(request, 'notes/standalone_todo_form.html', {'form': form, 'todo': todo})


@login_required
def standalone_todo_delete(request, pk):
    """Delete a standalone todo."""
    todo = get_object_or_404(Todo, pk=pk, user=request.user, note__isnull=True)
    
    if request.method == 'POST':
        todo_title = todo.title
        todo.delete()
        messages.success(request, f'Todo "{todo_title}" deleted successfully!')
        return redirect('notes:standalone_todo_list')
    
    return render(request, 'notes/standalone_todo_confirm_delete.html', {'todo': todo})


@login_required
def standalone_todo_toggle(request, pk):
    """Toggle completion status of a standalone todo."""
    todo = get_object_or_404(Todo, pk=pk, user=request.user, note__isnull=True)
    
    if request.method == 'POST':
        todo.is_completed = not todo.is_completed
        todo.save()
        
        return JsonResponse({
            'success': True,
            'is_completed': todo.is_completed,
            'message': f'Todo {"completed" if todo.is_completed else "marked as pending"}'
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required
def standalone_todo_quick_add(request):
    """Quick add a standalone todo via AJAX."""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        priority = request.POST.get('priority', 'medium')
        
        if title:
            todo = Todo.objects.create(
                user=request.user,
                title=title,
                priority=priority,
                note=None  # Standalone
            )
            
            return JsonResponse({
                'success': True,
                'todo': {
                    'id': todo.id,
                    'title': todo.title,
                    'priority': todo.priority,
                    'status': todo.status,
                    'is_completed': todo.is_completed,
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Title is required'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


# Notebook Delete View
class NotebookDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a notebook and move its notes to default notebook."""
    model = Notebook
    template_name = 'notes/notebook_confirm_delete.html'
    success_url = reverse_lazy('notes:notebook_list')
    
    def get_queryset(self):
        return Notebook.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        notebook = self.get_object()
        
        # Get notes that will be moved to default notebook
        notes_to_move = notebook.notes.all()
        
        # Get or create default notebook
        default_notebook, created = Notebook.objects.get_or_create(
            user=self.request.user,
            is_default=True,
            defaults={
                'name': 'Default',
                'description': 'Default notebook for notes without a specific notebook',
                'color': '#6c757d'
            }
        )
        
        context.update({
            'notes_to_move': notes_to_move,
            'default_notebook': default_notebook,
            'archived_notes': self.request.user.notes.filter(is_archived=True).count(),
            'standalone_todos': self.request.user.todos.filter(note__isnull=True).count(),
        })
        return context
    
    def delete(self, request, *args, **kwargs):
        notebook = self.get_object()
        
        # Get or create default notebook
        default_notebook, created = Notebook.objects.get_or_create(
            user=request.user,
            is_default=True,
            defaults={
                'name': 'Default',
                'description': 'Default notebook for notes without a specific notebook',
                'color': '#6c757d'
            }
        )
        
        # Move all notes from this notebook to default notebook
        notes_to_move = notebook.notes.all()
        for note in notes_to_move:
            note.notebook = default_notebook
            note.save()
        
        # Delete the notebook
        notebook_name = notebook.name
        notebook.delete()
        
        messages.success(
            request, 
            f'Notebook "{notebook_name}" has been deleted. {notes_to_move.count()} notes have been moved to the default notebook.'
        )
        
        return super().delete(request, *args, **kwargs)
