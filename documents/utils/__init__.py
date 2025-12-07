"""
Document Library Utilities
"""
from .compression import (
    compress_file,
    decompress_file,
    calculate_checksum,
    get_file_type,
    should_compress_file,
    select_compression_algorithm,
)
from .file_handler import (
    handle_uploaded_file,
    validate_file,
    get_file_extension,
)

__all__ = [
    'compress_file',
    'decompress_file',
    'calculate_checksum',
    'get_file_type',
    'should_compress_file',
    'select_compression_algorithm',
    'handle_uploaded_file',
    'validate_file',
    'get_file_extension',
]
