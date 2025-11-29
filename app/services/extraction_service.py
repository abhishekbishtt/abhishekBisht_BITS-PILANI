from typing import Dict, Any, List
import logging

from app.services.gemini_service import GeminiService
from app.services.document_service import DocumentService
from app.models.schemas import PageData, TokenUsage

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
            pdf_bytes = await self.document_service.download_document(url)
            
            # Convert to images
            images = self.document_service.convert_pdf_to_images(pdf_bytes)
            logger.info(f"Processing {len(images)} pages")
            
            # Process all pages
            all_pages = []
            total_tokens = {"total": 0, "input": 0, "output": 0}
            
            for page_idx, image in enumerate(images, 1):
                logger.info(f"Processing page {page_idx}/{len(images)}")
                result = await self.gemini_service.analyze_page(image, page_idx)
                
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
            
            # Aggregate results
            all_items = []
            for page in all_pages:
                all_items.extend(page.bill_items)
            
            response_data = {
                "pagewise_line_items": [
                    {
                        "page_no": page.page_no,
                        "page_type": page.page_type,
                        "bill_items": [item.dict() for item in page.bill_items]
                    }
                    for page in all_pages
                ],
                "total_item_count": len(all_items)
            }
            
            logger.info(f"✓ Extraction complete: {len(all_pages)} pages, {len(all_items)} items")
            
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
