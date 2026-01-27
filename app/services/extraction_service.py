import asyncio
from typing import Dict, Any, List

from app.services.gemini_service import GeminiService
from app.services.document_service import DocumentService
from app.models.schemas import PageData, TokenUsage, BillItem


class ExtractionService:
    """Extraction service - Full document processing with multi-doc parallelism"""
    
    def __init__(self):
        self.gemini_service = GeminiService()
        self.document_service = DocumentService()
        self._gemini_semaphore = None
    
    @property
    def gemini_semaphore(self):
        """Lazy-initialized semaphore for concurrent document processing"""
        if self._gemini_semaphore is None:
            # Limit concurrent DOCUMENTS (not pages)
            self._gemini_semaphore = asyncio.Semaphore(5)
        return self._gemini_semaphore
    
    async def extract_from_url(self, url: str) -> Dict[str, Any]:
        """
        Extract bill data from document URL.
        
        Architecture:
        - Downloads document and converts to images
        - Sends ALL pages to Gemini in ONE call (full context)
        - Gemini handles deduplication across pages
        - Semaphore limits concurrent documents for rate limiting
        
        Args:
            url: URL of the document to process
            
        Returns:
            Dict with extraction results and token usage
        """
        try:
            # Step 1: Download document
            file_content, file_type = await self.document_service.download_document(url)
            
            # Step 2: Convert to images
            page_images = self.document_service.process_document(file_content, file_type)
            total_pages = len(page_images)
            
            # Step 3: Send ALL pages in ONE Gemini call (with rate limiting)
            async with self.gemini_semaphore:
                result = await self.gemini_service.analyze_full_document(
                    images=page_images,
                    total_pages=total_pages
                )
            
            # Step 4: Process response
            if not result.get("success", False):
                return {
                    "is_success": False,
                    "token_usage": TokenUsage(**result["token_usage"]),
                    "data": {"pagewise_line_items": [], "total_item_count": 0},
                    "error": result.get("error", "Unknown error")
                }
            
            # Step 5: Filter and format pages
            all_extracted_pages = []
            for page_data in result.get("pages", []):
                try:
                    page = PageData(**page_data)
                    
                    # Filter valid items (amount > 0)
                    valid_items = [
                        item for item in page.bill_items
                        if item.item_amount is not None and item.item_amount > 0
                    ]
                    page.bill_items = valid_items
                    
                    if page.bill_items:
                        all_extracted_pages.append(page)
                except Exception:
                    continue
            
            # Step 6: Filter for detail pages only
            detail_pages = [
                page for page in all_extracted_pages
                if page.page_type in ["Bill Detail", "Pharmacy"]
            ]
            final_pages = detail_pages if detail_pages else all_extracted_pages
            
            # Step 7: Build response
            all_items = []
            pagewise_data = []
            
            for page in final_pages:
                for item in page.bill_items:
                    all_items.append(item)
                
                pagewise_data.append({
                    "page_no": page.page_no,
                    "page_type": page.page_type,
                    "bill_items": [item.dict() for item in page.bill_items]
                })
            
            return {
                "is_success": True,
                "token_usage": TokenUsage(**result["token_usage"]),
                "data": {
                    "pagewise_line_items": pagewise_data,
                    "total_item_count": len(all_items)
                }
            }
            
        except Exception as error:
            return {
                "is_success": False,
                "token_usage": TokenUsage(total_tokens=0, input_tokens=0, output_tokens=0),
                "data": {"pagewise_line_items": [], "total_item_count": 0},
                "error": str(error)
            }
    
    async def extract_multiple(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Process multiple documents in parallel.
        
        Each document is processed with full context (all pages in one call).
        Semaphore limits concurrent API calls to prevent rate limiting.
        
        Args:
            urls: List of document URLs
            
        Returns:
            List of extraction results
        """
        tasks = [self.extract_from_url(url) for url in urls]
        return await asyncio.gather(*tasks, return_exceptions=True)
