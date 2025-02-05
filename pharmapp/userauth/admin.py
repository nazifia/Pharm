from django.contrib import admin
from .models import *

# Register your models here.
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'mobile', 'is_staff', 'is_superuser')
    search_fields = ('username', 'mobile')
    list_filter = ('is_staff', 'is_superuser')

class ProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name',)
    search_fields = ('full_name',)

class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('user__username', 'action')


admin.site.register(User, UserAdmin)
admin.site.register(ActivityLog, ActivityLogAdmin)

admin.site.register(Profile, ProfileAdmin)