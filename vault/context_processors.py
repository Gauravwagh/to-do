"""
Context processors for vault app.
"""
from .models import VaultConfig, VaultCredential, VaultSecureNote, VaultFile, VaultAPIKey
from .session import VaultSessionManager


def vault_stats(request):
    """
    Add vault statistics to template context.
    """
    context = {
        'vault_is_initialized': False,
        'vault_is_unlocked': False,
        'vault_credential_count': 0,
        'vault_note_count': 0,
        'vault_file_count': 0,
        'vault_apikey_count': 0,
        'vault_total_items': 0,
    }

    if request.user.is_authenticated:
        try:
            vault_config = request.user.vault_config
            context['vault_is_initialized'] = vault_config.is_initialized
            context['vault_is_unlocked'] = VaultSessionManager.is_vault_unlocked(request)

            # Get vault item counts
            context['vault_credential_count'] = VaultCredential.objects.filter(user=request.user).count()
            context['vault_note_count'] = VaultSecureNote.objects.filter(user=request.user).count()
            context['vault_file_count'] = VaultFile.objects.filter(user=request.user).count()
            context['vault_apikey_count'] = VaultAPIKey.objects.filter(user=request.user).count()
            context['vault_total_items'] = (
                context['vault_credential_count'] +
                context['vault_note_count'] +
                context['vault_file_count'] +
                context['vault_apikey_count']
            )
        except VaultConfig.DoesNotExist:
            pass

    return context
