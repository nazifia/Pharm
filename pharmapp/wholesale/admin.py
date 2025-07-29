from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from decimal import Decimal
from store.models import *

# ============ WHOLESALE MANAGEMENT ADMIN CLASSES ============

class WholesaleItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'dosage_form', 'brand', 'unit', 'cost_formatted', 'price_formatted', 'markup_display', 'stock_status', 'exp_date', 'profit_margin')
    search_fields = ('name', 'brand', 'dosage_form')
    list_filter = ('markup', 'unit', 'exp_date', 'dosage_form')
    readonly_fields = ('cost_formatted', 'price_formatted', 'markup_display', 'profit_margin', 'stock_status', 'sales_performance')
    list_per_page = 50
    date_hierarchy = 'exp_date'

    def cost_formatted(self, obj):
        return f"₦{obj.cost:,.2f}"
    cost_formatted.short_description = 'Cost'
    cost_formatted.admin_order_field = 'cost'

    def price_formatted(self, obj):
        return f"₦{obj.price:,.2f}"
    price_formatted.short_description = 'Price'
    price_formatted.admin_order_field = 'price'

    def markup_display(self, obj):
        return f"{obj.markup}%"
    markup_display.short_description = 'Markup'
    markup_display.admin_order_field = 'markup'

    def stock_status(self, obj):
        if obj.stock <= obj.low_stock_threshold:
            return format_html('<span style="color: red;">⚠ Low Stock ({} {})</span>', obj.stock, obj.unit)
        elif obj.stock <= (obj.low_stock_threshold * 2):
            return format_html('<span style="color: orange;">⚡ Medium ({} {})</span>', obj.stock, obj.unit)
        else:
            return format_html('<span style="color: green;">✓ Good ({} {})</span>', obj.stock, obj.unit)
    stock_status.short_description = 'Stock Status'

    def profit_margin(self, obj):
        if obj.cost > 0:
            margin = ((obj.price - obj.cost) / obj.cost * 100)
            color = 'green' if margin > 20 else 'orange' if margin > 10 else 'red'
            return format_html('<span style="color: {};">{:.1f}%</span>', color, margin)
        return "N/A"
    profit_margin.short_description = 'Profit Margin'

    def sales_performance(self, obj):
        """Show sales performance for this wholesale item"""
        # Get sales data for this item (placeholder - would need actual sales tracking)
        return "Track Sales"
    sales_performance.short_description = 'Sales Performance'

class WholesaleStockCheckItemInline(admin.TabularInline):
    model = WholesaleStockCheckItem
    extra = 0
    readonly_fields = ('discrepancy_display',)

    def discrepancy_display(self, obj):
        if obj.pk:
            discrepancy = obj.discrepancy()
            if discrepancy > 0:
                return format_html('<span style="color: green;">+{}</span>', discrepancy)
            elif discrepancy < 0:
                return format_html('<span style="color: red;">{}</span>', discrepancy)
            else:
                return format_html('<span style="color: blue;">0</span>')
        return "N/A"
    discrepancy_display.short_description = 'Discrepancy'

@admin.register(WholesaleStockCheck)
class WholesaleStockCheckAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_by', 'date', 'status', 'items_count', 'total_discrepancy')
    list_filter = ('status', 'date', 'created_by')
    search_fields = ('created_by__username', 'created_by__first_name', 'created_by__last_name')
    date_hierarchy = 'date'
    inlines = [WholesaleStockCheckItemInline]
    readonly_fields = ('items_count', 'total_discrepancy', 'discrepancy_summary')

    def items_count(self, obj):
        return obj.wholesale_items.count()
    items_count.short_description = 'Items Count'

    def total_discrepancy(self, obj):
        total = sum(item.discrepancy() for item in obj.wholesale_items.all())
        color = 'red' if total < 0 else 'green' if total > 0 else 'blue'
        return format_html('<span style="color: {};">{:+d}</span>', color, total)
    total_discrepancy.short_description = 'Total Discrepancy'

    def discrepancy_summary(self, obj):
        """Detailed discrepancy breakdown"""
        items = obj.wholesale_items.all()
        positive = sum(1 for item in items if item.discrepancy() > 0)
        negative = sum(1 for item in items if item.discrepancy() < 0)
        zero = sum(1 for item in items if item.discrepancy() == 0)

        return format_html(
            '<strong>Summary:</strong><br>'
            '✓ Exact: {} items<br>'
            '↗ Surplus: {} items<br>'
            '↘ Shortage: {} items',
            zero, positive, negative
        )
    discrepancy_summary.short_description = 'Discrepancy Summary'








# Register wholesale models with enhanced admin interfaces
admin.site.register(WholesaleItem, WholesaleItemAdmin)
admin.site.register(WholesaleStockCheckItem)

# Customize wholesale admin section
admin.site.site_header = "PharmApp Wholesale & Sales Management"