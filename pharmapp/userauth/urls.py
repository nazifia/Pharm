from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = 'userauth'

def root_redirect(request):
    """Redirect root URL to store login page"""
    return redirect('store:index')

urlpatterns = [
    path('', root_redirect, name='root'),
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
    path('users/assign-cashier/<int:user_id>/', views.assign_cashier_role, name='assign_cashier_role'),
    path('users/toggle-cashier/<int:user_id>/', views.toggle_cashier_status, name='toggle_cashier_status'),
    path('users/bulk-actions/', views.bulk_user_actions, name='bulk_user_actions'),
    path('privilege-management/', views.privilege_management_view, name='privilege_management_view'),
    path('enhanced-privilege-management/', views.enhanced_privilege_management_view, name='enhanced_privilege_management_view'),

    # Enhanced privilege management API endpoints
    path('api/user-permissions/<int:user_id>/', views.user_permissions_api, name='user_permissions_api'),
    path('api/save-user-permissions/', views.save_user_permissions_api, name='save_user_permissions_api'),
    path('api/bulk-operations/', views.bulk_operations_api, name='bulk_operations_api'),
    
    path('api/legacy-user-permissions/<int:user_id>/', views.get_user_permissions, name='get_user_permissions'),
    path('api/users/', views.get_all_users_api, name='get_all_users_api'),
    path('bulk-permission-management/', views.bulk_permission_management, name='bulk_permission_management'),

    # Cashier Management API endpoints
    path('api/cashiers/', views.cashier_management_api, name='cashier_management_api'),
    path('api/available-users/', views.available_users_api, name='available_users_api'),
    path('api/cashier/<int:cashier_id>/', views.update_cashier_api, name='update_cashier_api'),
]