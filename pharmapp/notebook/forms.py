from django import forms
from django.contrib.auth import get_user_model
from .models import Note, NoteCategory, NoteShare

User = get_user_model()


class NoteForm(forms.ModelForm):
    """Form for creating and editing notes"""
    
    class Meta:
        model = Note
        fields = ['title', 'content', 'category', 'priority', 'tags', 'is_pinned', 'reminder_date']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter note title...',
                'maxlength': 200
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Write your note here...'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-control'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter tags separated by commas (e.g., work, important, meeting)',
                'maxlength': 500
            }),
            'is_pinned': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'reminder_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].empty_label = "Select a category (optional)"
        self.fields['reminder_date'].required = False


class NoteCategoryForm(forms.ModelForm):
    """Form for creating and editing note categories"""
    
    class Meta:
        model = NoteCategory
        fields = ['name', 'description', 'color']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Category name...',
                'maxlength': 100
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Category description (optional)...'
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
                'value': '#007bff'
            }),
        }


class NoteSearchForm(forms.Form):
    """Form for searching notes"""
    query = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search notes by title, content, or tags...',
            'autocomplete': 'off'
        })
    )
    category = forms.ModelChoiceField(
        queryset=NoteCategory.objects.all(),
        required=False,
        empty_label="All categories",
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    priority = forms.ChoiceField(
        choices=[('', 'All priorities')] + Note.PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    is_pinned = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    is_archived = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )


class NoteShareForm(forms.ModelForm):
    """Form for sharing notes with other users"""
    
    class Meta:
        model = NoteShare
        fields = ['shared_with', 'can_edit']
        widgets = {
            'shared_with': forms.Select(attrs={
                'class': 'form-control'
            }),
            'can_edit': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)
        if current_user:
            # Exclude current user from the list of users to share with
            self.fields['shared_with'].queryset = User.objects.exclude(id=current_user.id)
