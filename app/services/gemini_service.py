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
        """Initialize Gemini client"""
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    async def analyze_page(self, image: Image.Image, page_no: int) -> Dict[str, Any]:
        """
        Analyze a single page image and extract bill data.
        
        Args:
            image: PIL Image of the bill page
            page_no: Page number
            
        Returns:
            Dictionary with extraction results and token usage
        """
        try:
            # Configure generation
            config = types.GenerateContentConfig(
                temperature=settings.GEMINI_TEMPERATURE,
                response_mime_type="application/json",
            )
            
            # Create prompt with page number
            prompt = f"{EXTRACTION_PROMPT}\n\nThis is page {page_no} of the bill."
            
            # Call Gemini API
            response = await self.client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[prompt, image],
                config=config
            )
            
            # Parse response
            result_json = json.loads(response.text)
            
            # Force override page number
            result_json["page_no"] = str(page_no)
            
            # Count items
            item_count = len(result_json.get("bill_items", []))
            result_json["item_count"] = item_count
            
            # Get token usage
            usage = response.usage_metadata
            token_usage = {
                "total_tokens": usage.total_token_count,
                "input_tokens": usage.prompt_token_count,
                "output_tokens": usage.candidates_token_count
            }
            
            logger.info(f"✓ Page {page_no}: {item_count} items, {token_usage['total_tokens']} tokens")
            
            return {
                "success": True,
                "page_data": result_json,
                "token_usage": token_usage,
                "page_number": page_no
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"✗ Page {page_no} JSON parse error: {str(e)}")
            return {
                "success": False,
                "page_data": None,
                "token_usage": {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0},
                "error": f"JSON parse error: {str(e)}",
                "page_number": page_no
            }
        except Exception as e:
            logger.error(f"✗ Page {page_no} failed: {str(e)}")
            return {
                "success": False,
                "page_data": None,
                "token_usage": {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0},
                "error": str(e),
                "page_number": page_no
            }
