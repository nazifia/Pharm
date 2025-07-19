from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # path("sync-offline-actions/", sync_offline_actions, name="sync-offline-actions"),
    path('index/', views.login_view, name='index'),
    path('offline/', views.offline_view, name='offline'),
    path('sync-offline-actions/', views.sync_offline_actions, name='sync_offline_actions'),

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
    path('dispensing_log_search_suggestions/', views.dispensing_log_search_suggestions, name='dispensing_log_search_suggestions'),
    path('dispensing_log_stats/', views.dispensing_log_stats, name='dispensing_log_stats'),
    path('receipt_list/', views.receipt_list, name='receipt_list'),
    path('search_receipts/', views.search_receipts, name='search_receipts'),
    path('daily_sales/', views.daily_sales, name='daily_sales'),
    path('monthly_sales/', views.monthly_sales, name='monthly_sales'),
    path('sales_by_user/', views.sales_by_user, name='sales_by_user'),
    path('exp_date_alert/', views.exp_date_alert, name='exp_date_alert'),
    path('customer_history/<int:customer_id>/', views.customer_history, name='customer_history'),
    path('register_supplier_view/', views.register_supplier_view, name='register_supplier_view'),
    path('list_suppliers_view/', views.list_suppliers_view, name='supplier_list'),
    path('edit_supplier/<int:pk>/', views.edit_supplier, name='edit_supplier'),
    path('delete_supplier/<int:pk>/', views.delete_supplier, name='delete_supplier'),
    path('procurement_list/', views.procurement_list, name='procurement_list'),
    path('add_procurement/', views.add_procurement, name='add_procurement'),
    path('search_procurement/', views.search_procurement, name='search_procurement'),
    path('procurement_detail/<int:procurement_id>/', views.procurement_detail, name='procurement_detail'),
    path('suppliers/', views.list_suppliers_view, name='list_suppliers'),
    path('register_supplier_view/partials/supplier_list.html', views.supplier_list_partial),

    # Stock Check URLs
    path('create/', views.create_stock_check, name='create_stock_check'),
    path('<int:stock_check_id>/update/', views.update_stock_check, name='update_stock_check'),
    path('<int:stock_check_id>/report/', views.stock_check_report, name='stock_check_report'),
    path('stock-check/<int:stock_check_id>/approve/', views.approve_stock_check, name='approve_stock_check'),
    path('stock-check/<int:stock_check_id>/bulk-adjust/', views.bulk_adjust_stock, name='bulk_adjust_stock'),
    path('list/', views.list_stock_checks, name='list_stock_checks'),
    path('adjust-stock/<int:stock_item_id>/', views.adjust_stock, name='adjust_stock'),
    path('search-items/', views.search_items, name='search_items'),
    path('search-store-items/', views.search_store_items, name='search_store_items'),

    # Transfer Request URLs
    path("transfer/create/", views.create_transfer_request_wholesale, name="create_transfer_request_wholesale"),
    path("pending_transfer_requests/", views.pending_transfer_requests, name="pending_transfer_requests"),
    path("transfer/approve/<int:transfer_id>/", views.approve_transfer, name="approve_transfer"),
    path("transfer/reject/<int:transfer_id>/", views.reject_transfer, name="reject_transfer"),
    path("transfer_request_list/", views.transfer_request_list, name="transfer_request_list"),
    path("transfer/multiple/", views.transfer_multiple_store_items, name="transfer_multiple_store_items"),

    # Expense URLs
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/form/', views.add_expense_form, name='add_expense_form'),
    path('expenses/add/', views.add_expense, name='add_expense'),
    path('expenses/edit/<int:expense_id>/', views.edit_expense_form, name='edit_expense_form'),
    path('expenses/update/<int:expense_id>/', views.update_expense, name='update_expense'),
    path('expenses/delete/<int:expense_id>/', views.delete_expense, name='delete_expense'),
    path('monthly-sales-deduction/', views.monthly_sales_with_deduction, name='monthly_sales_deduction'),
    path('expense-category/form/', views.add_expense_category_form, name='add_expense_category_form'),
    path('expense-category/add/', views.add_expense_category, name='add_expense_category'),
    path('expenses/report/', views.generate_monthly_report, name='generate_monthly_report'),

    # Stock Adjustment URLs
    path('adjust-stock-levels/', views.adjust_stock_levels, name='adjust_stock_levels'),
    path('search-for-adjustment/', views.search_for_adjustment, name='search_for_adjustment'),
    path('adjust-stock-level/<int:item_id>/', views.adjust_stock_level, name='adjust_stock_level'),
    path('update-marquee/', views.update_marquee, name='update_marquee'),
    path('complete_customer_history/<int:customer_id>/', views.complete_customer_history, name='complete_customer_history'),

    # Wallet Transaction History URLs
    path('wallet_transaction_history/<int:customer_id>/', views.wallet_transaction_history, name='wallet_transaction_history'),
    path('wholesale_wallet_transaction_history/<int:customer_id>/', views.wholesale_wallet_transaction_history, name='wholesale_wallet_transaction_history'),

    # User Dispensing Summary URLs
    path('user_dispensing_summary/', views.user_dispensing_summary, name='user_dispensing_summary'),
    path('user_dispensing_details/', views.user_dispensing_details, name='user_dispensing_details'),
    path('user_dispensing_details/<int:user_id>/', views.user_dispensing_details, name='user_dispensing_details_user'),

    # Stock Check Enhancement URLs
    path('add_items_to_stock_check/<int:stock_check_id>/', views.add_items_to_stock_check, name='add_items_to_stock_check'),
]
