"""
Session management for vault operations.

This module handles storing and retrieving the decrypted DEK in Django sessions,
managing vault lock/unlock state, and enforcing session timeouts.
"""

import base64
from typing import Optional
from datetime import datetime
from django.utils import timezone


class VaultSessionManager:
    """
    Manages vault unlock sessions and DEK storage in Django sessions.

    The decrypted DEK is stored in the session only when the vault is unlocked,
    providing a balance between security and usability.
    """

    # Session keys for storing vault data
    SESSION_KEY = '_vault_dek'
    UNLOCK_TIME_KEY = '_vault_unlock_time'
    LAST_ACTIVITY_KEY = '_vault_last_activity'

    @staticmethod
    def store_dek_in_session(request, dek: bytes, timeout_minutes: int = 15):
        """
        Store decrypted DEK in session (base64 encoded).

        Args:
            request: Django HttpRequest object
            dek: Decrypted Data Encryption Key
            timeout_minutes: Session timeout in minutes (default: 15)
        """
        # Store DEK as base64 string
        request.session[VaultSessionManager.SESSION_KEY] = base64.b64encode(dek).decode('ascii')

        # Store timestamps
        now = timezone.now()
        request.session[VaultSessionManager.UNLOCK_TIME_KEY] = now.isoformat()
        request.session[VaultSessionManager.LAST_ACTIVITY_KEY] = now.isoformat()

        # Set session expiry (in seconds)
        request.session.set_expiry(timeout_minutes * 60)

    @staticmethod
    def get_dek_from_session(request) -> Optional[bytes]:
        """
        Retrieve DEK from session.

        Args:
            request: Django HttpRequest object

        Returns:
            Decrypted DEK bytes if vault is unlocked, None otherwise
        """
        dek_b64 = request.session.get(VaultSessionManager.SESSION_KEY)
        if dek_b64:
            # Update last activity timestamp
            request.session[VaultSessionManager.LAST_ACTIVITY_KEY] = timezone.now().isoformat()
            return base64.b64decode(dek_b64)
        return None

    @staticmethod
    def is_vault_unlocked(request) -> bool:
        """
        Check if vault is currently unlocked.

        Args:
            request: Django HttpRequest object

        Returns:
            True if vault is unlocked, False otherwise
        """
        return VaultSessionManager.SESSION_KEY in request.session

    @staticmethod
    def lock_vault(request):
        """
        Lock vault by clearing session data.

        Args:
            request: Django HttpRequest object
        """
        # Remove vault session keys
        keys_to_remove = [
            VaultSessionManager.SESSION_KEY,
            VaultSessionManager.UNLOCK_TIME_KEY,
            VaultSessionManager.LAST_ACTIVITY_KEY
        ]

        for key in keys_to_remove:
            if key in request.session:
                del request.session[key]

        # Force session save
        request.session.modified = True

    @staticmethod
    def check_timeout(request, timeout_minutes: int = 15) -> bool:
        """
        Check if vault session has timed out.

        Args:
            request: Django HttpRequest object
            timeout_minutes: Timeout duration in minutes

        Returns:
            True if session has timed out, False otherwise
        """
        last_activity_str = request.session.get(VaultSessionManager.LAST_ACTIVITY_KEY)

        if not last_activity_str:
            return True

        try:
            last_activity = datetime.fromisoformat(last_activity_str)
            # Make timezone-aware if needed
            if timezone.is_naive(last_activity):
                last_activity = timezone.make_aware(last_activity)

            elapsed = timezone.now() - last_activity
            return elapsed.total_seconds() > (timeout_minutes * 60)
        except (ValueError, TypeError):
            # If there's any error parsing the timestamp, consider it timed out
            return True

    @staticmethod
    def update_activity(request):
        """
        Update last activity timestamp.

        Args:
            request: Django HttpRequest object
        """
        if VaultSessionManager.is_vault_unlocked(request):
            request.session[VaultSessionManager.LAST_ACTIVITY_KEY] = timezone.now().isoformat()
            request.session.modified = True

    @staticmethod
    def get_unlock_time(request) -> Optional[datetime]:
        """
        Get the time when vault was unlocked.

        Args:
            request: Django HttpRequest object

        Returns:
            Datetime when vault was unlocked, or None if not unlocked
        """
        unlock_time_str = request.session.get(VaultSessionManager.UNLOCK_TIME_KEY)
        if unlock_time_str:
            try:
                unlock_time = datetime.fromisoformat(unlock_time_str)
                if timezone.is_naive(unlock_time):
                    unlock_time = timezone.make_aware(unlock_time)
                return unlock_time
            except (ValueError, TypeError):
                return None
        return None

    @staticmethod
    def get_time_remaining(request, timeout_minutes: int = 15) -> Optional[int]:
        """
        Get remaining time before timeout in seconds.

        Args:
            request: Django HttpRequest object
            timeout_minutes: Timeout duration in minutes

        Returns:
            Remaining seconds, or None if not unlocked
        """
        last_activity_str = request.session.get(VaultSessionManager.LAST_ACTIVITY_KEY)

        if not last_activity_str:
            return None

        try:
            last_activity = datetime.fromisoformat(last_activity_str)
            if timezone.is_naive(last_activity):
                last_activity = timezone.make_aware(last_activity)

            timeout_seconds = timeout_minutes * 60
            elapsed = (timezone.now() - last_activity).total_seconds()
            remaining = timeout_seconds - elapsed

            return max(0, int(remaining))
        except (ValueError, TypeError):
            return None
