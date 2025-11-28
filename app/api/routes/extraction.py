#bill extraction end point
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
import logging

from app.models.schemas import DocumentRequest, APIResponse, ErrorResponse
from app.services.extraction_service import ExtractionService

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize service
extraction_service = ExtractionService()


@router.post("/extract-bill-data", response_model=APIResponse)
async def extract_bill_data(request: DocumentRequest):
    """
    Extract line items from a medical bill document
    
    - **document**: URL to the document (PDF or image)
    """
    try:
        return await extraction_service.extract_from_url(request.document)
        
    except HTTPException as e:
        logger.error(f"HTTP error: {e.detail}")
        return JSONResponse(
            status_code=e.status_code,
            content=ErrorResponse(
                is_success=False,
                message=e.detail
            ).dict()
        )
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                is_success=False,
                message="Failed to process document. Internal server error occurred"
            ).dict()
        )
