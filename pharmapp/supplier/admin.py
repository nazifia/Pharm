from django.contrib import admin
from . models import *

# Register your models here.
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'contact_info')
    search_fields = ('name', 'phone')

class ProcurementItemAdmin(admin.ModelAdmin):
    list_display = ('item_name', 'unit', 'quantity')
    search_fields = ('item_name', 'supplier__name')
    list_filter = ('item_name', 'unit', 'quantity', 'cost_price', 'subtotal')


class ProcurementAdmin(admin.ModelAdmin):
    list_display = ('supplier', 'date', 'total')
    search_fields = ('supplier__name', 'date')
    list_filter = ('supplier__name', 'date')
















admin.site.register(Supplier, SupplierAdmin)
admin.site.register(ProcurementItem, ProcurementItemAdmin)
admin.site.register(Procurement, ProcurementAdmin)
