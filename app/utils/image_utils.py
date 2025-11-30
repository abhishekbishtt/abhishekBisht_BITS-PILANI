import io
import tempfile
import os
from typing import List
from PIL import Image
from pdf2image import convert_from_path
from fastapi import HTTPException, status
import logging
# import cv2
# import numpy as np


from app.core.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()



def preprocess_for_extraction(image: Image.Image) -> Image.Image:
    """A lightweight no-op preprocessing function.

    The original implementation performed several OpenCV‑based enhancements that
    significantly increased processing time. For faster response we now simply
    return the original image unchanged while keeping the function signature for
    compatibility.
    """
    # No heavy processing – just return the image as‑is.
    logger.info("✓ Skipping heavy image preprocessing for speed optimization")
    return image



def convert_pdf_to_images(pdf_bytes: bytes) -> List[Image.Image]:
    """
    Convert PDF bytes to list of PIL Images with preprocessing
    
    Args:
        pdf_bytes: PDF file content as bytes
        
    Returns:
        List of preprocessed PIL Image objects
        
    Raises:
        HTTPException: If conversion fails
    """
    temp_pdf_path = None
    try:
        # Save PDF bytes to temp file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
            temp_pdf.write(pdf_bytes)
            temp_pdf_path = temp_pdf.name
        
        # Convert PDF to images
        logger.info(f"Converting PDF to images at {settings.PDF_DPI} DPI...")
        images = convert_from_path(
            temp_pdf_path,
            dpi=settings.PDF_DPI,
            fmt='png'
        )
        
        # Return raw images without additional preprocessing for speed
        logger.info(f"✓ Converted PDF to {len(images)} page(s) without extra preprocessing")
        return images
        
    except Exception as e:
        logger.error(f"Error converting PDF to images: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process PDF: {str(e)}"
        )
    finally:
        # Clean up temp file
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try:
                os.unlink(temp_pdf_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")



def load_image_from_bytes(image_bytes: bytes) -> Image.Image:
    """
    Load PIL Image from bytes with preprocessing
    
    Args:
        image_bytes: Image file content as bytes
        
    Returns:
        Preprocessed PIL Image object
        
    Raises:
        HTTPException: If loading fails
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        logger.info(f"✓ Loaded image: {image.size[0]}x{image.size[1]}px, mode={image.mode}")
        
        # Apply preprocessing
        processed_image = preprocess_for_extraction(image)
        logger.info("✓ Preprocessed loaded image")
        
        return processed_image
        
    except Exception as e:
        logger.error(f"Error loading image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image file: {str(e)}"
        )
