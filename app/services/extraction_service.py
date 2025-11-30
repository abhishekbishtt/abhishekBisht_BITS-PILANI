import asyncio
import logging
import os
from typing import Dict, Any, List
# import backoff  # Removed unused dependency

from app.services.gemini_service import GeminiService
from app.services.document_service import DocumentService
from app.utils.image_utils import preprocess_for_extraction
from app.models.schemas import PageData, TokenUsage, BillItem

logger = logging.getLogger(__name__)

class ExtractionService:
    """Service for extracting data from medical bills with rate limiting and accuracy enhancements"""
    
    def __init__(self):
        self.gemini_service = GeminiService()
        self.document_service = DocumentService()
        self._gemini_semaphore = None  # Lazy initialization
    
    @property
    def gemini_semaphore(self):
        """Lazy property to ensure semaphore is created in the running loop"""
        if self._gemini_semaphore is None:
            self._gemini_semaphore = asyncio.Semaphore(10)
        return self._gemini_semaphore
    
    async def analyze_page_with_rate_limit(self, *args, **kwargs):
        """Wrapper with rate limiting and backoff"""
        async with self.gemini_semaphore:
            return await self.gemini_service.analyze_page(*args, **kwargs)
    
    async def extract_from_url(self, url: str) -> Dict[str, Any]:
        """Extract data with parallel batch processing and rate limiting"""
        try:
            logger.info(f"Starting extraction for: {url}")
            content, content_type = await self.document_service.download_document(url)
            images = self.document_service.process_document(content, content_type)
            total_pages = len(images)
            
            batch_size = 5
            
            
            logger.info(f"Processing {total_pages} pages in batches of {batch_size}")
            
            all_pages = []
            total_tokens = {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0}
            previous_items = []
            
            page_idx = 0
            while page_idx < total_pages:
                batch_end = min(page_idx + batch_size, total_pages)
                batch_images = images[page_idx:batch_end]
                
                # Preprocess images
                processed_images = [preprocess_for_extraction(img) for img in batch_images]
                
                # Create tasks
                tasks = [
                    self.analyze_page_with_rate_limit(
                        image=img,
                        page_no=page_idx + offset,
                        total_pages=total_pages,
                        previous_items=previous_items,
                    )
                    for offset, img in enumerate(processed_images, start=1)
                ]
                
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for offset, result in enumerate(batch_results, start=1):
                    current_page_no = page_idx + offset
                    
                    if isinstance(result, Exception):
                        logger.error(f"Page {current_page_no} exception: {result}")
                        continue
                    
                    if result.get("success"):
                        try:
                            page = PageData(**result["page_data"])
                            # Filter only valid amounts
                            page.bill_items = [
                                item for item in page.bill_items
                                if item.item_amount is not None and item.item_amount > 0
                            ]
                            
                            if page.bill_items:
                                all_pages.append(page)
                                previous_items.extend([item.dict() for item in page.bill_items])
                            
                            usage = result["token_usage"]
                            total_tokens["total_tokens"] += usage["total_tokens"]
                            total_tokens["input_tokens"] += usage["input_tokens"]
                            total_tokens["output_tokens"] += usage["output_tokens"]
                            
                        except Exception as parse_error:
                            logger.error(f"Page {current_page_no} validation error: {parse_error}")
                    else:
                        logger.warning(f"Page {current_page_no} failed: {result.get('error')}")
                
                page_idx = batch_end
            
            # NO DUPLICATE REMOVAL - trust Gemini's context awareness
            # Filter to Bill Detail/Pharmacy pages only
            detail_pages = [p for p in all_pages if p.page_type in ["Bill Detail", "Pharmacy"]]
            filtered_pages = detail_pages if detail_pages else all_pages
            
            all_items = [item for page in filtered_pages for item in page.bill_items]
            
            # SIMPLIFIED RESPONSE
            return {
                "is_success": True,
                "token_usage": TokenUsage(**total_tokens),
                "data": {
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
            }
            
        except Exception as e:
            logger.error(f"Extraction failed: {str(e)}")
            return {
                "is_success": False,
                "token_usage": TokenUsage(total_tokens=0, input_tokens=0, output_tokens=0),
                "data": {"pagewise_line_items": [], "total_item_count": 0},
                "error": str(e)
            }
