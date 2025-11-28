import aiohttp
import tempfile
import os
from typing import Tuple
from fastapi import HTTPException, status
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def download_file(url: str) -> bytes:
    """
    Download file from URL asynchronously
    
    Args:
        url: URL to download from
        
    Returns:
        File content as bytes
        
    Raises:
        HTTPException: If download fails
    """
    try:
        timeout = aiohttp.ClientTimeout(total=settings.TIMEOUT_SECONDS)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to download document. Status: {response.status}"
                    )
                
                content = await response.read()
                
                # Check file size
                size_mb = len(content) / (1024 * 1024)
                if size_mb > settings.MAX_FILE_SIZE_MB:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File size ({size_mb:.2f}MB) exceeds limit ({settings.MAX_FILE_SIZE_MB}MB)"
                    )
                
                logger.info(f"Downloaded file: {size_mb:.2f}MB")
                return content
                
    except aiohttp.ClientError as e:
        logger.error(f"Network error downloading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Network error: {str(e)}"
        )


def is_pdf(file_bytes: bytes) -> bool:
    """Check if file is a PDF"""
    return file_bytes[:4] == b'%PDF'


def is_image(file_bytes: bytes) -> bool:
    """Check if file is an image (PNG, JPG, JPEG)"""
    # PNG signature
    if file_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return True
    # JPEG signature
    if file_bytes[:2] == b'\xff\xd8':
        return True
    return False


def detect_file_type(file_bytes: bytes) -> Tuple[str, str]:
    """
    Detect file type from bytes
    
    Returns:
        Tuple of (file_type, extension)
    """
    if is_pdf(file_bytes):
        return "pdf", ".pdf"
    elif is_image(file_bytes):
        if file_bytes[:8] == b'\x89PNG\r\n\x1a\n':
            return "image", ".png"
        else:
            return "image", ".jpg"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Only PDF and images (PNG, JPG) are supported."
        )
