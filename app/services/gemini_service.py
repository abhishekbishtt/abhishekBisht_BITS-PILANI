from google import genai
from google.genai import types
from PIL import Image
import json
from typing import Dict, Any, List, Optional

from app.core.config import get_settings
from app.core.constants import EXTRACTION_PROMPT

settings = get_settings()


class GeminiService:
    """Gemini service for medical bill extraction - Full document processing"""
    
    def __init__(self):
        """Initialize Gemini service"""
        pass
    
    def build_full_doc_prompt(self, total_pages: int) -> str:
        """Build prompt for full document extraction"""
        
        base_prompt = EXTRACTION_PROMPT
        context = f"""

## DOCUMENT CONTEXT

This document has {total_pages} page(s). You are seeing ALL pages at once.

## CROSS-PAGE DEDUPLICATION

- If the same item appears on multiple pages, extract it ONLY ONCE
- Use the page with the most complete information
- Skip duplicate/continued entries on other pages

## OUTPUT FORMAT (MULTI-PAGE)

Return ONE JSON object with ALL pages:
{{
  "pages": [
    {{
      "page_no": "1",
      "page_type": "Pharmacy | Bill Detail | Final Bill",
      "bill_items": [
        {{
          "item_name": "string",
          "item_amount": float,
          "item_rate": float,
          "item_quantity": float
        }}
      ]
    }}
  ]
}}
"""
        return base_prompt + context
    
    def sanitize_response(self, data: Dict) -> Dict:
        """Clean Gemini response - replace None with 0.0"""
        if "pages" in data:
            for page in data["pages"]:
                if "bill_items" in page:
                    for item in page["bill_items"]:
                        if item.get("item_amount") is None:
                            item["item_amount"] = 0.0
                        if item.get("item_rate") is None:
                            item["item_rate"] = 0.0
                        if item.get("item_quantity") is None:
                            item["item_quantity"] = 0.0
        return data
    
    async def analyze_full_document(
        self, 
        images: List[Image.Image],
        total_pages: int
    ) -> Dict[str, Any]:
        """
        Send ALL pages in ONE call - Gemini handles context & deduplication
        
        Args:
            images: List of PIL Image objects (all pages)
            total_pages: Total number of pages
            
        Returns:
            Dict with success status, pages data, and token usage
        """
        try:
            config = types.GenerateContentConfig(
                temperature=settings.GEMINI_TEMPERATURE,
                response_mime_type="application/json",
            )
            
            prompt = self.build_full_doc_prompt(total_pages)
            
            # Build contents: [prompt, image1, image2, ...]
            contents = [prompt] + list(images)
            
            # Create client and make request
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            response = await client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=config
            )
            
            # Parse response
            result_json = json.loads(response.text)
            
            # Handle if response is a list instead of object with "pages"
            if isinstance(result_json, list):
                result_json = {"pages": result_json}
            
            # Sanitize
            result_json = self.sanitize_response(result_json)
            
            # Extract token usage
            usage = response.usage_metadata
            token_usage = {
                "total_tokens": usage.total_token_count,
                "input_tokens": usage.prompt_token_count,
                "output_tokens": usage.candidates_token_count
            }
            
            return {
                "success": True,
                "pages": result_json.get("pages", []),
                "token_usage": token_usage
            }
            
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "pages": [],
                "token_usage": {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0},
                "error": f"JSON parse error: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "pages": [],
                "token_usage": {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0},
                "error": str(e)
            }