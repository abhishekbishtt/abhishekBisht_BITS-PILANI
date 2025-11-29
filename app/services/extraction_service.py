from typing import Dict, Any, List
import logging
import asyncio

from app.services.gemini_service import GeminiService
from app.services.document_service import DocumentService
from app.models.schemas import PageData, TokenUsage, BillItem
from app.core.constants import PageType

logger = logging.getLogger(__name__)

class ExtractionService:
    """Service for extracting data from medical bills"""
    
    def __init__(self):
        self.gemini_service = GeminiService()
        self.document_service = DocumentService()
    
    async def extract_from_url(self, url: str) -> Dict[str, Any]:
        """
        Extract data from document URL.
        """
        try:
            logger.info(f"Starting extraction for: {url}")
            content, content_type = await self.document_service.download_document(url)
            images = self.document_service.process_document(content, content_type)
            logger.info(f"Processing {len(images)} pages")
            
            # Process all pages in parallel
            tasks = [
                self.gemini_service.analyze_page(image, page_idx)
                for page_idx, image in enumerate(images, 1)
            ]
            results = await asyncio.gather(*tasks)
            
            all_pages = []
            total_tokens = {"total": 0, "input": 0, "output": 0}
            
            for page_idx, result in enumerate(results, 1):
                if result.get("success"):
                    page = PageData(**result["page_data"])
                    # Filter zero amounts only
                    page.bill_items = [item for item in page.bill_items if item.item_amount > 0]
                    
                    if page.bill_items:  # Only keep pages with items
                        all_pages.append(page)
                    
                    usage = result["token_usage"]
                    total_tokens["total"] += usage["total_tokens"]
                    total_tokens["input"] += usage["input_tokens"]
                    total_tokens["output"] += usage["output_tokens"]
                    
                    logger.info(f"Page {page_idx}: {len(page.bill_items)} valid items")
                else:
                    logger.warning(f"Page {page_idx} failed: {result.get('error')}")
            
            # Filter Final Bill if detail pages exist
            detail_pages = [p for p in all_pages if p.page_type in [PageType.BILL_DETAIL, PageType.PHARMACY]]
            filtered_pages = detail_pages if detail_pages else all_pages
            
            all_items = []
            for page in filtered_pages:
                all_items.extend(page.bill_items)
            
            response_data = {
                "pagewise_line_items": [
                    {
                        "page_no": page.page_no,
                        "page_type": page.page_type,
                        "bill_items": [item.dict() for item in page.bill_items]
                    }
                    for page in filtered_pages
                ],
                "total_item_count": len(all_items)
            }
            
            logger.info(f"✓ Extraction complete: {len(filtered_pages)} pages, {len(all_items)} items")
            
            return {
                "is_success": True,
                "token_usage": TokenUsage(
                    total_tokens=total_tokens["total"],
                    input_tokens=total_tokens["input"],
                    output_tokens=total_tokens["output"]
                ),
                "data": response_data
            }
            
        except Exception as e:
            logger.error(f"Extraction failed: {str(e)}", exc_info=True)
            return {
                "is_success": False,
                "token_usage": TokenUsage(total_tokens=0, input_tokens=0, output_tokens=0),
                "data": {},
                "error": str(e)
            }
