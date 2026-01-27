from typing import List
from difflib import SequenceMatcher

from app.models.schemas import PageData

def remove_duplicates_across_pages(pages: List[PageData]) -> List[PageData]:
    """Remove duplicate items using fuzzy matching"""
    seen_items = []
    unique_pages = []
    
    for page in pages:
        unique_items = []
        for item in page.bill_items:
            # Normalize name for comparison
            normalized_name = item.item_name.strip().upper()
            
            # Check against seen items (fuzzy match)
            is_duplicate = False
            for seen in seen_items:
                similarity = SequenceMatcher(None, normalized_name, seen).ratio()
                if similarity > 0.85:  # 85% similar = duplicate
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_items.append(item)
                seen_items.append(normalized_name)
        
        page.bill_items = unique_items
        unique_pages.append(page)
    
    return unique_pages
