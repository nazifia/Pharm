from django.urls import path
from . import views

app_name = 'wholesale'

urlpatterns = [
    path('wholesale_page/', views.wholesale_page, name='wholesale_page'),
    path('wholesale_dashboard/', views.wholesale_dashboard, name='wholesale_dashboard'),
    path('wholesales/', views.wholesales, name='wholesales'),
    path('add_to_wholesale/', views.add_to_wholesale, name='add_to_wholesale'),
    path('edit_wholesale_item/<int:pk>/', views.edit_wholesale_item, name='edit_wholesale_item'),
    path('return_wholesale_item/<int:pk>/', views.return_wholesale_item, name='return_wholesale_item'),
    path('delete_wholesale_item/<int:pk>/', views.delete_wholesale_item, name='delete_wholesale_item'),
    path('search_wholesale_item/', views.search_wholesale_item, name='search_wholesale_item'),
    path('add_to_wholesale_cart/<int:item_id>/', views.add_to_wholesale_cart, name='add_to_wholesale_cart'),
    path('dispense_wholesale/', views.test_template_view, name='dispense_wholesale'),
    path('wholesale-dispense-search-items/', views.wholesale_dispense_search_items, name='wholesale_dispense_search_items'),
    path('dispense_wholesale_simple/', views.dispense_wholesale_simple, name='dispense_wholesale_simple'),
    path('debug_dispense_wholesale/', views.debug_dispense_wholesale, name='debug_dispense_wholesale'),
    path('auth_test_wholesale/', views.auth_test_wholesale, name='auth_test_wholesale'),
    path('dispense_wholesale_no_auth/', views.dispense_wholesale_no_auth, name='dispense_wholesale_no_auth'),
    path('test_wholesale_page/', views.test_wholesale_page, name='test_wholesale_page'),
    path('simple_wholesale_test/', views.simple_wholesale_test, name='simple_wholesale_test'),
    path('minimal_test/', views.minimal_test, name='minimal_test'),
    path('test_template/', views.test_template_view, name='test_template'),
    path('wholesale_cart/', views.wholesale_cart, name='wholesale_cart'),
    path('clear_wholesale_cart/', views.clear_wholesale_cart, name='clear_wholesale_cart'),
    path('update_wholesale_cart_quantity/<int:pk>/', views.update_wholesale_cart_quantity, name='update_wholesale_cart_quantity'),
    path('wholesale_receipt/', views.wholesale_receipt, name='wholesale_receipt'),
    path('wholesale_receipt_list/', views.wholesale_receipt_list, name='wholesale_receipt_list'),
    path('wholesale_receipt_detail/<str:receipt_id>/', views.wholesale_receipt_detail, name='wholesale_receipt_detail'),
    path('wholesale_customers_on_negative/', views.wholesale_customers_on_negative, name='wholesale_customers_on_negative'),
    path('wholesale_customers/', views.wholesale_customers, name='wholesale_customers'),
    path('register_wholesale_customers/', views.register_wholesale_customers, name='register_wholesale_customers'),
    path('edit_wholesale_customer/<int:pk>/', views.edit_wholesale_customer, name='edit_wholesale_customer'),
    path('reset_wholesale_customer_wallet/<int:pk>/', views.reset_wholesale_customer_wallet, name='reset_wholesale_customer_wallet'),
    path('delete_wholesale_customer/<int:pk>/', views.delete_wholesale_customer, name='delete_wholesale_customer'),
    path('wholesale_customer_wallet_details/<int:pk>/', views.wholesale_customer_wallet_details, name='wholesale_customer_wallet_details'),
    path('wholesale_customer_add_funds/<int:pk>/', views.wholesale_customer_add_funds, name='wholesale_customer_add_funds'),
    path('wholesale_customer_add_funds/<int:pk>/', views.wholesale_customer_add_funds, name='wholesale_customer_add_funds'),
    path('wholesale_transactions/<int:customer_id>/', views.wholesale_transactions, name='wholesale_transactions'),
    path('select_wholesale_items/<int:pk>/', views.select_wholesale_items, name='select_wholesale_items'),
    path('wholesale/select_wholesale_items/<int:pk>/', views.select_wholesale_items, name='select_wholesale_items_alt'),
    path('wholesale_exp_alert/', views.wholesale_exp_alert, name='wholesale_exp_alert'),
    path('wholesale_receipt_list/', views.wholesale_receipt_list, name='wholesale_receipt_list'),
    path('wholesale_customer_history/<int:customer_id>/', views.wholesale_customer_history, name='wholesale_customer_history'),
    path('search_wholesale_receipts/', views.search_wholesale_receipts, name='search_wholesale_receipts'),
    path('complete_wholesale_customer_history/<int:customer_id>/', views.complete_wholesale_customer_history, name='complete_wholesale_customer_history'),
    
    # Wholesale Cashier URLs - adapted from retail
    path('send_to_cashier/', views.send_to_wholesale_cashier, name='send_to_wholesale_cashier'),
    path('payment_requests/', views.wholesale_payment_requests, name='wholesale_payment_requests'),
    path('payment_request/<str:request_id>/', views.wholesale_payment_request_detail, name='wholesale_payment_request_detail'),
    path('cashier_dashboard/', views.wholesale_cashier_dashboard, name='wholesale_cashier_dashboard'),
    path('accept_wholesale_payment_request/<str:request_id>/', views.accept_wholesale_payment_request, name='accept_wholesale_payment_request'),
    path('reject_payment_request/<str:request_id>/', views.reject_wholesale_payment_request, name='reject_wholesale_payment_request'),
    path('complete_payment_request/<str:request_id>/', views.complete_wholesale_payment_request, name='complete_payment_request'),


    # Procurement URLs
    path('add_wholesale_procurement/', views.add_wholesale_procurement, name='add_wholesale_procurement'),
    path('wholesales_by_user/', views.wholesales_by_user, name='wholesales_by_user'),
    path('wholesale_procurement_list/', views.wholesale_procurement_list, name='wholesale_procurement_list'),
    path('search_wholesale_procurement/', views.search_wholesale_procurement, name='search_wholesale_procurement'),
    path('wholesale_procurement_detail/<int:procurement_id>/', views.wholesale_procurement_detail, name='wholesale_procurement_detail'),
    path('wholesale_procurement_form/', views.wholesale_procurement_form, name='wholesale_procurement_form'),
    path('search_wholesale_items_for_procurement/', views.search_wholesale_items_for_procurement, name='search_wholesale_items_for_procurement'),


    # Stock Check URLs
    path('create-wholesale-check/', views.create_wholesale_stock_check, name='create_wholesale_stock_check'),
    path('<int:stock_check_id>/update-wholesale/', views.update_wholesale_stock_check, name='update_wholesale_stock_check'),
    path('<int:stock_check_id>/report-wholesale/', views.wholesale_stock_check_report, name='wholesale_stock_check_report'),
    path('stock-check/<int:stock_check_id>/wholesale-approve/', views.approve_wholesale_stock_check, name='approve_wholesale_stock_check'),
    path('stock-check/<int:stock_check_id>/wholesale-bulk-adjust/', views.wholesale_bulk_adjust_stock, name='wholesale_bulk_adjust_stock'),
    path('wholesale_list/', views.list_wholesale_stock_checks, name='list_wholesale_stock_checks'),
    path('delete-wholesale-stock-check/<int:stock_check_id>/', views.delete_wholesale_stock_check, name='delete_wholesale_stock_check'),
    path('adjust-wholesale-stock/<int:stock_item_id>/', views.adjust_wholesale_stock, name='adjust_wholesale_stock'),
    path('search-wholesale-items/', views.search_wholesale_items, name='search_wholesale_items'),
    # Search wholesale items for procurement URL has been removed


    # Request Transfer URLs
    path("transfer_wholesale/", views.create_transfer_request, name="create_transfer_request"),
    path("wholesale/approve/<int:transfer_id>/", views.wholesale_approve_transfer, name="wholesale_approve_transfer"),
    path("wholesale_pending_transfer_requests/", views.pending_wholesale_transfer_requests, name="pending_wholesale_transfer_requests"),
    path("transfer/reject/<int:transfer_id>/", views.reject_wholesale_transfer, name="reject_wholesale_transfer"),
    path("transfer_request_list/", views.wholesale_transfer_request_list, name="wholesale_transfer_request_list"),

    # Add these new URLs for stock adjustment
    path('adjust-wholesale-stock-levels/', views.adjust_wholesale_stock_levels, name='adjust_wholesale_stock_levels'),
    path('search-wholesale-for-adjustment/', views.search_wholesale_for_adjustment, name='search_wholesale_for_adjustment'),
    path('adjust-wholesale-stock-level/<int:item_id>/', views.adjust_wholesale_stock_level, name='adjust_wholesale_stock_level'),

    # Customer return items URL
    path('return_items/<int:pk>/', views.return_wholesale_items_for_customer, name='return_wholesale_items_for_customer'),

    # Wholesale Transfer URL
    path('transfer/multiple/', views.transfer_multiple_wholesale_items, name='transfer_multiple_wholesale_items'),

    # Cashier Payment Totals
    path('cashier_payment_totals/', views.cashier_payment_totals, name='cashier_payment_totals'),

    # Stock Check Enhancement URLs
    path('add_items_to_wholesale_stock_check/<int:stock_check_id>/', views.add_items_to_wholesale_stock_check, name='add_items_to_wholesale_stock_check'),

    # QR Code Generation URLs
    path('qr/item/<int:item_id>/', views.generate_wholesale_item_qr, name='generate_wholesale_item_qr'),
    path('qr/item/<int:item_id>/label/', views.generate_wholesale_item_label, name='generate_wholesale_item_label'),
    path('qr/receipt/<int:receipt_id>/', views.generate_wholesale_receipt_qr, name='generate_wholesale_receipt_qr'),
    path('print-labels/', views.print_wholesale_item_labels, name='print_wholesale_item_labels'),
    path('qr/bulk-labels/', views.bulk_generate_wholesale_labels, name='bulk_generate_wholesale_labels'),
]
