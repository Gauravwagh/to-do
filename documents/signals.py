"""
Django signals for document library.

Signals:
- Auto-create UserStorageQuota when user is created
- Trigger compression after document upload
- Update quota when document is created/deleted
- Clean up files when document is deleted
"""
import logging
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.conf import settings

from .models import Document, UserStorageQuota
from .tasks import compress_document_task, recalculate_user_quota

logger = logging.getLogger(__name__)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_storage_quota(sender, instance, created, **kwargs):
    """
    Create UserStorageQuota when a new user is created.
    """
    if created:
        UserStorageQuota.objects.create(user=instance)
        logger.info(f"Created storage quota for user {instance.username}")


@receiver(post_save, sender=Document)
def trigger_document_compression(sender, instance, created, **kwargs):
    """
    Trigger compression task after document is uploaded.
    Only triggers for new documents with 'pending' compression status.
    """
    if created and instance.compression_status == 'pending':
        # Trigger compression task asynchronously
        compress_document_task.delay(str(instance.id))
        logger.info(f"Queued compression task for document {instance.id}")


@receiver(post_save, sender=Document)
def update_quota_on_document_save(sender, instance, created, **kwargs):
    """
    Update user quota when document is created or modified.
    """
    # Delay quota recalculation to avoid race conditions
    recalculate_user_quota.apply_async(
        args=[str(instance.user.id)],
        countdown=5  # Wait 5 seconds
    )


@receiver(pre_delete, sender=Document)
def cleanup_document_files(sender, instance, **kwargs):
    """
    Clean up document files and backups before deletion.
    """
    import os

    # Delete main file
    if instance.file and os.path.exists(instance.file.path):
        try:
            os.remove(instance.file.path)
            logger.info(f"Deleted file for document {instance.id}")
        except Exception as e:
            logger.error(f"Failed to delete file for document {instance.id}: {str(e)}")

    # Delete backup if exists
    if hasattr(instance, 'backup'):
        try:
            backup = instance.backup
            if backup.backup_file and os.path.exists(backup.backup_file.path):
                os.remove(backup.backup_file.path)
                logger.info(f"Deleted backup file for document {instance.id}")
        except Exception as e:
            logger.error(f"Failed to delete backup for document {instance.id}: {str(e)}")


@receiver(post_delete, sender=Document)
def update_quota_on_document_delete(sender, instance, **kwargs):
    """
    Update user quota when document is deleted.
    """
    # Recalculate quota after deletion
    recalculate_user_quota.apply_async(
        args=[str(instance.user.id)],
        countdown=5  # Wait 5 seconds
    )
