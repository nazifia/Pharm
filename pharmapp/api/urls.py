from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('inventory/sync/', views.inventory_sync, name='inventory_sync'),
    path('sales/sync/', views.sales_sync, name='sales_sync'),
    path('customers/sync/', views.customers_sync, name='customers_sync'),
    path('suppliers/sync/', views.suppliers_sync, name='suppliers_sync'),
    path('wholesale/sync/', views.wholesale_sync, name='wholesale_sync'),
    path('data/initial/', views.get_initial_data, name='get_initial_data'),
]