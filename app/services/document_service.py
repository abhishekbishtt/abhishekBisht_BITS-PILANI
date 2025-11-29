from pdf2image import convert_from_bytes
from PIL import Image
import aiohttp
from typing import List, Tuple
import io
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentService:
    """Service for handling document downloads and processing"""
    
    async def download_document(self, url: str) -> Tuple[bytes, str]:
        """
        Download document from URL.
        
        Args:
            url: Document URL
            
        Returns:
            Tuple of (content_bytes, content_type)
            
        Raises:
            Exception: If download fails
        """
        try:
            logger.info(f"Downloading document from: {url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=settings.TIMEOUT_SECONDS) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to download: HTTP {response.status}")
                    
                    content = await response.read()
                    content_type = response.headers.get('Content-Type', '').lower()
                    logger.info(f"Downloaded {len(content)} bytes, type: {content_type}")
                    return content, content_type
                    
        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            raise
    
    def process_document(self, content: bytes, content_type: str) -> List[Image.Image]:
        """
        Process document content into list of images.
        
        Args:
            content: File content bytes
            content_type: MIME type of the file
            
        Returns:
            List of PIL Image objects
        """
        try:
            images = []
            
            if 'pdf' in content_type:
                logger.info("Processing as PDF")
                images = convert_from_bytes(
                    content,
                    dpi=settings.PDF_DPI,
                    fmt='png'
                )
            elif 'image' in content_type:
                logger.info("Processing as Image")
                image = Image.open(io.BytesIO(content))
                # Convert to RGB to handle RGBA/P modes if necessary
                if image.mode not in ('RGB', 'L'):
                    image = image.convert('RGB')
                images = [image]
            else:
                # Fallback: try to detect by signature or just try opening as image
                try:
                    logger.info("Unknown type, trying as Image")
                    image = Image.open(io.BytesIO(content))
                    if image.mode not in ('RGB', 'L'):
                        image = image.convert('RGB')
                    images = [image]
                except Exception:
                    # Try as PDF if image fails
                    logger.info("Image open failed, trying as PDF")
                    try:
                        images = convert_from_bytes(content, dpi=settings.PDF_DPI, fmt='png')
                    except Exception:
                        raise Exception(f"Unsupported file type: {content_type}")

            logger.info(f"Processed document into {len(images)} pages")
            
            if len(images) > settings.MAX_PAGES:
                logger.warning(f"Document has {len(images)} pages, limiting to {settings.MAX_PAGES}")
                images = images[:settings.MAX_PAGES]
            
            return images
            
        except Exception as e:
            logger.error(f"Document processing failed: {str(e)}")
            raise
