from django.contrib import admin
from django.db.models import Sum, Count, Q
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models.functions import TruncDate, TruncMonth
from datetime import datetime, timedelta
from decimal import Decimal
from .models import *

# Register your models here.
class FormulationAdmin(admin.ModelAdmin):
    list_display = ('dosage_form',)
    search_fields = ('dosage_form',)
    list_filter = ('dosage_form',)


class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'dosage_form', 'brand', 'unit', 'cost', 'price', 'markup', 'stock', 'exp_date', )
    search_fields = ('name', 'brand',)
    list_filter = ('name', 'brand',)


class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'cart_id', 'item', 'quantity', 'subtotal', )
    search_fields = ('user', 'cart_id',)
    list_filter = ('user', 'cart_id',)


class WholesaleCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'cart_id', 'item', 'quantity', 'subtotal', )
    search_fields = ('user', 'cart_id',)
    list_filter = ('user', 'cart_id',)


class DispensingLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'dosage_form', 'brand', 'unit', 'quantity', 'amount', 'status', 'created_at', 'sales_performance')
    list_filter = ('user', 'status', 'created_at', 'unit')
    search_fields = ('name', 'brand', 'user__username', 'user__first_name', 'user__last_name')
    date_hierarchy = 'created_at'
    list_per_page = 50
    readonly_fields = ('sales_performance', 'return_info')

    def sales_performance(self, obj):
        """Display sales performance indicator"""
        if obj.status == 'Dispensed':
            return format_html('<span style="color: green;">✓ Sale</span>')
        elif obj.status == 'Returned':
            return format_html('<span style="color: red;">✗ Return</span>')
        else:
            return format_html('<span style="color: orange;">⚠ Partial</span>')
    sales_performance.short_description = 'Performance'

    def return_info(self, obj):
        """Display return information"""
        if obj.has_returns:
            returns = obj.related_returns
            total_returned = sum(r.quantity for r in returns)
            return format_html(
                '<span style="color: red;">Returns: {}</span>',
                total_returned
            )
        return "No returns"
    return_info.short_description = 'Return Info'

    actions = ['mark_as_returned', 'export_sales_data']

    def mark_as_returned(self, request, queryset):
        """Mark selected items as returned"""
        updated = queryset.update(status='Returned')
        self.message_user(request, f'{updated} items marked as returned.')
    mark_as_returned.short_description = "Mark selected items as returned"

    def export_sales_data(self, request, queryset):
        """Export sales data (placeholder for future implementation)"""
        self.message_user(request, f'Export functionality for {queryset.count()} items will be implemented.')
    export_sales_data.short_description = "Export sales data"


# ============ SALES MANAGEMENT ADMIN CLASSES ============

class SalesItemInline(admin.TabularInline):
    model = SalesItem
    extra = 0
    readonly_fields = ('item_total',)

    def item_total(self, obj):
        if obj.pk:
            total = (obj.price * obj.quantity) - obj.discount_amount
            return f"₦{total:,.2f}"
        return "₦0.00"
    item_total.short_description = 'Item Total'

class WholesaleSalesItemInline(admin.TabularInline):
    model = WholesaleSalesItem
    extra = 0
    readonly_fields = ('item_total',)

    def item_total(self, obj):
        if obj.pk:
            total = (obj.price * obj.quantity) - obj.discount_amount
            return f"₦{total:,.2f}"
        return "₦0.00"
    item_total.short_description = 'Item Total'

@admin.register(Sales)
class SalesAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'customer_info', 'total_amount_formatted', 'date', 'sales_type', 'items_count', 'profit_margin')
    list_filter = ('date', 'user', 'customer', 'wholesale_customer')
    search_fields = ('customer__name', 'wholesale_customer__name', 'user__username', 'user__first_name', 'user__last_name')
    date_hierarchy = 'date'
    inlines = [SalesItemInline, WholesaleSalesItemInline]
    readonly_fields = ('total_amount_formatted', 'sales_type', 'items_count', 'profit_analysis', 'payment_status')
    list_per_page = 50

    def customer_info(self, obj):
        if obj.customer:
            return format_html('<strong>{}</strong><br><small>Retail Customer</small>', obj.customer.name)
        elif obj.wholesale_customer:
            return format_html('<strong>{}</strong><br><small>Wholesale Customer</small>', obj.wholesale_customer.name)
        else:
            return format_html('<strong>WALK-IN</strong><br><small>No Account</small>')
    customer_info.short_description = 'Customer'

    def total_amount_formatted(self, obj):
        return f"₦{obj.total_amount:,.2f}"
    total_amount_formatted.short_description = 'Total Amount'
    total_amount_formatted.admin_order_field = 'total_amount'

    def sales_type(self, obj):
        if obj.wholesale_customer:
            return format_html('<span style="color: blue;">Wholesale</span>')
        else:
            return format_html('<span style="color: green;">Retail</span>')
    sales_type.short_description = 'Type'

    def items_count(self, obj):
        retail_count = obj.sales_items.count()
        wholesale_count = obj.wholesale_sales_items.count()
        total = retail_count + wholesale_count
        return f"{total} items"
    items_count.short_description = 'Items'

    def profit_margin(self, obj):
        # Calculate profit margin (placeholder - would need cost data)
        return "Calculate"
    profit_margin.short_description = 'Profit'

    def profit_analysis(self, obj):
        """Detailed profit analysis"""
        retail_items = obj.sales_items.all()
        wholesale_items = obj.wholesale_sales_items.all()

        analysis = []
        total_cost = Decimal('0')
        total_revenue = obj.total_amount

        for item in retail_items:
            item_cost = item.item.cost * item.quantity
            item_revenue = (item.price * item.quantity) - item.discount_amount
            total_cost += item_cost
            analysis.append(f"• {item.item.name}: Cost ₦{item_cost}, Revenue ₦{item_revenue}")

        for item in wholesale_items:
            item_cost = item.item.cost * item.quantity
            item_revenue = (item.price * item.quantity) - item.discount_amount
            total_cost += item_cost
            analysis.append(f"• {item.item.name}: Cost ₦{item_cost}, Revenue ₦{item_revenue}")

        profit = total_revenue - total_cost
        margin = (profit / total_revenue * 100) if total_revenue > 0 else 0

        result = f"<strong>Profit Analysis:</strong><br>"
        result += f"Total Cost: ₦{total_cost:,.2f}<br>"
        result += f"Total Revenue: ₦{total_revenue:,.2f}<br>"
        result += f"Profit: ₦{profit:,.2f}<br>"
        result += f"Margin: {margin:.1f}%<br><br>"
        result += "<br>".join(analysis)

        return format_html(result)
    profit_analysis.short_description = 'Profit Analysis'

    def payment_status(self, obj):
        """Show payment status from receipts"""
        receipts = obj.receipts.all()
        wholesale_receipts = obj.wholesale_receipts.all()

        if receipts.exists():
            receipt = receipts.first()
            return format_html(
                '<span style="color: {};">{}</span>',
                'green' if receipt.status == 'Paid' else 'red',
                receipt.get_status_display()
            )
        elif wholesale_receipts.exists():
            receipt = wholesale_receipts.first()
            return format_html(
                '<span style="color: {};">{}</span>',
                'green' if receipt.status == 'Paid' else 'red',
                receipt.get_status_display()
            )
        return "No Receipt"
    payment_status.short_description = 'Payment Status'

class ReceiptPaymentInline(admin.TabularInline):
    model = ReceiptPayment
    extra = 1

class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('receipt_id', 'customer_info', 'total_amount_formatted', 'date', 'payment_method', 'status', 'sales_link')
    list_filter = ('date', 'payment_method', 'status', 'printed')
    search_fields = ('customer__name', 'receipt_id', 'buyer_name')
    date_hierarchy = 'date'
    inlines = [ReceiptPaymentInline]
    readonly_fields = ('total_amount_formatted', 'sales_link', 'payment_breakdown')
    list_per_page = 50

    def customer_info(self, obj):
        if obj.customer:
            return format_html('<strong>{}</strong>', obj.customer.name)
        elif obj.buyer_name:
            return format_html('<strong>{}</strong><br><small>Walk-in</small>', obj.buyer_name)
        else:
            return "WALK-IN CUSTOMER"
    customer_info.short_description = 'Customer'

    def total_amount_formatted(self, obj):
        return f"₦{obj.total_amount:,.2f}"
    total_amount_formatted.short_description = 'Amount'
    total_amount_formatted.admin_order_field = 'total_amount'

    def sales_link(self, obj):
        if obj.sales:
            url = reverse('admin:store_sales_change', args=[obj.sales.pk])
            return format_html('<a href="{}">View Sales #{}</a>', url, obj.sales.pk)
        return "No Sales Record"
    sales_link.short_description = 'Related Sales'

    def payment_breakdown(self, obj):
        """Show payment breakdown for split payments"""
        if obj.is_split_payment:
            payments = obj.receipt_payments.all()
            breakdown = []
            for payment in payments:
                breakdown.append(f"• {payment.payment_method}: ₦{payment.amount:,.2f}")
            return format_html("<br>".join(breakdown))
        return f"{obj.payment_method}: ₦{obj.total_amount:,.2f}"
    payment_breakdown.short_description = 'Payment Breakdown'

class WholesaleReceiptPaymentInline(admin.TabularInline):
    model = WholesaleReceiptPayment
    extra = 1

class WholesaleReceiptAdmin(admin.ModelAdmin):
    list_display = ('receipt_id', 'customer_info', 'total_amount_formatted', 'date', 'payment_method', 'status', 'sales_link')
    list_filter = ('date', 'payment_method', 'status', 'wallet_went_negative')
    search_fields = ('wholesale_customer__name', 'receipt_id', 'buyer_name')
    date_hierarchy = 'date'
    inlines = [WholesaleReceiptPaymentInline]
    readonly_fields = ('total_amount_formatted', 'sales_link', 'payment_breakdown')
    list_per_page = 50

    def customer_info(self, obj):
        if obj.wholesale_customer:
            return format_html('<strong>{}</strong>', obj.wholesale_customer.name)
        elif obj.buyer_name:
            return format_html('<strong>{}</strong><br><small>Walk-in</small>', obj.buyer_name)
        else:
            return "WALK-IN CUSTOMER"
    customer_info.short_description = 'Customer'

    def total_amount_formatted(self, obj):
        return f"₦{obj.total_amount:,.2f}"
    total_amount_formatted.short_description = 'Amount'
    total_amount_formatted.admin_order_field = 'total_amount'

    def sales_link(self, obj):
        if obj.sales:
            url = reverse('admin:store_sales_change', args=[obj.sales.pk])
            return format_html('<a href="{}">View Sales #{}</a>', url, obj.sales.pk)
        return "No Sales Record"
    sales_link.short_description = 'Related Sales'

    def payment_breakdown(self, obj):
        """Show payment breakdown for split payments"""
        if obj.is_split_payment:
            payments = obj.wholesale_receipt_payments.all()
            breakdown = []
            for payment in payments:
                breakdown.append(f"• {payment.payment_method}: ₦{payment.amount:,.2f}")
            return format_html("<br>".join(breakdown))
        return f"{obj.payment_method}: ₦{obj.total_amount:,.2f}"
    payment_breakdown.short_description = 'Payment Breakdown'


class StockCheckItemInline(admin.TabularInline):
    model = StockCheckItem
    extra = 0

@admin.register(StockCheck)
class StockCheckAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_by', 'date', 'status')
    inlines = [StockCheckItemInline]


# ============ SALES ANALYTICS ADMIN CLASSES ============

@admin.register(SalesItem)
class SalesItemAdmin(admin.ModelAdmin):
    list_display = ('sales_info', 'item', 'quantity', 'price_formatted', 'discount_formatted', 'total_formatted', 'profit_margin')
    list_filter = ('sales__date', 'item__name', 'unit')
    search_fields = ('item__name', 'brand', 'sales__customer__name')
    date_hierarchy = 'sales__date'
    readonly_fields = ('price_formatted', 'discount_formatted', 'total_formatted', 'profit_analysis')
    list_per_page = 100

    def sales_info(self, obj):
        return format_html(
            'Sales #{}<br><small>{}</small>',
            obj.sales.pk,
            obj.sales.date.strftime('%Y-%m-%d')
        )
    sales_info.short_description = 'Sales'

    def price_formatted(self, obj):
        return f"₦{obj.price:,.2f}"
    price_formatted.short_description = 'Unit Price'

    def discount_formatted(self, obj):
        return f"₦{obj.discount_amount:,.2f}"
    discount_formatted.short_description = 'Discount'

    def total_formatted(self, obj):
        total = (obj.price * obj.quantity) - obj.discount_amount
        return f"₦{total:,.2f}"
    total_formatted.short_description = 'Total'

    def profit_margin(self, obj):
        cost = obj.item.cost * obj.quantity
        revenue = (obj.price * obj.quantity) - obj.discount_amount
        profit = revenue - cost
        margin = (profit / revenue * 100) if revenue > 0 else 0
        return f"{margin:.1f}%"
    profit_margin.short_description = 'Margin'

    def profit_analysis(self, obj):
        cost = obj.item.cost * obj.quantity
        revenue = (obj.price * obj.quantity) - obj.discount_amount
        profit = revenue - cost
        margin = (profit / revenue * 100) if revenue > 0 else 0

        return format_html(
            '<strong>Cost:</strong> ₦{:,.2f}<br>'
            '<strong>Revenue:</strong> ₦{:,.2f}<br>'
            '<strong>Profit:</strong> ₦{:,.2f}<br>'
            '<strong>Margin:</strong> {:.1f}%',
            cost, revenue, profit, margin
        )
    profit_analysis.short_description = 'Profit Analysis'

@admin.register(WholesaleSalesItem)
class WholesaleSalesItemAdmin(admin.ModelAdmin):
    list_display = ('sales_info', 'item', 'quantity', 'price_formatted', 'discount_formatted', 'total_formatted', 'profit_margin')
    list_filter = ('sales__date', 'item__name', 'unit')
    search_fields = ('item__name', 'brand', 'sales__wholesale_customer__name')
    date_hierarchy = 'sales__date'
    readonly_fields = ('price_formatted', 'discount_formatted', 'total_formatted', 'profit_analysis')
    list_per_page = 100

    def sales_info(self, obj):
        return format_html(
            'Sales #{}<br><small>{}</small>',
            obj.sales.pk,
            obj.sales.date.strftime('%Y-%m-%d')
        )
    sales_info.short_description = 'Sales'

    def price_formatted(self, obj):
        return f"₦{obj.price:,.2f}"
    price_formatted.short_description = 'Unit Price'

    def discount_formatted(self, obj):
        return f"₦{obj.discount_amount:,.2f}"
    discount_formatted.short_description = 'Discount'

    def total_formatted(self, obj):
        total = (obj.price * obj.quantity) - obj.discount_amount
        return f"₦{total:,.2f}"
    total_formatted.short_description = 'Total'

    def profit_margin(self, obj):
        cost = obj.item.cost * obj.quantity
        revenue = (obj.price * obj.quantity) - obj.discount_amount
        profit = revenue - cost
        margin = (profit / revenue * 100) if revenue > 0 else 0
        return f"{margin:.1f}%"
    profit_margin.short_description = 'Margin'

    def profit_analysis(self, obj):
        cost = obj.item.cost * obj.quantity
        revenue = (obj.price * obj.quantity) - obj.discount_amount
        profit = revenue - cost
        margin = (profit / revenue * 100) if revenue > 0 else 0

        return format_html(
            '<strong>Cost:</strong> ₦{:,.2f}<br>'
            '<strong>Revenue:</strong> ₦{:,.2f}<br>'
            '<strong>Profit:</strong> ₦{:,.2f}<br>'
            '<strong>Margin:</strong> {:.1f}%',
            cost, revenue, profit, margin
        )
    profit_analysis.short_description = 'Profit Analysis'

class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('category', 'amount_formatted', 'date', 'expense_ratio')
    list_filter = ('category', 'date')
    search_fields = ('category__name',)
    date_hierarchy = 'date'
    readonly_fields = ('amount_formatted', 'expense_ratio')

    def amount_formatted(self, obj):
        return f"₦{obj.amount:,.2f}"
    amount_formatted.short_description = 'Amount'
    amount_formatted.admin_order_field = 'amount'

    def expense_ratio(self, obj):
        # Calculate expense as percentage of daily sales (placeholder)
        return "Calculate vs Sales"
    expense_ratio.short_description = 'vs Sales'








# ============ SALES DASHBOARD ADMIN ============

class SalesDashboardAdmin(admin.ModelAdmin):
    """Custom admin for sales dashboard and analytics"""

    def changelist_view(self, request, extra_context=None):
        # Calculate sales statistics
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        this_month = today.replace(day=1)
        last_month = (this_month - timedelta(days=1)).replace(day=1)

        # Daily sales
        today_sales = DispensingLog.objects.filter(
            created_at__date=today,
            status='Dispensed'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        yesterday_sales = DispensingLog.objects.filter(
            created_at__date=yesterday,
            status='Dispensed'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Monthly sales
        this_month_sales = DispensingLog.objects.filter(
            created_at__date__gte=this_month,
            status='Dispensed'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        last_month_sales = DispensingLog.objects.filter(
            created_at__date__gte=last_month,
            created_at__date__lt=this_month,
            status='Dispensed'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Top selling items
        top_items = DispensingLog.objects.filter(
            created_at__date__gte=this_month,
            status='Dispensed'
        ).values('name').annotate(
            total_quantity=Sum('quantity'),
            total_amount=Sum('amount')
        ).order_by('-total_amount')[:10]

        # Sales by user
        sales_by_user = DispensingLog.objects.filter(
            created_at__date__gte=this_month,
            status='Dispensed'
        ).values('user__username', 'user__first_name', 'user__last_name').annotate(
            total_sales=Sum('amount'),
            total_items=Count('id')
        ).order_by('-total_sales')[:10]

        extra_context = extra_context or {}
        extra_context.update({
            'today_sales': today_sales,
            'yesterday_sales': yesterday_sales,
            'this_month_sales': this_month_sales,
            'last_month_sales': last_month_sales,
            'top_items': top_items,
            'sales_by_user': sales_by_user,
            'daily_change': ((today_sales - yesterday_sales) / yesterday_sales * 100) if yesterday_sales > 0 else 0,
            'monthly_change': ((this_month_sales - last_month_sales) / last_month_sales * 100) if last_month_sales > 0 else 0,
        })

        return super().changelist_view(request, extra_context=extra_context)

# Register all models with enhanced admin interfaces
admin.site.register(Formulation, FormulationAdmin)
admin.site.register(Item, ItemAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(WholesaleCart, WholesaleCartAdmin)
admin.site.register(DispensingLog, DispensingLogAdmin)
admin.site.register(Receipt, ReceiptAdmin)
admin.site.register(WholesaleReceipt, WholesaleReceiptAdmin)
admin.site.register(ReceiptPayment)
admin.site.register(WholesaleReceiptPayment)
admin.site.register(StockCheckItem)
admin.site.register(ExpenseCategory, ExpenseCategoryAdmin)
admin.site.register(Expense, ExpenseAdmin)

# Additional models that weren't registered before
admin.site.register(Customer)
admin.site.register(WholesaleCustomer)
# Note: WholesaleItem is registered in wholesale/admin.py with enhanced features

# Customize admin site headers
admin.site.site_header = "PharmApp Sales Management"
admin.site.site_title = "PharmApp Admin"
admin.site.index_title = "Sales & Inventory Management Dashboard"