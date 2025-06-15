from django.urls import path
from . import views

app_name = 'userauth'

urlpatterns = [
    path('register', views.register_view, name='register'),
    path('profile/', views.edit_user_profile, name='profile'),
    path('activity/', views.activity_dashboard, name='activity_dashboard'),
    path('activity/generate-test-logs/', views.generate_test_logs, name='generate_test_logs'),
    path('permissions/', views.permissions_management, name='permissions_management'),

    # User management URLs
    path('users/', views.user_list, name='user_list'),
    path('users/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('users/delete/<int:user_id>/', views.delete_user, name='delete_user'),
    path('users/toggle-status/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
    path('users/details/<int:user_id>/', views.user_details, name='user_details'),
    path('users/bulk-actions/', views.bulk_user_actions, name='bulk_user_actions'),
    path('privilege-management/', views.privilege_management_view, name='privilege_management_view'),
    path('api/user-permissions/<int:user_id>/', views.get_user_permissions, name='get_user_permissions'),
]