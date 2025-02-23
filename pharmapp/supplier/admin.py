from django.contrib import admin
from . models import *

# Register your models here.
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'contact_info')
    search_fields = ('name', 'phone')

class ProcurementItemAdmin(admin.ModelAdmin):
    list_display = ('item_name', 'unit', 'quantity', 'expiry_date',)
    search_fields = ('item_name', 'supplier__name')
    list_filter = ('item_name', 'unit', 'quantity', 'cost_price', 'subtotal')


class WholesaleProcurementItemAdmin(admin.ModelAdmin):
    list_display = ('item_name', 'unit', 'quantity', 'expiry_date')
    search_fields = ('item_name', 'supplier__name')
    list_filter = ('item_name', 'unit', 'quantity', 'cost_price', 'subtotal')

class ProcurementAdmin(admin.ModelAdmin):
    list_display = ('supplier', 'date', 'total')
    search_fields = ('supplier__name', 'date')
    list_filter = ('supplier__name', 'date')

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # Recalculate and update the total after saving inlines
        procurement = form.instance
        procurement.calculate_total()


class WholesaleProcurementAdmin(admin.ModelAdmin):
    list_display = ('supplier', 'date', 'total')
    search_fields = ('supplier__name', 'date')
    list_filter = ('supplier__name', 'date')

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # Recalculate and update the total after saving inlines
        procurement = form.instance
        procurement.calculate_total()



class StoreItemAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name', )
    list_filter = ('name',)















admin.site.register(Supplier, SupplierAdmin)
admin.site.register(ProcurementItem, ProcurementItemAdmin)
admin.site.register(WholesaleProcurementItem, WholesaleProcurementItemAdmin)
admin.site.register(Procurement, ProcurementAdmin)
admin.site.register(WholesaleProcurement, WholesaleProcurementAdmin)
admin.site.register(StoreItem, StoreItemAdmin)
