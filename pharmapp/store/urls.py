from django.urls import path, register_converter 
from.converters import ShortUUIDConverter
from . import views


# Register the ShortUUIDConverter
register_converter(ShortUUIDConverter, 'shortuuid')


app_name = 'store'

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout_user/', views.logout_user, name='logout_user'),
    path('store/', views.store, name='store'),
    path('search_item/', views.search_item, name='search_item'),
    path('add_item/', views.add_item, name='add_item'),
    path('edit_item/<int:pk>/', views.edit_item, name='edit_item'),
    path('return_item/<int:pk>/', views.return_item, name='return_item'),
    path('delete_item/<int:pk>/', views.delete_item, name='delete_item'),
    path('dispense/', views.dispense, name='dispense'),
    path('cart/', views.cart, name='cart'),
    path('add_to_cart/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('view_cart/', views.view_cart, name='view_cart'),
    path('update_cart_quantity/<int:pk>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('clear_cart/', views.clear_cart, name='clear_cart'),
    path('receipt/', views.receipt, name='receipt'),
    path('receipts/<str:receipt_id>/', views.receipt_detail, name='receipt_detail'),
    path('register_customers/', views.register_customers, name='register_customers'),
    path('customer_list/', views.customer_list, name='customer_list'),
    path('edit_customer/<int:pk>/', views.edit_customer, name='edit_customer'),
    path('customers_on_negative/', views.customers_on_negative, name='customers_on_negative'),
    path('wallet_details/<int:pk>/', views.wallet_details, name='wallet_details'),
    path('add_funds/<int:pk>/', views.add_funds, name='add_funds'),
    path('reset_wallet/<int:pk>/', views.reset_wallet, name='reset_wallet'),
    path('delete_customer/<int:pk>/', views.delete_customer, name='delete_customer'),
    path('select_items/<int:pk>/', views.select_items, name='select_items'),
    path('dispensing_log/', views.dispensing_log, name='dispensing_log'),
    path('receipt_list/', views.receipt_list, name='receipt_list'),
    path('search_receipts/', views.search_receipts, name='search_receipts'),
    path('daily_sales/', views.daily_sales, name='daily_sales'),
    path('monthly_sales/', views.monthly_sales, name='monthly_sales'),
    path('sales_by_user/', views.sales_by_user, name='sales_by_user'),
    path('exp_date_alert/', views.exp_date_alert, name='exp_date_alert'),
    path('customer_history/<int:pk>/', views.customer_history, name='customer_history'),
    path('register_supplier_view/', views.register_supplier_view, name='register_supplier_view'),
    path('list_suppliers_view/', views.list_suppliers_view, name='supplier_list'),
    path('procurement_list/', views.procurement_list, name='procurement_list'),
    path('add_procurement/', views.add_procurement, name='add_procurement'),
    path('search_procurement/', views.search_procurement, name='search_procurement'),
    path('procurement_detail/<int:procurement_id>/', views.procurement_detail, name='procurement_detail'),
    path('suppliers/', views.list_suppliers_view, name='list_suppliers'),    
]
