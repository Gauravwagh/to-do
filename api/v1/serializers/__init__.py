"""
API v1 Serializers.
"""
from .notes import (
    NotebookListSerializer,
    NotebookDetailSerializer,
    NotebookCreateUpdateSerializer,
    NoteListSerializer,
    NoteDetailSerializer,
    NoteCreateUpdateSerializer,
    NoteCopySerializer,
    NoteMoveSerializer,
    NoteAttachmentSerializer,
    SharedNoteSerializer,
    NoteVersionSerializer,
)
from .todos import (
    TodoListSerializer,
    TodoDetailSerializer,
    TodoCreateUpdateSerializer,
    TodoBulkUpdateSerializer,
)
from .tags import TagSerializer

__all__ = [
    # Notebooks
    'NotebookListSerializer',
    'NotebookDetailSerializer',
    'NotebookCreateUpdateSerializer',
    # Notes
    'NoteListSerializer',
    'NoteDetailSerializer',
    'NoteCreateUpdateSerializer',
    'NoteCopySerializer',
    'NoteMoveSerializer',
    'NoteAttachmentSerializer',
    'SharedNoteSerializer',
    'NoteVersionSerializer',
    # Todos
    'TodoListSerializer',
    'TodoDetailSerializer',
    'TodoCreateUpdateSerializer',
    'TodoBulkUpdateSerializer',
    # Tags
    'TagSerializer',
]
