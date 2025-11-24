from django import forms
from django.contrib.auth import get_user_model
from .models import Note, Notebook, NoteAttachment, Todo
from taggit.forms import TagWidget

User = get_user_model()


class NoteForm(forms.ModelForm):
    """Form for creating and editing notes."""
    
    class Meta:
        model = Note
        fields = ['title', 'content', 'notebook', 'tags', 'is_pinned', 'is_public']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Note title...',
                'required': True,
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control tinymce-editor',
                'rows': 15,
                'placeholder': 'Start writing your note...',
                'id': 'note-editor',
            }),
            'notebook': forms.Select(attrs={
                'class': 'form-select',
            }),
            'tags': TagWidget(attrs={
                'class': 'form-control',
                'placeholder': 'Add tags (comma separated)...',
            }),
            'is_pinned': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Limit notebook choices to user's notebooks
            self.fields['notebook'].queryset = Notebook.objects.filter(user=self.user)
            self.fields['notebook'].empty_label = "Choose a notebook..."


class NotebookForm(forms.ModelForm):
    """Form for creating and editing notebooks."""
    
    class Meta:
        model = Notebook
        fields = ['name', 'description', 'color']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Notebook name...',
                'required': True,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe your notebook...',
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
                'title': 'Choose notebook color',
            }),
        }


class NoteAttachmentForm(forms.ModelForm):
    """Form for uploading note attachments."""
    
    class Meta:
        model = NoteAttachment
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.txt,.jpg,.jpeg,.png,.gif',
            }),
        }


class NoteMoveForm(forms.Form):
    """Form for moving notes between notebooks."""
    
    notebook = forms.ModelChoiceField(
        queryset=Notebook.objects.none(),
        required=True,
        empty_label="Select a notebook...",
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.current_notebook = kwargs.pop('current_notebook', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Exclude the current notebook from the choices
            queryset = Notebook.objects.filter(user=self.user)
            if self.current_notebook:
                queryset = queryset.exclude(id=self.current_notebook.id)
            self.fields['notebook'].queryset = queryset


class NoteCopyForm(forms.ModelForm):
    """Form for copying notes."""
    
    class Meta:
        model = Note
        fields = ['title', 'notebook', 'is_pinned', 'is_public']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter title for the copy...',
                'required': True,
            }),
            'notebook': forms.Select(attrs={
                'class': 'form-select',
            }),
            'is_pinned': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.original_note = kwargs.pop('original_note', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Limit notebook choices to user's notebooks
            self.fields['notebook'].queryset = Notebook.objects.filter(user=self.user)
            self.fields['notebook'].empty_label = "Choose a notebook..."
        
        # Set default title if copying
        if self.original_note and not self.instance.pk:
            self.fields['title'].initial = f"Copy of {self.original_note.title}"


class NoteSearchForm(forms.Form):
    """Form for searching notes."""
    
    q = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search notes, tags, or content...',
            'autocomplete': 'off',
        })
    )
    
    notebook = forms.ModelChoiceField(
        queryset=Notebook.objects.none(),
        required=False,
        empty_label="All notebooks",
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    
    tags = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by tags...',
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['notebook'].queryset = Notebook.objects.filter(user=self.user)


class TodoForm(forms.ModelForm):
    """Form for creating and editing todos."""
    
    class Meta:
        model = Todo
        fields = ['title', 'description', 'priority', 'status', 'due_date', 'tags']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter todo title...',
                'required': True,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add description (optional)...',
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select',
            }),
            'status': forms.Select(attrs={
                'class': 'form-select',
            }),
            'due_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }),
            'tags': TagWidget(attrs={
                'class': 'form-control',
                'placeholder': 'Add tags (comma separated)...',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.note = kwargs.pop('note', None)
        super().__init__(*args, **kwargs)
        
        # Set default due date to tomorrow
        if not self.instance.pk and not self.initial.get('due_date'):
            from django.utils import timezone
            from datetime import timedelta
            tomorrow = timezone.now() + timedelta(days=1)
            self.fields['due_date'].initial = tomorrow.strftime('%Y-%m-%dT%H:%M')
    
    def save(self, commit=True):
        todo = super().save(commit=False)
        if self.note:
            todo.note = self.note
        if commit:
            todo.save()
        return todo


class StandaloneTodoForm(forms.ModelForm):
    """Form for creating and editing standalone todos (not linked to notes)."""
    
    class Meta:
        model = Todo
        fields = ['title', 'description', 'priority', 'status', 'due_date', 'tags']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter todo title...',
                'required': True,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add description (optional)...',
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select',
            }),
            'status': forms.Select(attrs={
                'class': 'form-select',
            }),
            'due_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }),
            'tags': TagWidget(attrs={
                'class': 'form-control',
                'placeholder': 'Add tags (comma separated)...',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set default due date to tomorrow
        if not self.instance.pk and not self.initial.get('due_date'):
            from django.utils import timezone
            from datetime import timedelta
            tomorrow = timezone.now() + timedelta(days=1)
            self.fields['due_date'].initial = tomorrow.strftime('%Y-%m-%dT%H:%M')
    
    def save(self, commit=True):
        todo = super().save(commit=False)
        if self.user:
            todo.user = self.user
        todo.note = None  # Ensure it's standalone
        if commit:
            todo.save()
        return todo


class TodoQuickForm(forms.Form):
    """Quick form for adding todos inline."""
    
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Add a new todo...',
            'autocomplete': 'off',
        })
    )
    
    priority = forms.ChoiceField(
        choices=Todo.PRIORITY_CHOICES,
        initial='medium',
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )


class TodoBulkForm(forms.Form):
    """Form for bulk todo operations."""
    
    ACTION_CHOICES = [
        ('complete', 'Mark as Completed'),
        ('pending', 'Mark as Pending'),
        ('in_progress', 'Mark as In Progress'),
        ('cancelled', 'Mark as Cancelled'),
        ('delete', 'Delete Selected'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    
    todo_ids = forms.CharField(
        widget=forms.HiddenInput()
    )


class AttachmentForm(forms.ModelForm):
    """Form for uploading file attachments."""
    
    class Meta:
        model = NoteAttachment
        fields = ['file', 'description']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,application/pdf,.doc,.docx,.txt,.rtf,.odt,audio/*,video/*,.zip,.rar,.7z,.tar,.gz',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add a description for this attachment (optional)...',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.note = kwargs.pop('note', None)
        super().__init__(*args, **kwargs)
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (max 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if file.size > max_size:
                raise forms.ValidationError(f'File size cannot exceed 10MB. Current size: {file.size / (1024*1024):.1f}MB')
        return file


class MultipleAttachmentForm(forms.Form):
    """Form for uploading multiple attachments at once."""
    
    files = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*,application/pdf,.doc,.docx,.txt,.rtf,.odt,audio/*,video/*,.zip,.rar,.7z,.tar,.gz',
        }),
        help_text='Select multiple files to upload (max 10MB each)'
    )
    
    def clean_files(self):
        files = self.files.getlist('files')
        if not files:
            raise forms.ValidationError('Please select at least one file.')
        
        max_size = 10 * 1024 * 1024  # 10MB
        for file in files:
            if file.size > max_size:
                raise forms.ValidationError(f'File "{file.name}" exceeds 10MB limit.')
        
        return files









