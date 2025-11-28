from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
from app.core.constants import PageType

class BillItem(BaseModel):
    """Individual line item from a bill"""
    item_name: str = Field(..., description="Name of the item exactly as mentioned in the bill")
    item_amount: float = Field(..., description="Net amount post discounts")
    item_rate: float = Field(..., description="Rate per unit")
    item_quantity: float = Field(..., description="Quantity of the item")


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
    """Request body for document extraction"""
    document: str = Field(..., description="URL to the document (PDF or image)")
