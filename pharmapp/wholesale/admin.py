from django.contrib import admin
from store.models import *

# Register your models here.
class WholesaleItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'dosage_form', 'brand', 'unit', 'cost', 'price', 'stock', 'exp_date', 'markup')
    search_fields = ('name',)
    list_filter = ('markup', 'unit', 'exp_date')



class WholesaleStockCheckItemInline(admin.TabularInline):
    model = StockCheckItem
    extra = 0


class WholesaleStockCheckAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_by', 'date', 'status')
    inlines = [WholesaleStockCheckItemInline]








admin.site.register(WholesaleItem, WholesaleItemAdmin)
admin.site.register(WholesaleStockCheckItem)