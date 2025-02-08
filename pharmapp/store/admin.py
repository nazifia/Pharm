from django.contrib import admin
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
    list_display = ('user', 'name', 'dosage_form', 'brand', 'unit', 'quantity', 'amount', 'status', 'created_at',)
    list_filter = ('user', 'created_at',)
    search_fields = ('name',)


class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('sales', 'total_amount', 'date', 'receipt_id',)
    list_filter = ('date',)
    search_fields = ('customer__name', 'receipt_id',)


class WholesaleReceiptAdmin(admin.ModelAdmin):
    list_display = ( 'sales', 'total_amount', 'date', 'receipt_id',)
    list_filter = ('date',)
    search_fields = ( 'wholesale_customer__name', 'receipt_id',)


class StockCheckItemInline(admin.TabularInline):
    model = StockCheckItem
    extra = 0

@admin.register(StockCheck)
class StockCheckAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_by', 'date', 'status')
    inlines = [StockCheckItemInline]













admin.site.register(Formulation, FormulationAdmin)
admin.site.register(Item, ItemAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(WholesaleCart, WholesaleCartAdmin)
admin.site.register(DispensingLog, DispensingLogAdmin)
admin.site.register(Receipt, ReceiptAdmin)
admin.site.register(WholesaleReceipt, WholesaleReceiptAdmin)
admin.site.register(StockCheckItem)