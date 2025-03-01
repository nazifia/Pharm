from django.urls import path
from . import views

app_name = 'offline'

urlpatterns = [
    path('', views.offline_page, name='offline_page'),
    path('cache-data/', views.cache_data, name='cache_data'),
    path('store-action/', views.store_offline_action, name='store_action'),
    path('sync/', views.sync_offline_actions, name='sync'),
]
