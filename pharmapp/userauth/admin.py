from django.contrib import admin
from django.utils import timezone
from datetime import timedelta
from django import forms
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import *

class TimePeriodFilter(admin.SimpleListFilter):
    title = 'time period'
    parameter_name = 'time_period'

    def lookups(self, request, model_admin):
        return (
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('this_week', 'This Week'),
            ('last_week', 'Last Week'),
            ('this_month', 'This Month'),
            ('last_month', 'Last Month'),
        )

    def queryset(self, request, queryset):
        today = timezone.now().date()

        if self.value() == 'today':
            return queryset.filter(timestamp__date=today)

        if self.value() == 'yesterday':
            yesterday = today - timedelta(days=1)
            return queryset.filter(timestamp__date=yesterday)

        if self.value() == 'this_week':
            start_of_week = today - timedelta(days=today.weekday())
            return queryset.filter(timestamp__date__gte=start_of_week)

        if self.value() == 'last_week':
            start_of_this_week = today - timedelta(days=today.weekday())
            start_of_last_week = start_of_this_week - timedelta(days=7)
            end_of_last_week = start_of_this_week - timedelta(days=1)
            return queryset.filter(timestamp__date__gte=start_of_last_week, timestamp__date__lte=end_of_last_week)

        if self.value() == 'this_month':
            return queryset.filter(timestamp__month=today.month, timestamp__year=today.year)

        if self.value() == 'last_month':
            last_month = today.replace(day=1) - timedelta(days=1)
            return queryset.filter(timestamp__month=last_month.month, timestamp__year=last_month.year)

# Register your models here.
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'mobile', 'is_staff', 'is_superuser')
    search_fields = ('username', 'mobile')
    list_filter = ('is_staff', 'is_superuser')

class ProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name',)
    search_fields = ('full_name',)

class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type', 'action', 'timestamp', 'formatted_timestamp')
    list_filter = (TimePeriodFilter, 'user__profile__user_type', 'timestamp')
    search_fields = ('user__username', 'user__mobile', 'action')
    date_hierarchy = 'timestamp'
    list_per_page = 50
    readonly_fields = ('user', 'action', 'timestamp')
    change_list_template = 'admin/userauth/activitylog/change_list.html'
    actions = ['export_as_csv']
    ordering = ('-timestamp',)

    def user_type(self, obj):
        try:
            return obj.user.profile.user_type
        except:
            return 'N/A'
    user_type.short_description = 'User Type'

    def formatted_timestamp(self, obj):
        return obj.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    formatted_timestamp.short_description = 'Time (Y-m-d H:M:S)'

    def export_as_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        from django.utils.encoding import smart_str

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=activity_log.csv'
        writer = csv.writer(response, csv.excel)

        # Write header row
        writer.writerow([
            smart_str('User'),
            smart_str('User Type'),
            smart_str('Action'),
            smart_str('Timestamp'),
        ])

        # Write data rows
        for obj in queryset:
            try:
                user_type = obj.user.profile.user_type
            except:
                user_type = 'N/A'

            writer.writerow([
                smart_str(obj.user.username),
                smart_str(user_type),
                smart_str(obj.action),
                smart_str(obj.timestamp.strftime('%Y-%m-%d %H:%M:%S')),
            ])

        return response
    export_as_csv.short_description = "Export selected activities as CSV"

    def changelist_view(self, request, extra_context=None):
        # Get statistics for the dashboard
        from django.utils import timezone
        import datetime

        # Get today's activities count
        today = timezone.now().date()
        today_start = datetime.datetime.combine(today, datetime.time.min, tzinfo=timezone.get_current_timezone())
        today_end = datetime.datetime.combine(today, datetime.time.max, tzinfo=timezone.get_current_timezone())
        today_count = ActivityLog.objects.filter(timestamp__range=(today_start, today_end)).count()

        # Get active users count (users with activity in the last 7 days)
        last_week = today - datetime.timedelta(days=7)
        active_users = User.objects.filter(activitylog__timestamp__gte=last_week).distinct().count()

        # Add to context
        extra_context = extra_context or {}
        extra_context.update({
            'today_count': today_count,
            'active_users': active_users,
        })

        return super().changelist_view(request, extra_context=extra_context)


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'mobile', 'is_staff', 'is_superuser')

    def save(self, commit=True):
        user = super().save(commit=False)
        # If user_type is Admin, automatically set is_staff and is_superuser
        if commit:
            user.save()
            if hasattr(user, 'profile') and user.profile.user_type == 'Admin':
                user.is_staff = True
                user.is_superuser = True
                user.save()
        return user


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    list_display = ('username', 'mobile', 'is_staff', 'is_superuser', 'get_user_type')
    list_filter = ('is_staff', 'is_superuser', 'profile__user_type')
    fieldsets = (
        (None, {'fields': ('username', 'mobile', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'mobile', 'password1', 'password2', 'is_staff', 'is_superuser'),
        }),
    )
    search_fields = ('username', 'mobile')
    ordering = ('username',)

    def get_user_type(self, obj):
        try:
            return obj.profile.user_type
        except:
            return 'N/A'
    get_user_type.short_description = 'User Type'


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'user_type')
    list_filter = ('user_type',)
    search_fields = ('user__username', 'user__mobile', 'full_name')
    raw_id_fields = ('user',)


admin.site.register(User, CustomUserAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(ActivityLog, ActivityLogAdmin)