from google import genai
from google.genai import types
from PIL import Image
import json
from typing import Dict, Any
import logging

from app.core.config import get_settings
from app.core.constants import EXTRACTION_PROMPT

logger = logging.getLogger(__name__)
settings = get_settings()


class GeminiService:
    """Service for interacting with Google Gemini Vision API"""
    
    def __init__(self):
        """Initialize Gemini service"""
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = "gemini-2.0-flash-001"
        logger.info(f"✓ Gemini Service initialized: {self.model}")
    
    def analyze_page(
        self, 
        image: Image.Image, 
        page_no: int
    ) -> Dict[str, Any]:
        """
        Analyze a single page image and extract bill items
        """
        try:
            logger.info(f"Analyzing page {page_no}...")
            
            # Add page number to prompt
            prompt_with_page = f"{EXTRACTION_PROMPT}\n\nIMPORTANT: This is page {page_no}. Set page_no field to \"{page_no}\" in your response."
            
            # Generate content
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt_with_page, image],  # CHANGED: use prompt with page number
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=settings.GEMINI_TEMPERATURE,
                )
            )
            
            # Parse response
            result_json = json.loads(response.text)
            
            # FORCE CORRECT PAGE NUMBER (override Gemini's response)
            result_json["page_no"] = str(page_no)  # ADD THIS LINE
            
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
                "error": None,
                "page_number": page_no
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error on page {page_no}: {e}")
            return {
                "page_data": None,
                "token_usage": {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0},
                "error": f"Invalid JSON response: {str(e)}",
                "page_number": page_no
            }
            
        except Exception as e:
            logger.error(f"Error analyzing page {page_no}: {str(e)}")
            return {
                "page_data": None,
                "token_usage": {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0},
                "error": str(e),
                "page_number": page_no
            }
