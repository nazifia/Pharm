from django.urls import path
from . import views

app_name = 'userauth'

urlpatterns = [
    path('register', views.register_view, name='register'),
    path('profile/', views.edit_user_profile, name='profile'),
    path('activity/', views.activity_dashboard, name='activity_dashboard'),
    path('activity/generate-test-logs/', views.generate_test_logs, name='generate_test_logs'),
    path('permissions/', views.permissions_management, name='permissions_management'),
]