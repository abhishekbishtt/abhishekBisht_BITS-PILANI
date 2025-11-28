from dataclasses import dataclass
from typing import List, Optional
from PIL import Image

@dataclass
class ProcessingResult:
    """Result from processing a single page"""
    page_data: dict
    token_usage: dict
    fraud_detected: bool = False
    error: Optional[str] = None


@dataclass
class DocumentContext:
    """Context for document processing"""
    url: str
    file_type: str
    total_pages: int
    images: List[Image.Image]
