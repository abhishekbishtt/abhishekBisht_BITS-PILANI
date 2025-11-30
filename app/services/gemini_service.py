from google import genai
from google.genai import types
from PIL import Image
import json
from typing import Dict, Any, List, Optional
import logging

from app.core.config import get_settings
from app.core.constants import EXTRACTION_PROMPT

logger = logging.getLogger(__name__)
settings = get_settings()

class GeminiService:
    """Context-aware Gemini service for medical bill extraction"""
    
    def __init__(self):
        """Initialize Gemini client"""
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    def build_context_prompt(self, page_no: int, total_pages: int, previous_items: List[Dict]) -> str:
        """Build context-aware prompt from previous pages"""
        
        base_prompt = EXTRACTION_PROMPT
        context = f"\n\n📄 PAGE {page_no} of {total_pages}\n"
        
        if previous_items and len(previous_items) > 0:
            # Safely extract item names
            prev_names = []
            for item in previous_items[-10:]:
                if isinstance(item, dict):
                    name = item.get('item_name', '')
                else:
                    name = getattr(item, 'item_name', '')
                if name:
                    prev_names.append(str(name).upper()[:40])
            
            if prev_names:
                context += f"\n🚨 CONTEXT: {len(previous_items)} items seen in previous pages.\n"
                context += "SKIP duplicates or children of these items:\n"
                for name in prev_names[:5]:
                    context += f"  - {name}\n"
        
        return base_prompt + context
    
    def sanitize_response(self, data: Dict) -> Dict:
        """Clean Gemini response - replace None with 0.0"""
        if "bill_items" in data:
            for item in data["bill_items"]:
                # Fix None values
                if item.get("item_amount") is None:
                    item["item_amount"] = 0.0
                if item.get("item_rate") is None:
                    item["item_rate"] = 0.0
                if item.get("item_quantity") is None:
                    item["item_quantity"] = 0.0
        return data
    
    async def analyze_page(
        self, 
        image: Image.Image, 
        page_no: int,
        total_pages: int = 1,
        previous_items: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Analyze single page with context from previous pages"""
        try:
            if previous_items is None:
                previous_items = []
            
            config = types.GenerateContentConfig(
                temperature=settings.GEMINI_TEMPERATURE,
                response_mime_type="application/json",
            )
            
            prompt = self.build_context_prompt(page_no, total_pages, previous_items)
            
            response = await self.client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[prompt, image],
                config=config
            )
            
            # Parse and sanitize
            result_json = json.loads(response.text)
            result_json = self.sanitize_response(result_json)  # Fix None values
            result_json["page_no"] = str(page_no)
            
            item_count = len(result_json.get("bill_items", []))
            result_json["item_count"] = item_count
            
            usage = response.usage_metadata
            token_usage = {
                "total_tokens": usage.total_token_count,
                "input_tokens": usage.prompt_token_count,
                "output_tokens": usage.candidates_token_count
            }
            
            logger.info(f"✓ Page {page_no}/{total_pages}: {item_count} items, {token_usage['total_tokens']} tokens")
            
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
                "page_data": {
                    "page_no": str(page_no),
                    "page_type": "Bill Detail",
                    "fraud_suspected": False,
                    "bill_items": []
                },
                "token_usage": {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0},
                "error": f"JSON parse error: {str(e)}",
                "page_number": page_no
            }
        except Exception as e:
            logger.error(f"✗ Page {page_no} failed: {str(e)}")
            return {
                "success": False,
                "page_data": {
                    "page_no": str(page_no),
                    "page_type": "Bill Detail",
                    "fraud_suspected": False,
                    "bill_items": []
                },
                "token_usage": {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0},
                "error": str(e),
                "page_number": page_no
            }
