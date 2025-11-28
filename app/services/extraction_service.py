import asyncio
from typing import List
import logging

from app.models.schemas import APIResponse, PageData, ExtractedData, TokenUsage
from app.models.domain import DocumentContext
from app.services.gemini_service import GeminiService  # CHANGED: import GeminiService
from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)


class ExtractionService:
    """Service for orchestrating the extraction process"""
    
    def __init__(self):
        self.gemini_service = GeminiService()  # CHANGED: use GeminiService
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
        logger.info(f"Downloading document from: {document_url}")
        doc_context = await self.document_service.prepare_document(document_url)
        
        # Check if document was processed
        if not doc_context or not doc_context.images:
            logger.error(f"Failed to extract images from document. Total pages: {doc_context.total_pages if doc_context else 0}")
            raise ValueError("Failed to extract images from document. The PDF may be corrupted or inaccessible.")
        
        logger.info(f"Processing {doc_context.total_pages} page(s), {len(doc_context.images)} images extracted...")
        
        # Process pages in parallel
        tasks = []
        for idx, image in enumerate(doc_context.images, start=1):
            task = asyncio.get_event_loop().run_in_executor(
                None,
                self.gemini_service.analyze_page,  # CHANGED: use gemini_service
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
        failed_pages = []
        
        for result in results:
            if result.get("page_data") and not result.get("error"):
                # Convert to PageData model
                page = PageData(**result["page_data"])
                all_pages.append(page)
                
                # Aggregate tokens
                total_tokens += result["token_usage"]["total_tokens"]
                total_input_tokens += result["token_usage"]["input_tokens"]
                total_output_tokens += result["token_usage"]["output_tokens"]
            else:
                error_msg = result.get("error", "Unknown error")
                logger.warning(f"Page {result.get('page_number', '?')} processing failed: {error_msg}")
                failed_pages.append(result.get('page_number', '?'))
        
        # Check if all pages failed
        if not all_pages:
            error_msg = f"All pages failed to process. Failed pages: {failed_pages}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Calculate total items
        total_items = sum(len(page.bill_items) for page in all_pages)
        
        logger.info(
            f"✓ Extraction complete: {len(all_pages)}/{doc_context.total_pages} pages successful, "
            f"{total_items} items extracted, {total_tokens} tokens used"
        )
        
        if failed_pages:
            logger.warning(f"Failed pages: {failed_pages}")
        
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
