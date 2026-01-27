from pydantic import BaseModel, Field, HttpUrl, model_validator
from typing import List, Optional, Union
from app.core.constants import PageType

class BillItem(BaseModel):
    """Individual line item from a bill"""
    item_name: str = Field(..., description="Name of the item exactly as mentioned in the bill")
    item_amount: float = Field(..., description="Net amount post discounts")
    item_rate: Optional[float] = Field(default=0.00, description="Rate per unit")
    item_quantity: Optional[float] = Field(default=0.00, description="Quantity of the item")


class PageData(BaseModel):
    """Data extracted from a single page"""
    page_no: str = Field(..., description="Page number as string")
    page_type: PageType = Field(..., description="Type of the page")
    bill_items: List[BillItem] = Field(default_factory=list, description="Line items from this page")


class ExtractedData(BaseModel):
    """Complete extracted data from all pages"""
    pagewise_line_items: List[PageData] = Field(..., description="List of all pages with their items")
    total_item_count: int = Field(..., description="Total count of items across all pages")


class TokenUsage(BaseModel):
    """Token usage information from LLM calls"""
    total_tokens: int = Field(default=0)
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)


class APIResponse(BaseModel):
    """Final API response structure"""
    is_success: bool = Field(..., description="Whether the request was successful")
    token_usage: TokenUsage = Field(..., description="Cumulative token usage")
    data: ExtractedData = Field(..., description="Extracted bill data")


class ErrorResponse(BaseModel):
    """Error response structure"""
    is_success: bool = Field(default=False)
    message: str = Field(..., description="Error message")


class DocumentRequest(BaseModel):
    """
    Request body for document extraction.
    
    Supports two modes:
    - Single document: {"document": "https://example.com/bill.pdf"}
    - Multiple documents: {"documents": ["url1", "url2", "url3"]}
    
    You can provide either 'document' (single) OR 'documents' (multiple), not both.
    """
    document: Optional[str] = Field(default=None, description="Single document URL")
    documents: Optional[List[str]] = Field(default=None, description="List of document URLs for batch processing")
    
    @model_validator(mode='after')
    def validate_document_fields(self):
        """Ensure exactly one of document or documents is provided"""
        has_single = self.document is not None
        has_multiple = self.documents is not None and len(self.documents) > 0
        
        if not has_single and not has_multiple:
            raise ValueError("Must provide either 'document' (single URL) or 'documents' (list of URLs)")
        
        if has_single and has_multiple:
            raise ValueError("Cannot provide both 'document' and 'documents'. Use one or the other.")
        
        return self
    
    @property
    def is_batch_request(self) -> bool:
        """Check if this is a batch (multiple documents) request"""
        return self.documents is not None and len(self.documents) > 0
    
    @property
    def urls(self) -> List[str]:
        """Get the list of URLs to process (works for both single and batch)"""
        if self.is_batch_request:
            return self.documents
        return [self.document]

