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
    path('enhanced-privilege-management/', views.enhanced_privilege_management_view, name='enhanced_privilege_management_view'),

    # Enhanced privilege management API endpoints
    path('api/user-permissions/<int:user_id>/', views.user_permissions_api, name='user_permissions_api'),
    path('api/save-user-permissions/', views.save_user_permissions_api, name='save_user_permissions_api'),
    path('api/bulk-operations/', views.bulk_operations_api, name='bulk_operations_api'),
    path('api/permission-matrix/', views.permission_matrix_api, name='permission_matrix_api'),
    path('api/privilege-statistics/', views.privilege_statistics_api, name='privilege_statistics_api'),
    path('api/all-permissions/', views.all_permissions_api, name='all_permissions_api'),
    path('api/export-permissions/', views.export_permissions_api, name='export_permissions_api'),
    path('api/user-audit-trail/<int:user_id>/', views.user_audit_trail_api, name='user_audit_trail_api'),
    path('api/grant-user-permission/', views.grant_user_permission_api, name='grant_user_permission_api'),
    path('api/revoke-user-permission/', views.revoke_user_permission_api, name='revoke_user_permission_api'),
    path('api/legacy-user-permissions/<int:user_id>/', views.get_user_permissions, name='get_user_permissions'),
    path('api/users/', views.get_all_users_api, name='get_all_users_api'),
    path('bulk-permission-management/', views.bulk_permission_management, name='bulk_permission_management'),
]