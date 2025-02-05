from django.urls import path
from . import views

app_name = 'userauth'

urlpatterns = [
    path('register', views.register_view, name='register'),
    path('profile/', views.edit_user_profile, name='profile'),
]