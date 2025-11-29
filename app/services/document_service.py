from pdf2image import convert_from_bytes
from PIL import Image
import aiohttp
from typing import List
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentService:
    """Service for handling document downloads and PDF conversion"""
    
    async def download_document(self, url: str) -> bytes:
        """
        Download document from URL.
        
        Args:
            url: Document URL
            
        Returns:
            Document content as bytes
            
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
                    logger.info(f"Downloaded {len(content)} bytes")
                    return content
                    
        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            raise
    
    def convert_pdf_to_images(self, pdf_bytes: bytes) -> List[Image.Image]:
        """
        Convert PDF bytes to list of PIL Images.
        
        Args:
            pdf_bytes: PDF file content as bytes
            
        Returns:
            List of PIL Image objects (one per page)
            
        Raises:
            Exception: If conversion fails
        """
        try:
            logger.info("Converting PDF to images...")
            images = convert_from_bytes(
                pdf_bytes,
                dpi=settings.PDF_DPI,
                fmt='png'
            )
            logger.info(f"Converted PDF to {len(images)} pages")
            
            if len(images) > settings.MAX_PAGES:
                logger.warning(f"PDF has {len(images)} pages, limiting to {settings.MAX_PAGES}")
                images = images[:settings.MAX_PAGES]
            
            return images
            
        except Exception as e:
            logger.error(f"PDF conversion failed: {str(e)}")
            raise
