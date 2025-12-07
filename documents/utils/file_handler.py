"""
File handling utilities for document uploads and validation.
"""
import os
import magic
from pathlib import Path
from typing import Tuple, Optional
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile


# Allowed file extensions
ALLOWED_EXTENSIONS = {
    'pdf', 'docx', 'xlsx', 'pptx', 'txt', 'csv',
    'png', 'jpg', 'jpeg', 'gif', 'zip'
}

# MIME type validation mapping
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain',
    'text/csv',
    'image/png',
    'image/jpeg',
    'image/gif',
    'application/zip',
    'application/x-zip-compressed',
}

# Maximum file sizes per type (in bytes)
MAX_FILE_SIZES = {
    'pdf': 100 * 1024 * 1024,  # 100MB
    'docx': 50 * 1024 * 1024,  # 50MB
    'xlsx': 50 * 1024 * 1024,  # 50MB
    'pptx': 100 * 1024 * 1024,  # 100MB
    'txt': 10 * 1024 * 1024,  # 10MB
    'csv': 50 * 1024 * 1024,  # 50MB
    'png': 25 * 1024 * 1024,  # 25MB
    'jpg': 25 * 1024 * 1024,  # 25MB
    'jpeg': 25 * 1024 * 1024,  # 25MB
    'gif': 25 * 1024 * 1024,  # 25MB
    'zip': 500 * 1024 * 1024,  # 500MB
}

DEFAULT_MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB default


def get_file_extension(filename: str) -> str:
    """
    Extract file extension from filename.

    Args:
        filename: The filename

    Returns:
        Lowercase file extension without dot
    """
    return Path(filename).suffix[1:].lower()


def validate_file_extension(filename: str) -> str:
    """
    Validate file extension.

    Args:
        filename: The filename

    Returns:
        Validated extension

    Raises:
        ValidationError: If extension is not allowed
    """
    extension = get_file_extension(filename)

    if not extension:
        raise ValidationError('File has no extension')

    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f'File type ".{extension}" is not allowed. '
            f'Allowed types: {", ".join(sorted(ALLOWED_EXTENSIONS))}'
        )

    return extension


def validate_file_size(file_size: int, file_extension: str) -> None:
    """
    Validate file size against limits.

    Args:
        file_size: Size in bytes
        file_extension: File extension

    Raises:
        ValidationError: If file is too large
    """
    max_size = MAX_FILE_SIZES.get(file_extension, DEFAULT_MAX_FILE_SIZE)

    if file_size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        raise ValidationError(
            f'File size ({file_size / (1024 * 1024):.2f}MB) exceeds '
            f'maximum allowed size ({max_size_mb:.0f}MB) for .{file_extension} files'
        )


def validate_mime_type(file_path: str) -> str:
    """
    Validate file MIME type using magic bytes.

    Args:
        file_path: Path to the file

    Returns:
        Detected MIME type

    Raises:
        ValidationError: If MIME type is not allowed or detection fails
    """
    try:
        mime_type = magic.from_file(file_path, mime=True)
    except Exception as e:
        raise ValidationError(f'Failed to detect file type: {str(e)}')

    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValidationError(
            f'File type "{mime_type}" is not allowed'
        )

    return mime_type


def validate_file(uploaded_file: UploadedFile, temp_path: Optional[str] = None) -> Tuple[str, str, int]:
    """
    Comprehensive file validation.

    Args:
        uploaded_file: Django UploadedFile object
        temp_path: Optional path to temporarily saved file for MIME type validation

    Returns:
        Tuple of (extension, mime_type, file_size)

    Raises:
        ValidationError: If any validation fails
    """
    # Validate extension
    extension = validate_file_extension(uploaded_file.name)

    # Validate size
    file_size = uploaded_file.size
    validate_file_size(file_size, extension)

    # Validate MIME type if temp_path is provided
    mime_type = None
    if temp_path and os.path.exists(temp_path):
        mime_type = validate_mime_type(temp_path)

    # Basic security checks
    # Check for null bytes in filename
    if '\x00' in uploaded_file.name:
        raise ValidationError('Invalid filename: contains null bytes')

    # Check for path traversal attempts
    if '..' in uploaded_file.name or '/' in uploaded_file.name or '\\' in uploaded_file.name:
        raise ValidationError('Invalid filename: contains path components')

    return extension, mime_type or 'application/octet-stream', file_size


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent security issues.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove path components
    filename = os.path.basename(filename)

    # Remove or replace dangerous characters
    dangerous_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*', '\x00']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')

    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')

    # Ensure filename is not empty
    if not filename:
        filename = 'unnamed_file'

    # Limit length (keep extension)
    max_length = 255
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        name = name[:max_length - len(ext) - 1]
        filename = name + ext

    return filename


def handle_uploaded_file(uploaded_file: UploadedFile, destination_path: str) -> Tuple[str, str, int]:
    """
    Handle uploaded file: validate and save to destination.

    Args:
        uploaded_file: Django UploadedFile object
        destination_path: Path where file should be saved

    Returns:
        Tuple of (file_type, mime_type, file_size)

    Raises:
        ValidationError: If validation fails
    """
    # Ensure destination directory exists
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)

    # Save file temporarily for validation
    temp_path = destination_path + '.tmp'

    try:
        # Write uploaded file to temp location
        with open(temp_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        # Validate file
        file_type, mime_type, file_size = validate_file(uploaded_file, temp_path)

        # If validation passes, move to final destination
        os.rename(temp_path, destination_path)

        return file_type, mime_type, file_size

    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

    finally:
        # Ensure temp file is removed
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def get_human_readable_size(size_bytes: int) -> str:
    """
    Convert bytes to human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"
