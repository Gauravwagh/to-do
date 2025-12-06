"""
Views for vault operations.
"""
import hashlib
import mimetypes
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, DetailView, FormView, TemplateView
)
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse, Http404
from django.utils import timezone
from django.db.models import Q
from cryptography.fernet import InvalidToken

from .models import (
    VaultConfig, VaultCredential, VaultSecureNote, VaultFile, VaultAPIKey,
    VaultSession, VaultAuditLog
)
from .forms import (
    VaultSetupForm, VaultUnlockForm, VaultCredentialForm, VaultSecureNoteForm,
    VaultFileForm, VaultAPIKeyForm, VaultConfigForm, VaultSearchForm, VaultReAuthForm
)
from .crypto import VaultCryptoService
from .session import VaultSessionManager


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip if ip else None


def log_vault_action(request, action, success=True, item_type=None, item_id=None, details=None):
    """Log vault action to audit log."""
    VaultAuditLog.objects.create(
        user=request.user,
        action=action,
        item_type=item_type or '',
        item_id=item_id,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
        success=success,
        details=details or {}
    )


class VaultRequiredMixin(LoginRequiredMixin):
    """Mixin that ensures vault is unlocked."""

    def dispatch(self, request, *args, **kwargs):
        # First check if user is logged in
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # Check if vault is set up
        try:
            vault_config = request.user.vault_config
            if not vault_config.is_initialized:
                messages.info(request, 'Please set up your vault first.')
                return redirect('vault:setup')
        except VaultConfig.DoesNotExist:
            messages.info(request, 'Please set up your vault first.')
            return redirect('vault:setup')

        # Check if vault is unlocked
        if not VaultSessionManager.is_vault_unlocked(request):
            messages.warning(request, 'Please unlock your vault to continue.')
            return redirect('vault:unlock')

        # Check for timeout
        if VaultSessionManager.check_timeout(request, vault_config.vault_timeout_minutes):
            VaultSessionManager.lock_vault(request)
            log_vault_action(request, 'timeout', success=True)
            messages.warning(request, 'Your vault session has timed out.')
            return redirect('vault:unlock')

        # Update activity
        VaultSessionManager.update_activity(request)

        return super().dispatch(request, *args, **kwargs)


class VaultSetupView(LoginRequiredMixin, FormView):
    """Initial vault setup view."""
    template_name = 'vault/setup.html'
    form_class = VaultSetupForm
    success_url = reverse_lazy('vault:dashboard')

    def dispatch(self, request, *args, **kwargs):
        # Check if vault is already set up
        try:
            if request.user.vault_config.is_initialized:
                messages.info(request, 'Your vault is already set up.')
                return redirect('vault:dashboard')
        except VaultConfig.DoesNotExist:
            pass

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        master_password = form.cleaned_data['master_password']
        timeout_minutes = form.cleaned_data['vault_timeout_minutes']

        # Generate salt for master password
        salt = VaultCryptoService.generate_salt()

        # Derive key from master password
        master_key = VaultCryptoService.derive_key_from_master_password(master_password, salt)

        # Generate DEK
        dek = VaultCryptoService.generate_dek()

        # Encrypt DEK with master key
        encrypted_dek = VaultCryptoService.encrypt_dek(dek, master_key)

        # Hash master password for verification
        password_hash = VaultCryptoService.hash_master_password(master_password, salt)

        # Create or update vault config
        vault_config, created = VaultConfig.objects.get_or_create(
            user=self.request.user,
            defaults={
                'encrypted_dek': encrypted_dek,
                'master_password_salt': salt,
                'master_password_hash': password_hash,
                'vault_timeout_minutes': timeout_minutes,
                'is_initialized': True,
                'initialized_at': timezone.now(),
            }
        )

        if not created:
            # Update existing config
            vault_config.encrypted_dek = encrypted_dek
            vault_config.master_password_salt = salt
            vault_config.master_password_hash = password_hash
            vault_config.vault_timeout_minutes = timeout_minutes
            vault_config.is_initialized = True
            vault_config.initialized_at = timezone.now()
            vault_config.save()

        # Automatically unlock vault after setup
        VaultSessionManager.store_dek_in_session(self.request, dek, timeout_minutes)

        # Log the setup
        log_vault_action(self.request, 'unlock', success=True, details={'setup': True})

        messages.success(self.request, 'Vault set up successfully!')
        return super().form_valid(form)


class VaultUnlockView(LoginRequiredMixin, FormView):
    """Vault unlock view."""
    template_name = 'vault/unlock.html'
    form_class = VaultUnlockForm

    def get_success_url(self):
        return self.request.GET.get('next', reverse('vault:dashboard'))

    def dispatch(self, request, *args, **kwargs):
        # Check if vault is set up
        try:
            vault_config = request.user.vault_config
            if not vault_config.is_initialized:
                messages.info(request, 'Please set up your vault first.')
                return redirect('vault:setup')
        except VaultConfig.DoesNotExist:
            messages.info(request, 'Please set up your vault first.')
            return redirect('vault:setup')

        # Check if already unlocked
        if VaultSessionManager.is_vault_unlocked(request):
            return redirect('vault:dashboard')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vault_config = self.request.user.vault_config

        # Always check if vault is locked and pass to template
        if vault_config.is_locked():
            remaining_time = (vault_config.locked_until - timezone.now()).seconds // 60
            context['locked'] = True
            context['remaining_minutes'] = remaining_time
        else:
            context['locked'] = False

        return context

    def form_valid(self, form):
        master_password = form.cleaned_data['master_password']
        vault_config = self.request.user.vault_config

        try:
            # Convert BinaryField values to bytes if they're memoryview
            master_password_salt = bytes(vault_config.master_password_salt)
            encrypted_dek = bytes(vault_config.encrypted_dek)

            # Verify master password
            is_valid = VaultCryptoService.verify_master_password(
                master_password,
                master_password_salt,
                vault_config.master_password_hash,
                vault_config.kdf_iterations
            )

            if is_valid:
                # Decrypt DEK
                master_key = VaultCryptoService.derive_key_from_master_password(
                    master_password,
                    master_password_salt,
                    vault_config.kdf_iterations
                )
                dek = VaultCryptoService.decrypt_dek(encrypted_dek, master_key)

                # Store DEK in session
                VaultSessionManager.store_dek_in_session(
                    self.request,
                    dek,
                    vault_config.vault_timeout_minutes
                )

                # Reset failed attempts
                vault_config.reset_failed_attempts()

                # Create or update vault session record
                # Ensure session has a key
                if not self.request.session.session_key:
                    self.request.session.create()

                VaultSession.objects.update_or_create(
                    session_key=self.request.session.session_key,
                    defaults={
                        'user': self.request.user,
                        'expires_at': timezone.now() + timezone.timedelta(minutes=vault_config.vault_timeout_minutes),
                        'ip_address': get_client_ip(self.request),
                        'user_agent': self.request.META.get('HTTP_USER_AGENT', '')[:255],
                        'is_active': True,
                        'unlocked_at': timezone.now(),
                    }
                )

                # Log successful unlock
                log_vault_action(self.request, 'unlock', success=True)

                messages.success(self.request, 'Vault unlocked successfully!')
                return super().form_valid(form)
            else:
                # Invalid password
                vault_config.failed_attempts += 1

                # Check if we should lock the vault
                if vault_config.failed_attempts >= vault_config.max_failed_attempts:
                    from django.conf import settings
                    lockout_minutes = settings.VAULT_SETTINGS.get('LOCKOUT_DURATION_MINUTES', 30)
                    vault_config.locked_until = timezone.now() + timezone.timedelta(minutes=lockout_minutes)
                    vault_config.save()

                    log_vault_action(self.request, 'failed_unlock', success=False)
                    # Error will be shown via template context in get_context_data()
                else:
                    vault_config.save()
                    remaining_attempts = vault_config.max_failed_attempts - vault_config.failed_attempts
                    log_vault_action(self.request, 'failed_unlock', success=False)
                    from django.contrib.messages import constants as message_constants
                    messages.add_message(
                        self.request,
                        message_constants.ERROR,
                        f'Invalid master password. {remaining_attempts} attempt{"s" if remaining_attempts != 1 else ""} remaining.',
                        extra_tags='danger'
                    )

                return self.form_invalid(form)

        except InvalidToken:
            log_vault_action(self.request, 'failed_unlock', success=False)
            from django.contrib.messages import constants as message_constants
            messages.add_message(
                self.request,
                message_constants.ERROR,
                'Failed to decrypt vault. Please contact support.',
                extra_tags='danger'
            )
            return self.form_invalid(form)


@login_required
def vault_lock(request):
    """Lock the vault."""
    VaultSessionManager.lock_vault(request)

    # Mark session as inactive
    VaultSession.objects.filter(
        user=request.user,
        session_key=request.session.session_key,
        is_active=True
    ).update(is_active=False)

    log_vault_action(request, 'lock', success=True)
    messages.success(request, 'Vault locked successfully.')
    return redirect('vault:unlock')


class VaultDashboardView(VaultRequiredMixin, TemplateView):
    """Vault dashboard view."""
    template_name = 'vault/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dek = VaultSessionManager.get_dek_from_session(self.request)

        # Get counts
        context['credential_count'] = VaultCredential.objects.filter(user=self.request.user).count()
        context['note_count'] = VaultSecureNote.objects.filter(user=self.request.user).count()
        context['file_count'] = VaultFile.objects.filter(user=self.request.user).count()
        context['apikey_count'] = VaultAPIKey.objects.filter(user=self.request.user).count()

        # Get recent items (decrypt names for display)
        recent_credentials = VaultCredential.objects.filter(user=self.request.user)[:5]
        recent_notes = VaultSecureNote.objects.filter(user=self.request.user)[:5]

        # Decrypt names for display
        for item in recent_credentials:
            try:
                item.decrypted_name = VaultCryptoService.decrypt_field(item.name, dek)
            except:
                item.decrypted_name = '[Decryption Error]'

        for item in recent_notes:
            try:
                item.decrypted_name = VaultCryptoService.decrypt_field(item.name, dek)
            except:
                item.decrypted_name = '[Decryption Error]'

        context['recent_credentials'] = recent_credentials
        context['recent_notes'] = recent_notes

        # Vault session info
        context['time_remaining'] = VaultSessionManager.get_time_remaining(
            self.request,
            self.request.user.vault_config.vault_timeout_minutes
        )

        return context


# Credential Views
class CredentialListView(VaultRequiredMixin, ListView):
    """List all credentials."""
    model = VaultCredential
    template_name = 'vault/credential_list.html'
    context_object_name = 'credentials'
    paginate_by = 20

    def get_queryset(self):
        queryset = VaultCredential.objects.filter(user=self.request.user)
        dek = VaultSessionManager.get_dek_from_session(self.request)

        # Decrypt names for display
        for item in queryset:
            try:
                item.decrypted_name = VaultCryptoService.decrypt_field(item.name, dek)
            except:
                item.decrypted_name = '[Decryption Error]'

        return queryset


class CredentialDetailView(VaultRequiredMixin, DetailView):
    """View credential details."""
    model = VaultCredential
    template_name = 'vault/credential_detail.html'
    context_object_name = 'credential'

    def get_queryset(self):
        return VaultCredential.objects.filter(user=self.request.user)

    def dispatch(self, request, *args, **kwargs):
        # Check if re-authentication is required
        if not self._check_reauth_session():
            # Store the intended URL
            request.session['vault_reauth_next'] = request.get_full_path()
            return redirect('vault:reauth', pk=kwargs.get('pk'))

        return super().dispatch(request, *args, **kwargs)

    def _check_reauth_session(self):
        """Check if user has recently re-authenticated."""
        reauth_time = self.request.session.get('vault_reauth_time')
        if not reauth_time:
            return False

        # Re-auth valid for 5 minutes
        from datetime import datetime
        reauth_datetime = datetime.fromisoformat(reauth_time)
        if timezone.is_naive(reauth_datetime):
            reauth_datetime = timezone.make_aware(reauth_datetime)

        elapsed = (timezone.now() - reauth_datetime).total_seconds()
        return elapsed < 300  # 5 minutes

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dek = VaultSessionManager.get_dek_from_session(self.request)
        credential = self.object

        # Decrypt fields
        try:
            credential.decrypted_name = VaultCryptoService.decrypt_field(credential.name, dek)
            credential.decrypted_username = VaultCryptoService.decrypt_field(credential.username, dek)
            credential.decrypted_password = VaultCryptoService.decrypt_field(credential.password, dek)
            credential.decrypted_website_url = VaultCryptoService.decrypt_field(credential.website_url, dek)
            credential.decrypted_email = VaultCryptoService.decrypt_field(credential.email, dek)
            credential.decrypted_notes = VaultCryptoService.decrypt_field(credential.notes, dek)
        except Exception as e:
            messages.error(self.request, 'Failed to decrypt credential data.')

        log_vault_action(self.request, 'view', success=True, item_type='credential', item_id=credential.id)
        log_vault_action(self.request, 'password_reveal', success=True, item_type='credential', item_id=credential.id)

        return context


class CredentialCreateView(VaultRequiredMixin, CreateView):
    """Create new credential."""
    model = VaultCredential
    form_class = VaultCredentialForm
    template_name = 'vault/credential_form.html'
    success_url = reverse_lazy('vault:credential_list')

    def form_valid(self, form):
        dek = VaultSessionManager.get_dek_from_session(self.request)
        credential = form.save(commit=False)
        credential.user = self.request.user

        # Generate IV for encryption
        credential.encryption_iv = VaultCryptoService.generate_salt()[:16]

        # Encrypt fields
        credential.name = VaultCryptoService.encrypt_field(form.cleaned_data['name'], dek)
        credential.username = VaultCryptoService.encrypt_field(form.cleaned_data['username'], dek)
        password = form.cleaned_data.get('plaintext_password') or form.cleaned_data.get('password', '')
        credential.password = VaultCryptoService.encrypt_field(password, dek)
        credential.website_url = VaultCryptoService.encrypt_field(form.cleaned_data.get('website_url', ''), dek)
        credential.email = VaultCryptoService.encrypt_field(form.cleaned_data.get('email', ''), dek)
        credential.notes = VaultCryptoService.encrypt_field(form.cleaned_data.get('notes', ''), dek)
        credential.totp_secret = VaultCryptoService.encrypt_field(form.cleaned_data.get('totp_secret', ''), dek)

        credential.save()

        log_vault_action(self.request, 'create', success=True, item_type='credential', item_id=credential.id)
        messages.success(self.request, 'Credential created successfully!')

        return redirect(self.success_url)


class CredentialUpdateView(VaultRequiredMixin, UpdateView):
    """Update credential."""
    model = VaultCredential
    form_class = VaultCredentialForm
    template_name = 'vault/credential_form.html'

    def get_queryset(self):
        return VaultCredential.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse('vault:credential_detail', kwargs={'pk': self.object.pk})

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        dek = VaultSessionManager.get_dek_from_session(self.request)

        # Decrypt fields for editing
        try:
            form.initial['name'] = VaultCryptoService.decrypt_field(self.object.name, dek)
            form.initial['username'] = VaultCryptoService.decrypt_field(self.object.username, dek)
            form.initial['plaintext_password'] = VaultCryptoService.decrypt_field(self.object.password, dek)
            form.initial['website_url'] = VaultCryptoService.decrypt_field(self.object.website_url, dek)
            form.initial['email'] = VaultCryptoService.decrypt_field(self.object.email, dek)
            form.initial['notes'] = VaultCryptoService.decrypt_field(self.object.notes, dek)
            form.initial['totp_secret'] = VaultCryptoService.decrypt_field(self.object.totp_secret, dek)
        except:
            messages.error(self.request, 'Failed to decrypt some fields.')

        return form

    def form_valid(self, form):
        dek = VaultSessionManager.get_dek_from_session(self.request)
        credential = form.save(commit=False)

        # Re-encrypt fields
        credential.name = VaultCryptoService.encrypt_field(form.cleaned_data['name'], dek)
        credential.username = VaultCryptoService.encrypt_field(form.cleaned_data['username'], dek)
        password = form.cleaned_data.get('plaintext_password') or form.cleaned_data.get('password', '')
        credential.password = VaultCryptoService.encrypt_field(password, dek)
        credential.website_url = VaultCryptoService.encrypt_field(form.cleaned_data.get('website_url', ''), dek)
        credential.email = VaultCryptoService.encrypt_field(form.cleaned_data.get('email', ''), dek)
        credential.notes = VaultCryptoService.encrypt_field(form.cleaned_data.get('notes', ''), dek)
        credential.totp_secret = VaultCryptoService.encrypt_field(form.cleaned_data.get('totp_secret', ''), dek)

        credential.save()

        log_vault_action(self.request, 'update', success=True, item_type='credential', item_id=credential.id)
        messages.success(self.request, 'Credential updated successfully!')

        return redirect(self.get_success_url())


class CredentialDeleteView(VaultRequiredMixin, DeleteView):
    """Delete credential."""
    model = VaultCredential
    template_name = 'vault/credential_confirm_delete.html'
    success_url = reverse_lazy('vault:credential_list')

    def get_queryset(self):
        return VaultCredential.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        credential = self.get_object()
        log_vault_action(request, 'delete', success=True, item_type='credential', item_id=credential.id)
        messages.success(request, 'Credential deleted successfully!')
        return super().delete(request, *args, **kwargs)


# Secure Note Views (similar pattern)
class SecureNoteListView(VaultRequiredMixin, ListView):
    """List all secure notes."""
    model = VaultSecureNote
    template_name = 'vault/note_list.html'
    context_object_name = 'notes'
    paginate_by = 20

    def get_queryset(self):
        queryset = VaultSecureNote.objects.filter(user=self.request.user)
        dek = VaultSessionManager.get_dek_from_session(self.request)

        for item in queryset:
            try:
                item.decrypted_name = VaultCryptoService.decrypt_field(item.name, dek)
            except:
                item.decrypted_name = '[Decryption Error]'

        return queryset


class SecureNoteDetailView(VaultRequiredMixin, DetailView):
    """View secure note details."""
    model = VaultSecureNote
    template_name = 'vault/note_detail.html'
    context_object_name = 'note'

    def get_queryset(self):
        return VaultSecureNote.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dek = VaultSessionManager.get_dek_from_session(self.request)
        note = self.object

        try:
            note.decrypted_name = VaultCryptoService.decrypt_field(note.name, dek)
            note.decrypted_content = VaultCryptoService.decrypt_field(note.content, dek)
            note.decrypted_notes = VaultCryptoService.decrypt_field(note.notes, dek)
        except:
            messages.error(self.request, 'Failed to decrypt note data.')

        log_vault_action(self.request, 'view', success=True, item_type='note', item_id=note.id)

        return context


class SecureNoteCreateView(VaultRequiredMixin, CreateView):
    """Create new secure note."""
    model = VaultSecureNote
    form_class = VaultSecureNoteForm
    template_name = 'vault/note_form.html'
    success_url = reverse_lazy('vault:note_list')

    def form_valid(self, form):
        dek = VaultSessionManager.get_dek_from_session(self.request)
        note = form.save(commit=False)
        note.user = self.request.user
        note.encryption_iv = VaultCryptoService.generate_salt()[:16]

        note.name = VaultCryptoService.encrypt_field(form.cleaned_data['name'], dek)
        note.content = VaultCryptoService.encrypt_field(form.cleaned_data['content'], dek)
        note.notes = VaultCryptoService.encrypt_field(form.cleaned_data.get('notes', ''), dek)

        note.save()

        log_vault_action(self.request, 'create', success=True, item_type='note', item_id=note.id)
        messages.success(self.request, 'Secure note created successfully!')

        return redirect(self.success_url)


class SecureNoteUpdateView(VaultRequiredMixin, UpdateView):
    """Update secure note."""
    model = VaultSecureNote
    form_class = VaultSecureNoteForm
    template_name = 'vault/note_form.html'

    def get_queryset(self):
        return VaultSecureNote.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse('vault:note_detail', kwargs={'pk': self.object.pk})

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        dek = VaultSessionManager.get_dek_from_session(self.request)

        try:
            form.initial['name'] = VaultCryptoService.decrypt_field(self.object.name, dek)
            form.initial['content'] = VaultCryptoService.decrypt_field(self.object.content, dek)
            form.initial['notes'] = VaultCryptoService.decrypt_field(self.object.notes, dek)
        except:
            messages.error(self.request, 'Failed to decrypt some fields.')

        return form

    def form_valid(self, form):
        dek = VaultSessionManager.get_dek_from_session(self.request)
        note = form.save(commit=False)

        note.name = VaultCryptoService.encrypt_field(form.cleaned_data['name'], dek)
        note.content = VaultCryptoService.encrypt_field(form.cleaned_data['content'], dek)
        note.notes = VaultCryptoService.encrypt_field(form.cleaned_data.get('notes', ''), dek)

        note.save()

        log_vault_action(self.request, 'update', success=True, item_type='note', item_id=note.id)
        messages.success(self.request, 'Secure note updated successfully!')

        return redirect(self.get_success_url())


class SecureNoteDeleteView(VaultRequiredMixin, DeleteView):
    """Delete secure note."""
    model = VaultSecureNote
    template_name = 'vault/note_confirm_delete.html'
    success_url = reverse_lazy('vault:note_list')

    def get_queryset(self):
        return VaultSecureNote.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        note = self.get_object()
        log_vault_action(request, 'delete', success=True, item_type='note', item_id=note.id)
        messages.success(request, 'Secure note deleted successfully!')
        return super().delete(request, *args, **kwargs)


# File Views
class FileListView(VaultRequiredMixin, ListView):
    """List all encrypted files."""
    model = VaultFile
    template_name = 'vault/file_list.html'
    context_object_name = 'files'
    paginate_by = 20

    def get_queryset(self):
        queryset = VaultFile.objects.filter(user=self.request.user)
        dek = VaultSessionManager.get_dek_from_session(self.request)

        for item in queryset:
            try:
                item.decrypted_name = VaultCryptoService.decrypt_field(item.name, dek)
                item.decrypted_filename = VaultCryptoService.decrypt_field(item.original_filename, dek)
            except:
                item.decrypted_name = '[Decryption Error]'
                item.decrypted_filename = '[Decryption Error]'

        return queryset


class FileDetailView(VaultRequiredMixin, DetailView):
    """View file details."""
    model = VaultFile
    template_name = 'vault/file_detail.html'
    context_object_name = 'file'

    def get_queryset(self):
        return VaultFile.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dek = VaultSessionManager.get_dek_from_session(self.request)
        file_obj = self.object

        try:
            file_obj.decrypted_name = VaultCryptoService.decrypt_field(file_obj.name, dek)
            file_obj.decrypted_filename = VaultCryptoService.decrypt_field(file_obj.original_filename, dek)
            file_obj.decrypted_notes = VaultCryptoService.decrypt_field(file_obj.notes, dek)
        except:
            messages.error(self.request, 'Failed to decrypt file metadata.')

        log_vault_action(self.request, 'view', success=True, item_type='file', item_id=file_obj.id)

        return context


class FileCreateView(VaultRequiredMixin, CreateView):
    """Upload encrypted file."""
    model = VaultFile
    form_class = VaultFileForm
    template_name = 'vault/file_form.html'
    success_url = reverse_lazy('vault:file_list')

    def form_valid(self, form):
        dek = VaultSessionManager.get_dek_from_session(self.request)
        file_obj = form.save(commit=False)
        file_obj.user = self.request.user
        file_obj.encryption_iv = VaultCryptoService.generate_salt()[:16]
        file_obj.file_encryption_iv = VaultCryptoService.generate_salt()[:16]

        # Get uploaded file
        uploaded_file = form.cleaned_data['encrypted_file']

        # Read file content
        file_content = uploaded_file.read()
        file_obj.file_size = len(file_content)

        # Encrypt file content
        encrypted_content = VaultCryptoService.encrypt_file(file_content, dek)
        file_obj.encrypted_file_size = len(encrypted_content)

        # Calculate checksum of original file
        file_obj.checksum_sha256 = hashlib.sha256(file_content).hexdigest()

        # Save encrypted file
        from django.core.files.base import ContentFile
        file_obj.encrypted_file.save(uploaded_file.name, ContentFile(encrypted_content), save=False)

        # Encrypt metadata
        file_obj.name = VaultCryptoService.encrypt_field(form.cleaned_data['name'], dek)
        file_obj.original_filename = VaultCryptoService.encrypt_field(uploaded_file.name, dek)
        file_obj.notes = VaultCryptoService.encrypt_field(form.cleaned_data.get('notes', ''), dek)

        # Store file metadata
        file_obj.mime_type = mimetypes.guess_type(uploaded_file.name)[0] or 'application/octet-stream'
        file_obj.file_extension = uploaded_file.name.split('.')[-1] if '.' in uploaded_file.name else ''

        file_obj.save()

        log_vault_action(self.request, 'create', success=True, item_type='file', item_id=file_obj.id)
        messages.success(self.request, 'File uploaded and encrypted successfully!')

        return redirect(self.success_url)


@login_required
def file_download(request, pk):
    """Download and decrypt file."""
    # Check vault is unlocked
    if not VaultSessionManager.is_vault_unlocked(request):
        messages.warning(request, 'Please unlock your vault first.')
        return redirect('vault:unlock')

    file_obj = get_object_or_404(VaultFile, pk=pk, user=request.user)
    dek = VaultSessionManager.get_dek_from_session(request)

    try:
        # Decrypt filename
        original_filename = VaultCryptoService.decrypt_field(file_obj.original_filename, dek)

        # Read and decrypt file
        with file_obj.encrypted_file.open('rb') as f:
            encrypted_content = f.read()

        decrypted_content = VaultCryptoService.decrypt_file(encrypted_content, dek)

        # Verify checksum
        checksum = hashlib.sha256(decrypted_content).hexdigest()
        if checksum != file_obj.checksum_sha256:
            messages.error(request, 'File integrity check failed!')
            return redirect('vault:file_detail', pk=pk)

        # Create response
        response = HttpResponse(decrypted_content, content_type=file_obj.mime_type)
        response['Content-Disposition'] = f'attachment; filename="{original_filename}"'
        response['Content-Length'] = len(decrypted_content)

        log_vault_action(request, 'file_download', success=True, item_type='file', item_id=file_obj.id)

        return response

    except Exception as e:
        messages.error(request, 'Failed to decrypt file.')
        return redirect('vault:file_detail', pk=pk)


class FileDeleteView(VaultRequiredMixin, DeleteView):
    """Delete encrypted file."""
    model = VaultFile
    template_name = 'vault/file_confirm_delete.html'
    success_url = reverse_lazy('vault:file_list')

    def get_queryset(self):
        return VaultFile.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        file_obj = self.get_object()
        log_vault_action(request, 'delete', success=True, item_type='file', item_id=file_obj.id)
        messages.success(request, 'File deleted successfully!')
        return super().delete(request, *args, **kwargs)


# API Key Views (similar pattern to credentials)
class APIKeyListView(VaultRequiredMixin, ListView):
    """List all API keys."""
    model = VaultAPIKey
    template_name = 'vault/apikey_list.html'
    context_object_name = 'apikeys'
    paginate_by = 20

    def get_queryset(self):
        queryset = VaultAPIKey.objects.filter(user=self.request.user)
        dek = VaultSessionManager.get_dek_from_session(self.request)

        for item in queryset:
            try:
                item.decrypted_name = VaultCryptoService.decrypt_field(item.name, dek)
                item.decrypted_service_name = VaultCryptoService.decrypt_field(item.service_name, dek)
            except:
                item.decrypted_name = '[Decryption Error]'
                item.decrypted_service_name = '[Decryption Error]'

        return queryset


class APIKeyDetailView(VaultRequiredMixin, DetailView):
    """View API key details."""
    model = VaultAPIKey
    template_name = 'vault/apikey_detail.html'
    context_object_name = 'apikey'

    def get_queryset(self):
        return VaultAPIKey.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dek = VaultSessionManager.get_dek_from_session(self.request)
        apikey = self.object

        try:
            apikey.decrypted_name = VaultCryptoService.decrypt_field(apikey.name, dek)
            apikey.decrypted_service_name = VaultCryptoService.decrypt_field(apikey.service_name, dek)
            apikey.decrypted_api_key = VaultCryptoService.decrypt_field(apikey.api_key, dek)
            apikey.decrypted_api_secret = VaultCryptoService.decrypt_field(apikey.api_secret, dek)
            apikey.decrypted_notes = VaultCryptoService.decrypt_field(apikey.notes, dek)
        except:
            messages.error(self.request, 'Failed to decrypt API key data.')

        log_vault_action(self.request, 'view', success=True, item_type='apikey', item_id=apikey.id)

        return context


class APIKeyCreateView(VaultRequiredMixin, CreateView):
    """Create new API key."""
    model = VaultAPIKey
    form_class = VaultAPIKeyForm
    template_name = 'vault/apikey_form.html'
    success_url = reverse_lazy('vault:apikey_list')

    def form_valid(self, form):
        dek = VaultSessionManager.get_dek_from_session(self.request)
        apikey = form.save(commit=False)
        apikey.user = self.request.user
        apikey.encryption_iv = VaultCryptoService.generate_salt()[:16]

        apikey.name = VaultCryptoService.encrypt_field(form.cleaned_data['name'], dek)
        apikey.service_name = VaultCryptoService.encrypt_field(form.cleaned_data['service_name'], dek)
        apikey.api_key = VaultCryptoService.encrypt_field(form.cleaned_data['api_key'], dek)
        apikey.api_secret = VaultCryptoService.encrypt_field(form.cleaned_data.get('api_secret', ''), dek)
        apikey.notes = VaultCryptoService.encrypt_field(form.cleaned_data.get('notes', ''), dek)

        apikey.save()

        log_vault_action(self.request, 'create', success=True, item_type='apikey', item_id=apikey.id)
        messages.success(self.request, 'API key created successfully!')

        return redirect(self.success_url)


class APIKeyUpdateView(VaultRequiredMixin, UpdateView):
    """Update API key."""
    model = VaultAPIKey
    form_class = VaultAPIKeyForm
    template_name = 'vault/apikey_form.html'

    def get_queryset(self):
        return VaultAPIKey.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse('vault:apikey_detail', kwargs={'pk': self.object.pk})

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        dek = VaultSessionManager.get_dek_from_session(self.request)

        try:
            form.initial['name'] = VaultCryptoService.decrypt_field(self.object.name, dek)
            form.initial['service_name'] = VaultCryptoService.decrypt_field(self.object.service_name, dek)
            form.initial['api_key'] = VaultCryptoService.decrypt_field(self.object.api_key, dek)
            form.initial['api_secret'] = VaultCryptoService.decrypt_field(self.object.api_secret, dek)
            form.initial['notes'] = VaultCryptoService.decrypt_field(self.object.notes, dek)
        except:
            messages.error(self.request, 'Failed to decrypt some fields.')

        return form

    def form_valid(self, form):
        dek = VaultSessionManager.get_dek_from_session(self.request)
        apikey = form.save(commit=False)

        apikey.name = VaultCryptoService.encrypt_field(form.cleaned_data['name'], dek)
        apikey.service_name = VaultCryptoService.encrypt_field(form.cleaned_data['service_name'], dek)
        apikey.api_key = VaultCryptoService.encrypt_field(form.cleaned_data['api_key'], dek)
        apikey.api_secret = VaultCryptoService.encrypt_field(form.cleaned_data.get('api_secret', ''), dek)
        apikey.notes = VaultCryptoService.encrypt_field(form.cleaned_data.get('notes', ''), dek)

        apikey.save()

        log_vault_action(self.request, 'update', success=True, item_type='apikey', item_id=apikey.id)
        messages.success(self.request, 'API key updated successfully!')

        return redirect(self.get_success_url())


class APIKeyDeleteView(VaultRequiredMixin, DeleteView):
    """Delete API key."""
    model = VaultAPIKey
    template_name = 'vault/apikey_confirm_delete.html'
    success_url = reverse_lazy('vault:apikey_list')

    def get_queryset(self):
        return VaultAPIKey.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        apikey = self.get_object()
        log_vault_action(request, 'delete', success=True, item_type='apikey', item_id=apikey.id)
        messages.success(request, 'API key deleted successfully!')
        return super().delete(request, *args, **kwargs)


# Additional Views
class VaultSettingsView(VaultRequiredMixin, UpdateView):
    """Vault settings view."""
    model = VaultConfig
    form_class = VaultConfigForm
    template_name = 'vault/settings.html'
    success_url = reverse_lazy('vault:dashboard')

    def get_object(self, queryset=None):
        return self.request.user.vault_config


class VaultAuditLogView(VaultRequiredMixin, ListView):
    """View audit log."""
    model = VaultAuditLog
    template_name = 'vault/audit_log.html'
    context_object_name = 'logs'
    paginate_by = 50

    def get_queryset(self):
        return VaultAuditLog.objects.filter(user=self.request.user)


class VaultSearchView(VaultRequiredMixin, ListView):
    """Search vault items."""
    template_name = 'vault/search.html'
    context_object_name = 'results'
    paginate_by = 20

    def get_queryset(self):
        # This is a simplified search - in production you'd want more sophisticated searching
        return []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = VaultSearchForm(self.request.GET)
        return context


class VaultReAuthView(VaultRequiredMixin, FormView):
    """Re-authenticate with master password before viewing sensitive data."""
    template_name = 'vault/reauth.html'
    form_class = VaultReAuthForm

    def get_success_url(self):
        return self.request.session.get('vault_reauth_next', reverse('vault:dashboard'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get the item being accessed for display
        pk = self.kwargs.get('pk')
        if pk:
            try:
                credential = VaultCredential.objects.get(pk=pk, user=self.request.user)
                dek = VaultSessionManager.get_dek_from_session(self.request)
                context['item_name'] = VaultCryptoService.decrypt_field(credential.name, dek)
            except:
                context['item_name'] = 'this item'
        return context

    def form_valid(self, form):
        master_password = form.cleaned_data['master_password']
        vault_config = self.request.user.vault_config

        # Convert BinaryField values to bytes if they're memoryview
        master_password_salt = bytes(vault_config.master_password_salt)

        # Verify master password
        is_valid = VaultCryptoService.verify_master_password(
            master_password,
            master_password_salt,
            vault_config.master_password_hash,
            vault_config.kdf_iterations
        )

        if is_valid:
            # Store re-authentication time in session
            self.request.session['vault_reauth_time'] = timezone.now().isoformat()
            self.request.session.modified = True

            log_vault_action(self.request, 'password_reveal', success=True, details={'reauth': True})
            messages.success(self.request, 'Master password verified.')

            # Clear the next URL from session
            if 'vault_reauth_next' in self.request.session:
                del self.request.session['vault_reauth_next']

            return super().form_valid(form)
        else:
            log_vault_action(self.request, 'password_reveal', success=False, details={'reauth_failed': True})
            from django.contrib.messages import constants as message_constants
            messages.add_message(
                self.request,
                message_constants.ERROR,
                'Invalid master password. Please try again.',
                extra_tags='danger'
            )
            return self.form_invalid(form)
