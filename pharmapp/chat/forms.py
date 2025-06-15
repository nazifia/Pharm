from django import forms
from django.contrib.auth import get_user_model
from .models import ChatMessage, ChatRoom

User = get_user_model()

class ChatMessageForm(forms.ModelForm):
    class Meta:
        model = ChatMessage
        fields = ['receiver', 'message', 'file_attachment']
        widgets = {
            'message': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Type your message...',
                'class': 'form-control',
                'id': 'message-input'
            }),
            'receiver': forms.Select(attrs={'class': 'form-control'}),
            'file_attachment': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,application/pdf,.doc,.docx,.txt'
            })
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            # Exclude current user from receiver choices
            self.fields['receiver'].queryset = User.objects.exclude(id=user.id)
            self.fields['receiver'].empty_label = "Select a user to chat with"

    def clean(self):
        cleaned_data = super().clean()
        message = cleaned_data.get('message')
        receiver = cleaned_data.get('receiver')
        file_attachment = cleaned_data.get('file_attachment')

        # Either message or file attachment is required
        if not message and not file_attachment:
            raise forms.ValidationError("Either message text or file attachment is required.")

        return cleaned_data

class QuickMessageForm(forms.Form):
    """Simple form for quick message sending via AJAX"""
    message = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Type your message...',
            'class': 'form-control',
            'autocomplete': 'off'
        }),
        max_length=1000,
        required=True
    )

class GroupChatForm(forms.ModelForm):
    """Form for creating group chats"""
    participants = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    class Meta:
        model = ChatRoom
        fields = ['name', 'participants']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter group name...'
            })
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            # Exclude current user from participants (they'll be added automatically)
            self.fields['participants'].queryset = User.objects.exclude(id=user.id)

class FileUploadForm(forms.Form):
    """Form for file uploads in chat"""
    file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*,application/pdf,.doc,.docx,.txt,.zip,.rar'
        }),
        required=True
    )
    message = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Add a caption (optional)...',
            'class': 'form-control'
        }),
        required=False,
        max_length=500
    )