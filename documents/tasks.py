"""
Celery tasks for document library.

Tasks:
- compress_document - Compress uploaded document
- bulk_compress_documents - Bulk compression job
- decompress_document - On-demand decompression
- send_email_share - Send document via email
- cleanup_expired_backups - Clean up old backups
- cleanup_temp_files - Clean up temporary decompressed files
- validate_compressions - Validate random sample of compressions
- recalculate_user_quota - Recalculate storage quota for user
"""
import os
import time
import logging
from datetime import timedelta
from pathlib import Path
from typing import Optional

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone
from django.db import transaction
from django.core.files.base import File

from .models import (
    Document,
    DocumentBackup,
    UserStorageQuota,
    CompressionStats,
)
from .utils.compression import (
    compress_file,
    decompress_file,
    calculate_checksum,
    should_compress_file,
    select_compression_algorithm,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def compress_document_task(self, document_id: str):
    """
    Compress a document in the background.

    Args:
        document_id: UUID of the document to compress

    Returns:
        dict with compression results
    """
    try:
        document = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found")
        return {'error': 'Document not found'}

    try:
        # Update status to compressing
        document.compression_status = 'compressing'
        document.save(update_fields=['compression_status'])

        # Get file path
        original_path = document.file.path

        # Check if we should compress
        file_size = os.path.getsize(original_path)
        if not should_compress_file(original_path, document.file_type, file_size):
            document.compression_status = 'uncompressed'
            document.is_compressed = False
            document.compressed_file_size = file_size
            document.compression_algorithm = 'none'
            document.save(update_fields=[
                'compression_status',
                'is_compressed',
                'compressed_file_size',
                'compression_algorithm'
            ])
            logger.info(f"Document {document_id} skipped compression (not beneficial)")
            return {'status': 'skipped', 'reason': 'compression not beneficial'}

        # Select compression algorithm
        algorithm = select_compression_algorithm(document.file_type)

        # Create backup of original file
        if settings.BACKUP_ENABLED:
            backup_path = original_path + '.backup'
            import shutil
            shutil.copy2(original_path, backup_path)

            # Create backup record
            backup = DocumentBackup.objects.create(
                document=document,
                backup_file=backup_path
            )

        # Compress file
        compressed_path = original_path + '.compressed'
        start_time = time.time()

        original_size, compressed_size, compression_ratio, algorithm_used = compress_file(
            input_path=original_path,
            output_path=compressed_path,
            algorithm=algorithm,
            level=settings.COMPRESSION_LEVEL
        )

        compression_time = (time.time() - start_time) * 1000  # milliseconds

        # Calculate checksum of compressed file
        compressed_checksum = calculate_checksum(compressed_path)

        # Verify compression was beneficial (at least 5% reduction)
        if compression_ratio > 0.95:
            # Compression not beneficial, keep original
            os.remove(compressed_path)
            document.compression_status = 'uncompressed'
            document.is_compressed = False
            document.compressed_file_size = original_size
            document.compression_algorithm = 'none'
            document.save(update_fields=[
                'compression_status',
                'is_compressed',
                'compressed_file_size',
                'compression_algorithm'
            ])
            logger.info(f"Document {document_id} compression ratio too low: {compression_ratio}")
            return {'status': 'skipped', 'reason': 'compression ratio too low'}

        # Replace original file with compressed file
        os.remove(original_path)
        os.rename(compressed_path, original_path)

        # Update document
        document.compressed_file_size = compressed_size
        document.compression_ratio = compression_ratio
        document.compression_algorithm = algorithm_used
        document.is_compressed = True
        document.compressed_file_checksum = compressed_checksum
        document.compression_timestamp = timezone.now()
        document.compression_status = 'compressed'
        document.decompression_failed = False
        document.save()

        # Update compression stats
        stats, created = CompressionStats.objects.get_or_create(
            user=document.user,
            file_type=document.file_type,
            algorithm=algorithm_used
        )
        stats.update_stats(original_size, compressed_size, compression_time)

        # Update user quota
        recalculate_user_quota.delay(str(document.user.id))

        logger.info(
            f"Document {document_id} compressed successfully. "
            f"Original: {original_size}, Compressed: {compressed_size}, "
            f"Ratio: {compression_ratio:.2%}"
        )

        return {
            'status': 'success',
            'original_size': original_size,
            'compressed_size': compressed_size,
            'compression_ratio': compression_ratio,
            'algorithm': algorithm_used,
            'compression_time': compression_time
        }

    except Exception as e:
        logger.error(f"Compression failed for document {document_id}: {str(e)}")

        # Update document status
        document.compression_status = 'failed'
        document.save(update_fields=['compression_status'])

        # Update failure stats
        try:
            stats, created = CompressionStats.objects.get_or_create(
                user=document.user,
                file_type=document.file_type,
                algorithm=algorithm or 'zstd'
            )
            stats.update_stats(0, 0, 0, failed=True)
        except Exception:
            pass

        # Retry
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

        return {'error': str(e)}


@shared_task
def decompress_document_task(document_id: str, output_path: str):
    """
    Decompress a document to a temporary location for download/preview.

    Args:
        document_id: UUID of the document
        output_path: Path where decompressed file should be saved

    Returns:
        dict with decompression results
    """
    try:
        document = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found")
        return {'error': 'Document not found'}

    try:
        # Check if document is compressed
        if not document.is_compressed or document.compression_algorithm == 'none':
            # Just copy the file
            import shutil
            shutil.copy2(document.file.path, output_path)
            return {
                'status': 'success',
                'decompressed_size': os.path.getsize(output_path)
            }

        # Decompress file
        decompressed_size, checksum = decompress_file(
            input_path=document.file.path,
            output_path=output_path,
            algorithm=document.compression_algorithm
        )

        # Verify checksum
        if checksum != document.original_file_checksum:
            logger.error(
                f"Checksum mismatch for document {document_id}. "
                f"Expected: {document.original_file_checksum}, Got: {checksum}"
            )
            # Try to restore from backup
            if hasattr(document, 'backup') and not document.backup.is_expired():
                import shutil
                shutil.copy2(document.backup.backup_file.path, output_path)
                document.backup.is_used_for_recovery = True
                document.backup.save()
                logger.info(f"Document {document_id} restored from backup")
                return {
                    'status': 'success',
                    'decompressed_size': decompressed_size,
                    'restored_from_backup': True
                }
            else:
                document.decompression_failed = True
                document.save(update_fields=['decompression_failed'])
                return {'error': 'Checksum verification failed, no backup available'}

        logger.info(f"Document {document_id} decompressed successfully")

        return {
            'status': 'success',
            'decompressed_size': decompressed_size
        }

    except Exception as e:
        logger.error(f"Decompression failed for document {document_id}: {str(e)}")
        document.decompression_failed = True
        document.save(update_fields=['decompression_failed'])
        return {'error': str(e)}


@shared_task
def bulk_compress_documents_task(user_id: str, document_ids: list, algorithm: Optional[str] = None):
    """
    Compress multiple documents in bulk.

    Args:
        user_id: UUID of the user
        document_ids: List of document UUIDs
        algorithm: Optional compression algorithm override

    Returns:
        dict with bulk compression results
    """
    results = {
        'total': len(document_ids),
        'successful': 0,
        'failed': 0,
        'skipped': 0,
        'total_savings': 0,
        'errors': []
    }

    for doc_id in document_ids:
        try:
            result = compress_document_task(doc_id)
            if result.get('status') == 'success':
                results['successful'] += 1
                savings = result['original_size'] - result['compressed_size']
                results['total_savings'] += savings
            elif result.get('status') == 'skipped':
                results['skipped'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'document_id': doc_id,
                    'error': result.get('error', 'Unknown error')
                })
        except Exception as e:
            results['failed'] += 1
            results['errors'].append({
                'document_id': doc_id,
                'error': str(e)
            })

    logger.info(
        f"Bulk compression completed for user {user_id}. "
        f"Successful: {results['successful']}, Failed: {results['failed']}, "
        f"Skipped: {results['skipped']}"
    )

    return results


@shared_task
def send_email_share_task(share_log_id: str):
    """
    Send document via email.

    Args:
        share_log_id: UUID of the DocumentShareLog

    Returns:
        dict with email send results
    """
    from .models import DocumentShareLog

    try:
        share_log = DocumentShareLog.objects.select_related('document', 'shared_by').get(
            id=share_log_id
        )
    except DocumentShareLog.DoesNotExist:
        logger.error(f"ShareLog {share_log_id} not found")
        return {'error': 'ShareLog not found'}

    try:
        document = share_log.document

        # Generate share link
        if not document.is_public:
            document.generate_share_token()
            if share_log.expiry_date:
                document.share_expiry = share_log.expiry_date
                document.save(update_fields=['share_expiry'])

        # Build share URL
        from django.contrib.sites.shortcuts import get_current_site
        share_url = f"{settings.SITE_URL}/documents/share/{document.share_token}/"

        # Prepare email
        subject = f"{share_log.shared_by.get_full_name() or share_log.shared_by.username} shared a document with you"
        message = f"""
Hello,

{share_log.shared_by.get_full_name() or share_log.shared_by.username} has shared the document "{document.title}" with you.

You can view and download it here: {share_url}

Document details:
- Title: {document.title}
- Type: {document.get_file_type_display()}
- Size: {document.file_size_display}

This link will expire on {share_log.expiry_date.strftime('%B %d, %Y') if share_log.expiry_date else 'never'}.

Best regards,
The Document Library Team
        """

        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[share_log.recipient],
        )

        email.send()

        # Update share log
        share_log.status = 'delivered'
        share_log.save(update_fields=['status'])

        logger.info(f"Email sent successfully for share log {share_log_id}")

        return {
            'status': 'success',
            'recipient': share_log.recipient
        }

    except Exception as e:
        logger.error(f"Email send failed for share log {share_log_id}: {str(e)}")
        share_log.status = 'failed'
        share_log.error_message = str(e)
        share_log.save(update_fields=['status', 'error_message'])
        return {'error': str(e)}


@shared_task
def cleanup_expired_backups_task():
    """
    Clean up expired document backups.

    Returns:
        dict with cleanup results
    """
    expired_backups = DocumentBackup.objects.filter(
        backup_expires__lt=timezone.now()
    )

    count = 0
    for backup in expired_backups:
        try:
            # Delete backup file
            if backup.backup_file and os.path.exists(backup.backup_file.path):
                os.remove(backup.backup_file.path)
            # Delete backup record
            backup.delete()
            count += 1
        except Exception as e:
            logger.error(f"Failed to delete backup {backup.id}: {str(e)}")

    logger.info(f"Cleaned up {count} expired backups")

    return {
        'status': 'success',
        'cleaned_count': count
    }


@shared_task
def cleanup_temp_files_task():
    """
    Clean up temporary decompressed files older than TTL.

    Returns:
        dict with cleanup results
    """
    temp_dir = settings.DECOMPRESSION_TEMP_DIR
    ttl = settings.DECOMPRESSION_TEMP_TTL

    if not os.path.exists(temp_dir):
        return {'status': 'success', 'cleaned_count': 0}

    count = 0
    cutoff_time = time.time() - ttl

    for root, dirs, files in os.walk(temp_dir):
        for filename in files:
            filepath = os.path.join(root, filename)
            try:
                # Check file age
                if os.path.getmtime(filepath) < cutoff_time:
                    os.remove(filepath)
                    count += 1
            except Exception as e:
                logger.error(f"Failed to delete temp file {filepath}: {str(e)}")

    logger.info(f"Cleaned up {count} temporary files")

    return {
        'status': 'success',
        'cleaned_count': count
    }


@shared_task
def validate_compressions_task(user_id: Optional[str] = None, sample_size: int = 10):
    """
    Validate a random sample of compressed documents to ensure integrity.

    Args:
        user_id: Optional user ID to limit validation to specific user
        sample_size: Number of documents to validate

    Returns:
        dict with validation results
    """
    import random
    import tempfile

    # Get sample of compressed documents
    queryset = Document.objects.filter(
        is_compressed=True,
        compression_status='compressed'
    )

    if user_id:
        queryset = queryset.filter(user_id=user_id)

    # Get random sample
    total_count = queryset.count()
    if total_count == 0:
        return {'status': 'success', 'validated': 0, 'failed': 0}

    sample_size = min(sample_size, total_count)
    document_ids = list(queryset.values_list('id', flat=True))
    sample_ids = random.sample(document_ids, sample_size)

    results = {
        'validated': 0,
        'failed': 0,
        'errors': []
    }

    for doc_id in sample_ids:
        try:
            document = Document.objects.get(id=doc_id)

            # Create temp file for decompression
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name

            # Decompress
            decompressed_size, checksum = decompress_file(
                input_path=document.file.path,
                output_path=temp_path,
                algorithm=document.compression_algorithm
            )

            # Verify checksum
            if checksum == document.original_file_checksum:
                results['validated'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'document_id': str(doc_id),
                    'error': 'Checksum mismatch'
                })
                # Mark document
                document.decompression_failed = True
                document.save(update_fields=['decompression_failed'])

            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

        except Exception as e:
            results['failed'] += 1
            results['errors'].append({
                'document_id': str(doc_id),
                'error': str(e)
            })

    logger.info(
        f"Validation completed. Validated: {results['validated']}, "
        f"Failed: {results['failed']}"
    )

    return results


@shared_task
def recalculate_user_quota(user_id: str):
    """
    Recalculate storage quota for a user.

    Args:
        user_id: UUID of the user

    Returns:
        dict with quota information
    """
    from accounts.models import User

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'error': 'User not found'}

    try:
        # Get or create quota
        quota, created = UserStorageQuota.objects.get_or_create(user=user)

        # Recalculate
        quota.recalculate()

        logger.info(f"Quota recalculated for user {user_id}")

        return {
            'status': 'success',
            'original_used': quota.original_used,
            'compressed_used': quota.compressed_used,
            'compression_savings': quota.compression_savings,
            'document_count': quota.document_count
        }

    except Exception as e:
        logger.error(f"Quota recalculation failed for user {user_id}: {str(e)}")
        return {'error': str(e)}


# Periodic tasks configuration (add to settings or celery beat schedule)
"""
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'cleanup-expired-backups-daily': {
        'task': 'documents.tasks.cleanup_expired_backups_task',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
    'cleanup-temp-files-hourly': {
        'task': 'documents.tasks.cleanup_temp_files_task',
        'schedule': crontab(minute=0),  # Every hour
    },
    'validate-compressions-weekly': {
        'task': 'documents.tasks.validate_compressions_task',
        'schedule': crontab(day_of_week=0, hour=3, minute=0),  # Sunday 3 AM
        'kwargs': {'sample_size': 100}
    },
}
"""
