from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage
import operator

class BillState(TypedDict):
    images: List  # All page images
    page_results: Annotated[List, operator.add]  # Accumulated page data
    seen_items: dict  # Cross-page dedup
    current_page: int
    total_tokens: dict

async def extract_page(state: BillState):
    """Extract single page with FULL context"""
    page_no = state["current_page"]
    image = state["images"][page_no-1]
    
    # Build context from PREVIOUS pages
    context = f"""PREV PAGES ({len(state['page_results'])}): {len(state['seen_items'])} unique items
    
SKIP THESE BREAKUP ITEMS FROM PRIOR PAGES:
{list(state['seen_items'].keys())[:10]}

CRITICAL: Page {page_no} - SKIP indented children, batch codes, duplicates."""
    
    # Gemini call with context
    model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp")
    response = await model.ainvoke([
        HumanMessage(content=context + EXTRACTION_PROMPT),
        HumanMessage(content=image)  # Image input
    ])
    
    page_data = parse_gemini_json(response.content)
    filtered_items = filter_breakups(page_data["bill_items"], state["seen_items"])
    
    # Update state
    new_seen = {k: v for k, v in state["seen_items"].items()}
    for item in filtered_items:
        key = f"{item['item_name'][:30].lower()}|{item['item_amount']:.2f}"
        new_seen[key] = page_no
    
    return {
        "page_results": [page_data],
        "seen_items": new_seen,
        "current_page": page_no + 1,
        "total_tokens": {"total": 1000}  # Mock
    }

# Build sequential graph
workflow = StateGraph(BillState)
workflow.add_node("extract", extract_page)
workflow.set_entry_point("extract")
workflow.add_conditional_edges("extract", should_continue)
workflow.add_edge("extract", END)

app = workflow.compile()
