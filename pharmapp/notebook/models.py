from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

User = get_user_model()


class NoteCategory(models.Model):
    """Categories for organizing notes"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    color = models.CharField(max_length=7, default='#007bff', help_text='Hex color code for category')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Note Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Note(models.Model):
    """Model for storing user notes"""
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    category = models.ForeignKey(NoteCategory, on_delete=models.SET_NULL, null=True, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    is_pinned = models.BooleanField(default=False, help_text='Pin important notes to top')
    is_archived = models.BooleanField(default=False, help_text='Archive completed notes')
    tags = models.CharField(max_length=500, blank=True, help_text='Comma-separated tags for easy searching')
    reminder_date = models.DateTimeField(null=True, blank=True, help_text='Optional reminder date')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_pinned', '-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at']),
            models.Index(fields=['user', 'category']),
            models.Index(fields=['user', 'is_pinned']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def get_absolute_url(self):
        return reverse('notebook:note_detail', kwargs={'pk': self.pk})
    
    def get_tags_list(self):
        """Return tags as a list"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []
    
    def is_overdue(self):
        """Check if reminder date has passed"""
        if self.reminder_date:
            return timezone.now() > self.reminder_date
        return False
    
    def get_priority_badge_class(self):
        """Return Bootstrap badge class based on priority"""
        priority_classes = {
            'low': 'badge-secondary',
            'medium': 'badge-info',
            'high': 'badge-warning',
            'urgent': 'badge-danger',
        }
        return priority_classes.get(self.priority, 'badge-secondary')

    def is_new(self, hours=24):
        """Check if note was created within the specified hours (default 24 hours)"""
        from datetime import timedelta
        cutoff_time = timezone.now() - timedelta(hours=hours)
        return self.created_at >= cutoff_time

    def is_recently_updated(self, hours=6):
        """Check if note was updated within the specified hours (default 6 hours)"""
        from datetime import timedelta
        cutoff_time = timezone.now() - timedelta(hours=hours)
        return self.updated_at >= cutoff_time and self.updated_at != self.created_at


class NoteShare(models.Model):
    """Model for sharing notes between users"""
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='shares')
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_notes')
    shared_with = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_notes')
    can_edit = models.BooleanField(default=False, help_text='Allow the recipient to edit the note')
    shared_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['note', 'shared_with']
        ordering = ['-shared_at']
    
    def __str__(self):
        return f"{self.note.title} shared with {self.shared_with.username}"
