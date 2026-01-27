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
    """Service for handling document downloads and processing."""
    
    async def download_document(self, url: str) -> Tuple[bytes, str]:
        """
        Download a document from a URL.
        
        Args:
            url: The web address of the document to download
            
        Returns:
            Tuple of (content_bytes, content_type)
            
        Raises:
            Exception: If the download fails
        """
        try:
            logger.info(f"Downloading document from: {url}")
            
            async with aiohttp.ClientSession() as http_session:
                async with http_session.get(url, timeout=settings.TIMEOUT_SECONDS) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to download: HTTP {response.status}")
                    
                    file_content = await response.read()
                    file_type = response.headers.get('Content-Type', '').lower()
                    
                    logger.info(f"Downloaded {len(file_content)} bytes, type: {file_type}")
                    return file_content, file_type
                    
        except Exception as error:
            logger.error(f"Download failed: {str(error)}")
            raise
    
    def process_document(self, content: bytes, content_type: str) -> List[Image.Image]:
        """
        Convert document content into a list of images.
        
        Args:
            content: The raw file data as bytes
            content_type: The MIME type of the file
            
        Returns:
            List of PIL Image objects
        """
        try:
            output_images = []
            
            if 'pdf' in content_type:
                logger.info("Processing as PDF")
                output_images = convert_from_bytes(
                    content,
                    dpi=settings.PDF_DPI,
                    fmt='png'
                )
            elif 'image' in content_type:
                logger.info("Processing as Image")
                image_file = io.BytesIO(content)
                image = Image.open(image_file)
                
                if image.mode not in ('RGB', 'L'):
                    image = image.convert('RGB')
                
                output_images = [image]
            else:
                output_images = self._try_to_open_unknown_file(content, content_type)
            
            page_count = len(output_images)
            logger.info(f"Processed document into {page_count} pages")
            
            if page_count > settings.MAX_PAGES:
                logger.warning(f"Document has {page_count} pages, limiting to {settings.MAX_PAGES}")
                output_images = output_images[:settings.MAX_PAGES]
            
            return output_images
            
        except Exception as error:
            logger.error(f"Document processing failed: {str(error)}")
            raise
    
    def _try_to_open_unknown_file(self, content: bytes, content_type: str) -> List[Image.Image]:
        """
        Try to open a file when we don't know its type.
        
        Args:
            content: The raw file data as bytes
            content_type: The reported content type
            
        Returns:
            List of PIL Image objects
            
        Raises:
            Exception: If the file cannot be opened
        """
        logger.info("Unknown type, trying as Image")
        
        try:
            image_file = io.BytesIO(content)
            image = Image.open(image_file)
            
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            
            return [image]
        except Exception:
            pass
        
        logger.info("Image open failed, trying as PDF")
        
        try:
            pdf_images = convert_from_bytes(
                content,
                dpi=settings.PDF_DPI,
                fmt='png'
            )
            return pdf_images
        except Exception:
            raise Exception(f"Unsupported file type: {content_type}")
