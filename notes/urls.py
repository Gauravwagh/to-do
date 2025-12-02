from django.urls import path
from . import views

app_name = 'notes'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Notes
    path('note/new/', views.NoteCreateView.as_view(), name='note_create'),
    path('note/<slug:slug>/', views.NoteDetailView.as_view(), name='note_detail'),
    path('note/<slug:slug>/edit/', views.NoteUpdateView.as_view(), name='note_edit'),
    path('note/<slug:slug>/delete/', views.NoteDeleteView.as_view(), name='note_delete'),
    path('note/<slug:slug>/pin/', views.toggle_pin_note, name='note_pin'),
    path('note/<slug:slug>/archive/', views.toggle_archive_note, name='note_archive'),

    # Notebooks
    path('notebooks/', views.NotebookListView.as_view(), name='notebook_list'),
    path('notebook/new/', views.NotebookCreateView.as_view(), name='notebook_create'),
    path('notebook/<slug:slug>/', views.NotebookDetailView.as_view(), name='notebook_detail'),
    path('notebook/<slug:slug>/edit/', views.NotebookUpdateView.as_view(), name='notebook_edit'),
    path('notebook/<slug:slug>/delete/', views.NotebookDeleteView.as_view(), name='notebook_delete'),

    # Search and Archive
    path('search/', views.search_notes, name='search'),
    path('archived/', views.archived_notes, name='archived'),

    # Todo Dashboard
    path('todos/', views.todo_dashboard, name='todo_dashboard'),

    # Note Actions
    path('note/<slug:slug>/move/', views.move_note, name='note_move'),
    path('note/<slug:slug>/copy/', views.copy_note, name='note_copy'),

    # Todo Management
    path('note/<slug:note_slug>/todos/', views.todo_list, name='todo_list'),
    path('note/<slug:note_slug>/todos/new/', views.todo_create, name='todo_create'),
    path('note/<slug:note_slug>/todos/<int:todo_id>/edit/', views.todo_edit, name='todo_edit'),
    path('note/<slug:note_slug>/todos/<int:todo_id>/delete/', views.todo_delete, name='todo_delete'),
    path('note/<slug:note_slug>/todos/<int:todo_id>/toggle/', views.todo_toggle, name='todo_toggle'),
    path('note/<slug:note_slug>/todos/quick-add/', views.todo_quick_add, name='todo_quick_add'),
    path('note/<slug:note_slug>/todos/bulk-action/', views.todo_bulk_action, name='todo_bulk_action'),

    # Attachment Management
    path('note/<slug:note_slug>/attachments/upload/', views.attachment_upload, name='attachment_upload'),
    path('note/<slug:note_slug>/attachments/multiple-upload/', views.attachment_multiple_upload, name='attachment_multiple_upload'),
    path('note/<slug:note_slug>/attachments/<int:attachment_id>/delete/', views.attachment_delete, name='attachment_delete'),
    path('note/<slug:note_slug>/attachments/<int:attachment_id>/download/', views.attachment_download, name='attachment_download'),
    path('note/<slug:note_slug>/attachments/<int:attachment_id>/preview/', views.attachment_preview, name='attachment_preview'),
    path('note/<slug:note_slug>/attachments/<int:attachment_id>/serve/', views.attachment_serve, name='attachment_serve'),
    path('note/<slug:note_slug>/attachments/ajax-upload/', views.attachment_ajax_upload, name='attachment_ajax_upload'),

    # Standalone Todo URLs
    path('standalone-todos/', views.standalone_todo_list, name='standalone_todo_list'),
    path('standalone-todos/create/', views.standalone_todo_create, name='standalone_todo_create'),
    path('standalone-todos/<int:pk>/edit/', views.standalone_todo_edit, name='standalone_todo_edit'),
    path('standalone-todos/<int:pk>/delete/', views.standalone_todo_delete, name='standalone_todo_delete'),
    path('standalone-todos/<int:pk>/toggle/', views.standalone_todo_toggle, name='standalone_todo_toggle'),
    path('standalone-todos/quick-add/', views.standalone_todo_quick_add, name='standalone_todo_quick_add'),

    # Sentry test (remove after testing)
    path('sentry-test/', views.sentry_test_error, name='sentry_test'),
]
