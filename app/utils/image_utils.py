import io
import tempfile
import os
from typing import List
from PIL import Image, ImageEnhance
from pdf2image import convert_from_path
from fastapi import HTTPException, status
import logging
import cv2
import numpy as np


from app.core.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()



def preprocess_for_extraction(image: Image.Image) -> Image.Image:
    """
    Apply medical-bill-specific preprocessing for optimal extraction accuracy
    
    Args:
        image: Raw PIL Image
        
    Returns:
        Enhanced PIL Image
    """
    try:
        # Convert to numpy for OpenCV operations
        img_array = np.array(image)
        
        # 1. Denoise (removes scanner artifacts and compression noise)
        denoised = cv2.fastNlMeansDenoisingColored(img_array, None, 10, 10, 7, 21)
        
        # 2. Convert back to PIL for enhancement
        pil_img = Image.fromarray(denoised)
        
        # 3. Increase contrast (makes text sharper and more defined)
        enhancer = ImageEnhance.Contrast(pil_img)
        enhanced = enhancer.enhance(1.5)  # 50% contrast boost
        
        # 4. Enhance sharpness (improves character edge definition)
        sharpener = ImageEnhance.Sharpness(enhanced)
        sharpened = sharpener.enhance(2.0)  # Double sharpness
        
        logger.info(f"✓ Preprocessed image: enhanced contrast & sharpness")
        return sharpened
        
    except Exception as e:
        logger.warning(f"Preprocessing failed: {str(e)}, returning original")
        return image  # Return original if preprocessing fails



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
        
        # Preprocess each image for optimal extraction
        preprocessed_images = []
        for idx, img in enumerate(images, 1):
            processed = preprocess_for_extraction(img)
            preprocessed_images.append(processed)
            logger.info(f"✓ Preprocessed page {idx}/{len(images)}")
        
        logger.info(f"✓ Converted PDF to {len(preprocessed_images)} preprocessed page(s)")
        return preprocessed_images
        
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
