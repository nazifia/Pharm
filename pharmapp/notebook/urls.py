from django.urls import path
from . import views

app_name = 'notebook'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Note management
    path('notes/', views.note_list, name='note_list'),
    path('notes/create/', views.note_create, name='note_create'),
    path('notes/<int:pk>/', views.note_detail, name='note_detail'),
    path('notes/<int:pk>/edit/', views.note_edit, name='note_edit'),
    path('notes/<int:pk>/delete/', views.note_delete, name='note_delete'),
    path('notes/<int:pk>/delete/permanent/', views.permanent_delete_note, name='permanent_delete_note'),
    path('notes/<int:pk>/delete/ajax/', views.note_delete_ajax, name='note_delete_ajax'),
    path('notes/<int:pk>/archive/', views.note_archive, name='note_archive'),
    path('notes/<int:pk>/pin/', views.note_pin, name='note_pin'),

    # Bulk operations
    path('notes/bulk-delete/', views.bulk_delete_notes, name='bulk_delete_notes'),
    path('undo-delete/', views.undo_delete, name='undo_delete'),
    
    # Archived notes
    path('archived/', views.archived_notes, name='archived_notes'),
    
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),

    # API endpoints
    path('api/quick-create/', views.quick_note_create, name='quick_note_create'),
    path('api/search/', views.note_search_api, name='note_search_api'),
    path('api/new-notes-count/', views.new_notes_count_api, name='new_notes_count_api'),

    # Tag-based filtering
    path('tags/<str:tag>/', views.notes_by_tag, name='notes_by_tag'),
]
