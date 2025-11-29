from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('inventory/sync/', views.inventory_sync, name='inventory_sync'),
    path('sales/sync/', views.sales_sync, name='sales_sync'),
    path('customers/sync/', views.customers_sync, name='customers_sync'),
    path('suppliers/sync/', views.suppliers_sync, name='suppliers_sync'),
    path('wholesale/sync/', views.wholesale_sync, name='wholesale_sync'),
    path('receipts/sync/', views.receipts_sync, name='receipts_sync'),
    path('dispensing/sync/', views.dispensing_sync, name='dispensing_sync'),
    path('cart/sync/', views.cart_sync, name='cart_sync'),
    path('wholesale-cart/sync/', views.wholesale_cart_sync, name='wholesale_cart_sync'),
    path('data/initial/', views.get_initial_data, name='get_initial_data'),
    # Barcode scanning endpoints
    path('barcode/lookup/', views.barcode_lookup, name='barcode_lookup'),
    path('barcode/assign/', views.assign_barcode, name='assign_barcode'),
    path('barcode/batch-lookup/', views.barcode_batch_lookup, name='barcode_batch_lookup'),
]