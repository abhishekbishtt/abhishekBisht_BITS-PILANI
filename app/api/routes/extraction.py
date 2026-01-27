from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
import logging
from typing import List, Dict, Any

from app.models.schemas import DocumentRequest, APIResponse, ErrorResponse, TokenUsage
from app.services.extraction_service import ExtractionService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/extract-bill-data")
async def extract_bill_data(request: DocumentRequest):
    """
    Extract line items from medical bill document(s).
    
    Supports both single and batch document processing:
    
    Single Document: {"document": "https://example.com/bill.pdf"}
    Batch Mode: {"documents": ["url1", "url2"]}
    
    Returns:
        For single document: Standard APIResponse
        For batch: List of results with aggregated stats
    """
    try:
        extraction_service = ExtractionService()
        
        if request.is_batch_request:
            urls = request.documents
            logger.info(f"Processing BATCH of {len(urls)} documents in parallel")
            
            results = await extraction_service.extract_multiple(urls)
            
            successful_results = []
            failed_results = []
            total_tokens = 0
            input_tokens = 0
            output_tokens = 0
            total_items = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_results.append({
                        "document_index": i,
                        "url": urls[i],
                        "error": str(result)
                    })
                elif result.get("is_success", False):
                    successful_results.append({
                        "document_index": i,
                        "url": urls[i],
                        "data": result.get("data", {})
                    })
                    token_usage = result.get("token_usage", {})
                    if hasattr(token_usage, 'total_tokens'):
                        total_tokens += token_usage.total_tokens
                        input_tokens += token_usage.input_tokens
                        output_tokens += token_usage.output_tokens
                    else:
                        total_tokens += token_usage.get("total_tokens", 0)
                        input_tokens += token_usage.get("input_tokens", 0)
                        output_tokens += token_usage.get("output_tokens", 0)
                    total_items += result.get("data", {}).get("total_item_count", 0)
                else:
                    failed_results.append({
                        "document_index": i,
                        "url": urls[i],
                        "error": result.get("error", "Unknown error")
                    })
            
            return {
                "is_success": len(failed_results) == 0,
                "batch_mode": True,
                "total_documents": len(urls),
                "successful_count": len(successful_results),
                "failed_count": len(failed_results),
                "total_items_extracted": total_items,
                "token_usage": {
                    "total_tokens": total_tokens,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens
                },
                "results": successful_results,
                "errors": failed_results if failed_results else None
            }
        
        else:
            document_url = request.document
            logger.info(f"Processing SINGLE document: {document_url}")
            
            extraction_result = await extraction_service.extract_from_url(document_url)
            return extraction_result
        
    except HTTPException as http_error:
        logger.error(f"HTTP error: {http_error.detail}")
        
        error_response = ErrorResponse(
            is_success=False,
            message=http_error.detail
        )
        
        return JSONResponse(
            status_code=http_error.status_code,
            content=error_response.dict()
        )
        
    except Exception as unexpected_error:
        logger.error(f"Unexpected error: {str(unexpected_error)}", exc_info=True)
        
        error_response = ErrorResponse(
            is_success=False,
            message="Failed to process document. Internal server error occurred"
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.dict()
        )
