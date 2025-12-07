"""
Compression utilities for document library.

Supports:
- Zstandard (primary for most file types)
- DEFLATE (fallback, gzip wrapper)
- Brotli (best for text files)
"""
import os
import hashlib
import gzip
import brotli
import zstandard as zstd
import magic
from pathlib import Path
from typing import Tuple, Optional
from django.conf import settings


# Compression settings
COMPRESSION_ENABLED = getattr(settings, 'COMPRESSION_ENABLED', True)
COMPRESSION_ALGORITHM = getattr(settings, 'COMPRESSION_ALGORITHM', 'zstd')
COMPRESSION_LEVEL = getattr(settings, 'COMPRESSION_LEVEL', 6)
COMPRESSION_MIN_SIZE = getattr(settings, 'COMPRESSION_MIN_SIZE', 102400)  # 100KB
COMPRESSION_MAX_SIZE = getattr(settings, 'COMPRESSION_MAX_SIZE', 5368709120)  # 5GB

# File types that are already compressed (skip compression)
SKIP_COMPRESSION_TYPES = {'png', 'gif', 'jpg', 'jpeg', 'mp4', 'mp3', 'avi', 'mov'}

# File type to compression algorithm mapping
FILE_TYPE_ALGORITHM_MAP = {
    'txt': 'brotli',
    'csv': 'brotli',
    'log': 'brotli',
    'docx': 'zstd',
    'xlsx': 'zstd',
    'pptx': 'zstd',
    'pdf': 'zstd',
    'zip': 'zstd',  # Try to compress ZIP with zstd wrapper
}


def calculate_checksum(file_path: str) -> str:
    """
    Calculate SHA256 checksum of a file.

    Args:
        file_path: Path to the file

    Returns:
        Hexadecimal checksum string
    """
    sha256_hash = hashlib.sha256()

    with open(file_path, 'rb') as f:
        # Read file in chunks to handle large files
        for chunk in iter(lambda: f.read(8192), b''):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


def get_file_type(file_path: str) -> Tuple[str, str]:
    """
    Detect file type using magic bytes and extension.

    Args:
        file_path: Path to the file

    Returns:
        Tuple of (extension, mime_type)
    """
    # Get extension from filename
    extension = Path(file_path).suffix[1:].lower()  # Remove the dot

    # Detect MIME type using python-magic
    try:
        mime_type = magic.from_file(file_path, mime=True)
    except Exception:
        mime_type = 'application/octet-stream'

    # Map some common MIME types to extensions if extension is missing
    if not extension:
        mime_to_ext = {
            'application/pdf': 'pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
            'text/plain': 'txt',
            'text/csv': 'csv',
            'image/png': 'png',
            'image/jpeg': 'jpg',
            'image/gif': 'gif',
        }
        extension = mime_to_ext.get(mime_type, 'bin')

    return extension, mime_type


def should_compress_file(file_path: str, file_type: str, file_size: int) -> bool:
    """
    Determine if a file should be compressed based on type and size.

    Args:
        file_path: Path to the file
        file_type: File extension/type
        file_size: File size in bytes

    Returns:
        True if file should be compressed, False otherwise
    """
    # Check if compression is globally enabled
    if not COMPRESSION_ENABLED:
        return False

    # Skip if file is too small (overhead not worth it)
    if file_size < COMPRESSION_MIN_SIZE:
        return False

    # Skip if file is too large
    if file_size > COMPRESSION_MAX_SIZE:
        return False

    # Skip already compressed file types
    if file_type.lower() in SKIP_COMPRESSION_TYPES:
        return False

    return True


def select_compression_algorithm(file_type: str) -> str:
    """
    Select the best compression algorithm for a file type.

    Args:
        file_type: File extension/type

    Returns:
        Algorithm name ('zstd', 'deflate', 'brotli', or 'none')
    """
    # Check file type mapping
    algorithm = FILE_TYPE_ALGORITHM_MAP.get(file_type.lower(), COMPRESSION_ALGORITHM)

    return algorithm


def compress_file(
    input_path: str,
    output_path: str,
    algorithm: Optional[str] = None,
    level: Optional[int] = None
) -> Tuple[int, int, float, str]:
    """
    Compress a file using the specified algorithm.

    Args:
        input_path: Path to input file
        output_path: Path to output compressed file
        algorithm: Compression algorithm ('zstd', 'deflate', 'brotli', or None for auto)
        level: Compression level (1-9, None for default)

    Returns:
        Tuple of (original_size, compressed_size, compression_ratio, algorithm_used)
    """
    # Get file info
    original_size = os.path.getsize(input_path)
    file_type, _ = get_file_type(input_path)

    # Auto-select algorithm if not specified
    if algorithm is None:
        algorithm = select_compression_algorithm(file_type)

    # Use default level if not specified
    if level is None:
        level = COMPRESSION_LEVEL

    # Read input file
    with open(input_path, 'rb') as f_in:
        data = f_in.read()

    # Compress based on algorithm
    if algorithm == 'zstd':
        compressed_data = _compress_zstd(data, level)
    elif algorithm == 'brotli':
        compressed_data = _compress_brotli(data, level)
    elif algorithm == 'deflate':
        compressed_data = _compress_deflate(data, level)
    else:
        raise ValueError(f"Unsupported compression algorithm: {algorithm}")

    # Write compressed file
    with open(output_path, 'wb') as f_out:
        f_out.write(compressed_data)

    compressed_size = len(compressed_data)
    compression_ratio = compressed_size / original_size if original_size > 0 else 1.0

    return original_size, compressed_size, compression_ratio, algorithm


def _compress_zstd(data: bytes, level: int) -> bytes:
    """Compress data using Zstandard"""
    compressor = zstd.ZstdCompressor(level=level)
    return compressor.compress(data)


def _compress_brotli(data: bytes, level: int) -> bytes:
    """Compress data using Brotli"""
    return brotli.compress(data, quality=level)


def _compress_deflate(data: bytes, level: int) -> bytes:
    """Compress data using DEFLATE (gzip)"""
    return gzip.compress(data, compresslevel=level)


def decompress_file(
    input_path: str,
    output_path: str,
    algorithm: str
) -> Tuple[int, str]:
    """
    Decompress a file using the specified algorithm.

    Args:
        input_path: Path to compressed file
        output_path: Path to output decompressed file
        algorithm: Compression algorithm used ('zstd', 'deflate', 'brotli')

    Returns:
        Tuple of (decompressed_size, checksum)

    Raises:
        ValueError: If algorithm is unsupported
        Exception: If decompression fails
    """
    # Read compressed file
    with open(input_path, 'rb') as f_in:
        compressed_data = f_in.read()

    # Decompress based on algorithm
    try:
        if algorithm == 'zstd':
            decompressed_data = _decompress_zstd(compressed_data)
        elif algorithm == 'brotli':
            decompressed_data = _decompress_brotli(compressed_data)
        elif algorithm == 'deflate':
            decompressed_data = _decompress_deflate(compressed_data)
        elif algorithm == 'none':
            # No compression, just copy
            decompressed_data = compressed_data
        else:
            raise ValueError(f"Unsupported decompression algorithm: {algorithm}")
    except Exception as e:
        raise Exception(f"Decompression failed: {str(e)}")

    # Write decompressed file
    with open(output_path, 'wb') as f_out:
        f_out.write(decompressed_data)

    # Calculate checksum of decompressed file
    checksum = calculate_checksum(output_path)

    return len(decompressed_data), checksum


def _decompress_zstd(data: bytes) -> bytes:
    """Decompress data using Zstandard"""
    decompressor = zstd.ZstdDecompressor()
    return decompressor.decompress(data)


def _decompress_brotli(data: bytes) -> bytes:
    """Decompress data using Brotli"""
    return brotli.decompress(data)


def _decompress_deflate(data: bytes) -> bytes:
    """Decompress data using DEFLATE (gzip)"""
    return gzip.decompress(data)


def verify_compression(
    original_checksum: str,
    decompressed_checksum: str
) -> bool:
    """
    Verify that decompression was successful by comparing checksums.

    Args:
        original_checksum: SHA256 checksum of original file
        decompressed_checksum: SHA256 checksum of decompressed file

    Returns:
        True if checksums match, False otherwise
    """
    return original_checksum == decompressed_checksum


def analyze_compression_potential(file_path: str) -> dict:
    """
    Analyze a file to estimate compression potential without actually compressing.

    Args:
        file_path: Path to the file

    Returns:
        Dictionary with analysis results
    """
    file_size = os.path.getsize(file_path)
    file_type, mime_type = get_file_type(file_path)

    # Estimate compression ratio based on file type
    estimated_ratios = {
        'txt': 0.3,  # 70% compression
        'csv': 0.3,
        'log': 0.2,
        'docx': 0.6,  # Already compressed, but zstd can help
        'xlsx': 0.6,
        'pptx': 0.6,
        'pdf': 0.7,  # PDFs are already compressed
        'zip': 0.9,  # Very little gain
        'png': 1.0,  # No gain
        'jpg': 1.0,
        'jpeg': 1.0,
        'gif': 1.0,
    }

    estimated_ratio = estimated_ratios.get(file_type.lower(), 0.5)
    estimated_compressed_size = int(file_size * estimated_ratio)
    estimated_savings = file_size - estimated_compressed_size

    return {
        'file_type': file_type,
        'mime_type': mime_type,
        'original_size': file_size,
        'estimated_compressed_size': estimated_compressed_size,
        'estimated_savings': estimated_savings,
        'estimated_ratio': estimated_ratio,
        'should_compress': should_compress_file(file_path, file_type, file_size),
        'recommended_algorithm': select_compression_algorithm(file_type),
    }
