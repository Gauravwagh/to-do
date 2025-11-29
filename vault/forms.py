"""
Forms for vault operations.
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import (
    VaultCredential, VaultSecureNote, VaultFile, VaultAPIKey, VaultConfig
)


class VaultSetupForm(forms.Form):
    """Form for initial vault setup."""

    master_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter master password',
            'required': True,
            'autocomplete': 'new-password',
        }),
        min_length=12,
        help_text='Minimum 12 characters. Use a strong, unique password.'
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm master password',
            'required': True,
            'autocomplete': 'new-password',
        }),
        label='Confirm Password'
    )

    vault_timeout_minutes = forms.IntegerField(
        initial=15,
        min_value=5,
        max_value=120,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
        }),
        help_text='Minutes before vault auto-locks (5-120)'
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('master_password')
        confirm = cleaned_data.get('confirm_password')

        if password and confirm:
            if password != confirm:
                raise ValidationError('Passwords do not match.')

        return cleaned_data


class VaultUnlockForm(forms.Form):
    """Form for unlocking the vault."""

    master_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter master password',
            'required': True,
            'autocomplete': 'current-password',
            'autofocus': True,
        }),
        label='Master Password'
    )


class VaultCredentialForm(forms.ModelForm):
    """Form for creating/editing vault credentials."""

    class Meta:
        model = VaultCredential
        fields = [
            'name', 'credential_type', 'website_url', 'username',
            'email', 'password', 'totp_secret', 'notes', 'category', 'is_favorite'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Gmail Account',
            }),
            'credential_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'website_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com',
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com',
            }),
            'password': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Password',
            }),
            'totp_secret': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '2FA Secret (optional)',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Additional notes...',
            }),
            'category': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Category (optional)',
            }),
            'is_favorite': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    # Plaintext password field for display during editing
    plaintext_password = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
        }),
        label='Password (visible)'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make password not required in form (we'll handle it manually)
        self.fields['password'].required = False


class VaultSecureNoteForm(forms.ModelForm):
    """Form for creating/editing secure notes."""

    class Meta:
        model = VaultSecureNote
        fields = ['name', 'content_type', 'content', 'notes', 'category', 'is_favorite']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Note title',
            }),
            'content_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Your secure note content...',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes (optional)...',
            }),
            'category': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Category (optional)',
            }),
            'is_favorite': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }


class VaultFileForm(forms.ModelForm):
    """Form for uploading encrypted files."""

    class Meta:
        model = VaultFile
        fields = ['name', 'encrypted_file', 'notes', 'category', 'is_favorite']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'File name/description',
            }),
            'encrypted_file': forms.FileInput(attrs={
                'class': 'form-control',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes (optional)...',
            }),
            'category': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Category (optional)',
            }),
            'is_favorite': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def clean_encrypted_file(self):
        from django.conf import settings
        file = self.cleaned_data.get('encrypted_file')

        if file:
            max_size = settings.VAULT_SETTINGS.get('MAX_FILE_SIZE_MB', 25) * 1024 * 1024
            if file.size > max_size:
                raise ValidationError(
                    f'File size cannot exceed {settings.VAULT_SETTINGS.get("MAX_FILE_SIZE_MB", 25)}MB.'
                )

        return file


class VaultAPIKeyForm(forms.ModelForm):
    """Form for storing API keys and tokens."""

    class Meta:
        model = VaultAPIKey
        fields = [
            'name', 'api_key_type', 'service_name', 'api_key', 'api_secret',
            'expires_at', 'expiration_warning_days', 'notes', 'category', 'is_favorite'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., AWS API Key',
            }),
            'api_key_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'service_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Service name',
            }),
            'api_key': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'API Key',
            }),
            'api_secret': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'API Secret (optional)',
            }),
            'expires_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }),
            'expiration_warning_days': forms.NumberInput(attrs={
                'class': 'form-control',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes (optional)...',
            }),
            'category': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Category (optional)',
            }),
            'is_favorite': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }


class VaultConfigForm(forms.ModelForm):
    """Form for updating vault configuration."""

    class Meta:
        model = VaultConfig
        fields = ['vault_timeout_minutes', 'max_failed_attempts']
        widgets = {
            'vault_timeout_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 5,
                'max': 120,
            }),
            'max_failed_attempts': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 3,
                'max': 10,
            }),
        }


class VaultReAuthForm(forms.Form):
    """Form for re-authenticating with master password."""

    master_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter master password to view',
            'required': True,
            'autocomplete': 'current-password',
            'autofocus': True,
        }),
        label='Master Password'
    )


class VaultSearchForm(forms.Form):
    """Form for searching vault items."""

    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search vault items...',
            'autocomplete': 'off',
        }),
        label='Search'
    )

    item_type = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Types'),
            ('credential', 'Credentials'),
            ('note', 'Secure Notes'),
            ('file', 'Files'),
            ('apikey', 'API Keys'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
        label='Type'
    )

    category = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Category...',
        }),
        label='Category'
    )

    favorites_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
        label='Favorites Only'
    )
