import io
import tempfile
import os
from typing import List
from PIL import Image
from pdf2image import convert_from_path
from fastapi import HTTPException, status
import logging

from app.core.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()


def preprocess_for_extraction(image: Image.Image) -> Image.Image:
    """Lightweight preprocessing - returns image unchanged for performance."""
    return image


def convert_pdf_to_images(pdf_bytes: bytes) -> List[Image.Image]:
    """
    Convert PDF bytes to list of PIL Images.
    
    Args:
        pdf_bytes: PDF file content as bytes
        
    Returns:
        List of PIL Image objects
        
    Raises:
        HTTPException: If conversion fails
    """
    temp_pdf_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
            temp_pdf.write(pdf_bytes)
            temp_pdf_path = temp_pdf.name
        
        logger.info(f"Converting PDF to images at {settings.PDF_DPI} DPI...")
        images = convert_from_path(
            temp_pdf_path,
            dpi=settings.PDF_DPI,
            fmt='png'
        )
        
        logger.info(f"Converted PDF to {len(images)} page(s)")
        return images
        
    except Exception as e:
        logger.error(f"Error converting PDF to images: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process PDF: {str(e)}"
        )
    finally:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try:
                os.unlink(temp_pdf_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")


def load_image_from_bytes(image_bytes: bytes) -> Image.Image:
    """
    Load PIL Image from bytes.
    
    Args:
        image_bytes: Image file content as bytes
        
    Returns:
        PIL Image object
        
    Raises:
        HTTPException: If loading fails
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        logger.info(f"Loaded image: {image.size[0]}x{image.size[1]}px, mode={image.mode}")
        
        processed_image = preprocess_for_extraction(image)
        return processed_image
        
    except Exception as e:
        logger.error(f"Error loading image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image file: {str(e)}"
        )
