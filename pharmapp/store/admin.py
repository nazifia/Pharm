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


class ReceiptPaymentInline(admin.TabularInline):
    model = ReceiptPayment
    extra = 1

class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('sales', 'total_amount', 'date', 'receipt_id', 'payment_method', 'status')
    list_filter = ('date', 'payment_method', 'status')
    search_fields = ('customer__name', 'receipt_id')
    inlines = [ReceiptPaymentInline]


class WholesaleReceiptPaymentInline(admin.TabularInline):
    model = WholesaleReceiptPayment
    extra = 1

class WholesaleReceiptAdmin(admin.ModelAdmin):
    list_display = ('sales', 'total_amount', 'date', 'receipt_id', 'payment_method', 'status')
    list_filter = ('date', 'payment_method', 'status')
    search_fields = ('wholesale_customer__name', 'receipt_id')
    inlines = [WholesaleReceiptPaymentInline]


class StockCheckItemInline(admin.TabularInline):
    model = StockCheckItem
    extra = 0

@admin.register(StockCheck)
class StockCheckAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_by', 'date', 'status')
    inlines = [StockCheckItemInline]


class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('category', 'amount', 'date',)








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