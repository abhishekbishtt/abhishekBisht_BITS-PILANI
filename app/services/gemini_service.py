import google.generativeai as genai
from PIL import Image
import json
from typing import Optional, Dict, Any
import logging

from app.core.config import get_settings
from app.core.constants import EXTRACTION_PROMPT

logger = logging.getLogger(__name__)
settings = get_settings()


class GeminiService:
    """Service for interacting with Google Gemini Vision API"""
    
    def __init__(self):
        """Initialize Gemini service"""
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(model_name=settings.GEMINI_MODEL)
        logger.info(f"✓ Gemini Service initialized: {settings.GEMINI_MODEL}")
    
    def analyze_page(
        self, 
        image: Image.Image, 
        page_no: int
    ) -> Dict[str, Any]:
        """
        Analyze a single page image and extract bill items
        
        Args:
            image: PIL Image object
            page_no: Page number (1-indexed)
            
        Returns:
            Dictionary containing:
                - page_data: Extracted data dict
                - token_usage: Token usage dict
                - error: Error message if failed (None if success)
        """
        try:
            logger.info(f"Analyzing page {page_no}...")
            
            # Generate content
            response = self.model.generate_content(
                [EXTRACTION_PROMPT, image],
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": settings.GEMINI_TEMPERATURE,
                }
            )
            
            # Parse response
            result_json = json.loads(response.text)
            
            # Extract token usage
            usage = response.usage_metadata
            token_usage = {
                "total_tokens": usage.total_token_count,
                "input_tokens": usage.prompt_token_count,
                "output_tokens": usage.candidates_token_count
            }
            
            # Log fraud detection
            if result_json.get("fraud_suspected", False):
                logger.warning(f"⚠️ FRAUD SUSPECTED on page {page_no}")
            
            items_count = len(result_json.get('bill_items', []))
            logger.info(
                f"✓ Page {page_no}: {items_count} items, "
                f"{token_usage['total_tokens']} tokens"
            )
            
            return {
                "page_data": result_json,
                "token_usage": token_usage,
                "error": None
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error on page {page_no}: {e}")
            return {
                "page_data": None,
                "token_usage": {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0},
                "error": f"Invalid JSON response: {str(e)}"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing page {page_no}: {str(e)}")
            return {
                "page_data": None,
                "token_usage": {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0},
                "error": str(e)
            }
