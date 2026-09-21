"""
Secure Document Storage, Path Traversal Defense, and Integrity Verification.
"""

import os
import re
import hashlib
from typing import Tuple
from fastapi import HTTPException, status

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
}

# Maximum upload size: 25 MB
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes an untrusted filename to prevent directory traversal,
    null byte injection, or command execution characters.
    """
    if not filename:
        return "unnamed_document.pdf"

    # Remove path separators and null bytes
    cleaned = filename.replace("\x00", "").replace("/", "").replace("\\", "").strip()
    
    # Retain basename only
    cleaned = os.path.basename(cleaned)

    # Extract base and ext
    base, ext = os.path.splitext(cleaned)
    ext_lower = ext.lower()

    if ext_lower not in ALLOWED_EXTENSIONS:
        ext_lower = ".pdf"

    # Clean base name
    base_clean = re.sub(r"[^A-Za-z0-9_\-\.]", "_", base)[:64]
    if not base_clean:
        base_clean = "medical_doc"

    return f"{base_clean}{ext_lower}"


def validate_storage_path(base_dir: str, target_path: str) -> str:
    """
    Verifies that the target path does not escape the designated base directory
    using strict canonical path resolution. Raises HTTPException(400) if violation detected.
    """
    real_base = os.path.realpath(base_dir)
    real_target = os.path.realpath(target_path)

    if not real_target.startswith(real_base):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security violation: Path traversal attempt detected."
        )

    return real_target


def validate_file_upload(filename: str, file_bytes: bytes, mime_type: str = "application/pdf") -> Tuple[str, str]:
    """
    Validates file extension, size, MIME type, and computes integrity checksum.
    Returns (sanitized_filename, sha256_checksum).
    """
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Uploaded file exceeds maximum limit of {MAX_FILE_SIZE_BYTES // (1024*1024)}MB."
        )

    sanitized = sanitize_filename(filename)
    ext = os.path.splitext(sanitized)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '{ext}' is not permitted. Permitted: {list(ALLOWED_EXTENSIONS)}"
        )

    # Validate MIME type
    if mime_type and mime_type.lower() not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MIME type '{mime_type}' is not permitted."
        )

    # Magic byte check for PDF or Image
    if ext == ".pdf" and not file_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File signature does not match valid PDF format."
        )

    sha256 = hashlib.sha256(file_bytes).hexdigest()
    return sanitized, sha256
