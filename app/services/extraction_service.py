import asyncio
from typing import List
import logging

from app.models.schemas import APIResponse, PageData, ExtractedData, TokenUsage
from app.models.domain import DocumentContext
from app.services.gemini_service import GeminiService
from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)


class ExtractionService:
    """Service for orchestrating the extraction process"""
    
    def __init__(self):
        self.gemini_service = GeminiService()
        self.document_service = DocumentService()
    
    async def extract_from_url(self, document_url: str) -> APIResponse:
        """
        Extract bill data from document URL
        
        Args:
            document_url: URL to the document
            
        Returns:
            APIResponse with extracted data
        """
        # Prepare document
        doc_context = await self.document_service.prepare_document(document_url)
        logger.info(f"Processing {doc_context.total_pages} page(s)...")
        
        # Process pages in parallel
        tasks = []
        for idx, image in enumerate(doc_context.images, start=1):
            task = asyncio.get_event_loop().run_in_executor(
                None,
                self.gemini_service.analyze_page,
                image,
                idx
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Aggregate results
        all_pages: List[PageData] = []
        total_tokens = 0
        total_input_tokens = 0
        total_output_tokens = 0
        
        for result in results:
            if result["page_data"] and not result["error"]:
                # Convert to PageData model
                page = PageData(**result["page_data"])
                all_pages.append(page)
                
                # Aggregate tokens
                total_tokens += result["token_usage"]["total_tokens"]
                total_input_tokens += result["token_usage"]["input_tokens"]
                total_output_tokens += result["token_usage"]["output_tokens"]
            else:
                logger.warning(f"Page processing failed: {result['error']}")
        
        # Calculate total items
        total_items = sum(len(page.bill_items) for page in all_pages)
        
        logger.info(
            f"✓ Extraction complete: {len(all_pages)}/{doc_context.total_pages} pages, "
            f"{total_items} items, {total_tokens} tokens"
        )
        
        # Build response
        return APIResponse(
            is_success=True,
            token_usage=TokenUsage(
                total_tokens=total_tokens,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens
            ),
            data=ExtractedData(
                pagewise_line_items=all_pages,
                total_item_count=total_items
            )
        )
