from django.contrib import admin
from .models import Note, NoteCategory, NoteShare


@admin.register(NoteCategory)
class NoteCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'color', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    ordering = ['name']


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'category', 'priority', 'is_pinned', 'is_archived', 'created_at', 'updated_at']
    list_filter = ['priority', 'is_pinned', 'is_archived', 'category', 'created_at', 'updated_at']
    search_fields = ['title', 'content', 'tags', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'content', 'user', 'category')
        }),
        ('Organization', {
            'fields': ('priority', 'tags', 'is_pinned', 'is_archived')
        }),
        ('Reminder', {
            'fields': ('reminder_date',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(NoteShare)
class NoteShareAdmin(admin.ModelAdmin):
    list_display = ['note', 'shared_by', 'shared_with', 'can_edit', 'shared_at']
    list_filter = ['can_edit', 'shared_at']
    search_fields = ['note__title', 'shared_by__username', 'shared_with__username']
    ordering = ['-shared_at']
