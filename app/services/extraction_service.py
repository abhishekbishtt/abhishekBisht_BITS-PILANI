from typing import Dict, Any, List
import logging
import asyncio

from app.services.gemini_service import GeminiService
from app.services.document_service import DocumentService
from app.models.schemas import PageData, TokenUsage
from app.core.constants import PageType

logger = logging.getLogger(__name__)


class ExtractionService:
    """Service for extracting data from medical bills"""
    
    def __init__(self):
        """Initialize services"""
        self.gemini_service = GeminiService()
        self.document_service = DocumentService()
    
    async def extract_from_url(self, url: str) -> Dict[str, Any]:
        """
        Extract data from document URL.
        
        Args:
            url: URL of the PDF document
            
        Returns:
            Dictionary with extraction results and metadata
        """
        try:
            # Download document
            logger.info(f"Starting extraction for: {url}")
            content, content_type = await self.document_service.download_document(url)
            
            # Convert to images
            images = self.document_service.process_document(content, content_type)
            logger.info(f"Processing {len(images)} pages")
            
            # Process all pages in parallel
            all_pages = []
            total_tokens = {"total": 0, "input": 0, "output": 0}
            
            # Create tasks for all pages
            tasks = [
                self.gemini_service.analyze_page(image, page_idx)
                for page_idx, image in enumerate(images, 1)
            ]
            
            # Process all pages in parallel
            logger.info(f"Processing {len(images)} pages in parallel")
            results = await asyncio.gather(*tasks)
            
            # Collect results
            for page_idx, result in enumerate(results, 1):
                if result.get("success"):
                    page = PageData(**result["page_data"])
                    all_pages.append(page)
                    
                    # Accumulate tokens
                    usage = result["token_usage"]
                    total_tokens["total"] += usage["total_tokens"]
                    total_tokens["input"] += usage["input_tokens"]
                    total_tokens["output"] += usage["output_tokens"]
                else:
                    logger.warning(f"Page {page_idx} extraction failed: {result.get('error')}")

            
            # Double Counting Prevention Logic
            # If we have detailed pages (Bill Detail or Pharmacy), ignore Final Bill pages
            has_details = any(p.page_type in [PageType.BILL_DETAIL, PageType.PHARMACY] for p in all_pages)
            
            filtered_pages = []
            if has_details:
                logger.info("Detailed pages detected. Filtering out 'Final Bill' pages to prevent double counting.")
                for page in all_pages:
                    if page.page_type == PageType.FINAL_BILL:
                        logger.info(f"Skipping Page {page.page_no} (Final Bill) from totals")
                        # We still keep the page in the response, but we might want to exclude its items from the total count
                        # The requirement says "Final Total will be sum (of all individual line items in the bills) without double-counting."
                        # So we should probably exclude the items from the final aggregation list if we want to be strict,
                        # OR just rely on the fact that the user wants the "pagewise_line_items" to be correct.
                        # However, the "total_item_count" should definitely not double count.
                        # Let's keep the page in "pagewise_line_items" but exclude from "total_item_count" calculation?
                        # Wait, the prompt says "extract the line item details... and also provide... Final Total".
                        # The API response has "pagewise_line_items" and "total_item_count".
                        # It doesn't explicitly have a "Final Total" field in the response schema provided in the user prompt,
                        # but the prompt text says "provide... Final Total".
                        # Looking at the response schema:
                        # "data": { "pagewise_line_items": [...], "total_item_count": ... }
                        # It seems the "Final Total" is implied to be calculated from the items? 
                        # Or maybe I should filter them out from the response entirely?
                        # "Final Total will be sum (of all individual line items in the bills) without double-counting."
                        # If I include Final Bill items in the response, the consumer might sum them up and double count.
                        # Safest bet: If details exist, REMOVE Final Bill items from the output entirely or mark them?
                        # The schema doesn't have a "ignored" flag.
                        # Let's EXCLUDE Final Bill pages from the output if details exist.
                        pass 
                    else:
                        filtered_pages.append(page)
            else:
                # If only Final Bill pages exist (e.g. summary only bill), keep them
                filtered_pages = all_pages

            # Aggregate results from FILTERED pages
            all_items = []
            for page in filtered_pages:
                all_items.extend(page.bill_items)
            
            # Construct response with FILTERED pages
            # Note: We are returning only the pages that contribute to the total.
            # If the user wants to see the Final Bill page but not count it, that's a UI concern,
            # but for an API, returning it might imply it should be counted.
            # However, the "pagewise_line_items" is a list of pages. 
            # If I remove the page, the user loses that data.
            # But if I keep it, they double count.
            # Let's look at the requirement again: "Final Total will be sum (of all individual line items in the bills) without double-counting."
            # This implies the *derived* total should be correct.
            # The API response doesn't have a "total_amount" field, only "total_item_count".
            # So the consumer will likely sum up `item_amount` from all items in `pagewise_line_items`.
            # Therefore, I MUST exclude the Final Bill items from `pagewise_line_items` if details exist.
            
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
            
            logger.info(f"✓ Extraction complete: {len(filtered_pages)} pages (filtered), {len(all_items)} items")
            
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
