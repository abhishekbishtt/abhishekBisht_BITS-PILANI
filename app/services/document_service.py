from typing import List
from PIL import Image
import logging

from app.utils.file_utils import download_file, detect_file_type
from app.utils.image_utils import convert_pdf_to_images, load_image_from_bytes
from app.models.domain import DocumentContext

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for document download and conversion"""
    
    @staticmethod
    async def prepare_document(document_url: str) -> DocumentContext:
        """
        Download and prepare document for processing
        
        Args:
            document_url: URL to the document
            
        Returns:
            DocumentContext with images ready for processing
        """
        # Download file
        logger.info(f"Downloading document from: {document_url}")
        file_bytes = await download_file(document_url)
        
        # Detect file type
        file_type, extension = detect_file_type(file_bytes)
        logger.info(f"Detected file type: {file_type}{extension}")
        
        # Convert to images
        images: List[Image.Image] = []
        
        if file_type == "pdf":
            images = convert_pdf_to_images(file_bytes)
        else:  # image
            images = [load_image_from_bytes(file_bytes)]
        
        return DocumentContext(
            url=document_url,
            file_type=file_type,
            total_pages=len(images),
            images=images
        )
