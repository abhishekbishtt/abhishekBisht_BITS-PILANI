from enum import Enum


class PageType(str, Enum):
    """Page type classification"""
    BILL_DETAIL = "Bill Detail"
    FINAL_BILL = "Final Bill"
    PHARMACY = "Pharmacy"


class FileType(str, Enum):
    """Supported file types"""
    PDF = "pdf"
    IMAGE = "image"

# Extraction prompt
EXTRACTION_PROMPT = """
    You are a precise medical bill data extraction system. Extract line items from any medical bill format with zero double-counting.

    ## PAGE CLASSIFICATION (General Rules)

    Classify each page based on **content structure**, not headers or titles:

    **Pharmacy**: Contains medicines/drugs with batch numbers, HSN codes, drug names

    **Bill Detail**: Contains **tabular line items** with:
    - **QTY/QUANTITY column** with numeric values
    - Individual descriptions and amounts per row
    - **CRITICAL**: Classify as Bill Detail even if page contains patient headers, titles, or metadata above the table

    **Final Bill**: Contains **only** summary totals, sub-totals, and grand totals with **no individual line items**

    ### Golden Rule:
    > **Presence of line items with QTY + individual amount → Bill Detail, regardless of headers above them**

    ## PARENT vs CHILD IDENTIFICATION

    ### **SKIP PARENT ROWS** (Category Headers & Totals):
    1. **Category name in first column** with **QTY = 1** (or empty) and amount that **matches sum of following rows**
    2. **Pattern**: Row describes a category (e.g., "CONSUMABLE CHARGES", "WARD CHARGES") not a specific service
    3. **Amount is a subtotal**: The number equals sum of multiple subsequent rows with more specific descriptions

    ### **EXTRACT CHILD ROWS** (Line Items):
    - **Specific service/item description** in first column (not a category name)
    - **Numeric QTY value present** (1.0, 2.0, 18.0, etc.)
    - **Individual amount present** in AMOUNT column (not a sum of other rows)
    - **All columns populated** with data for that specific line item

    ### **SKIP HEADER ROWS**:
    - Column titles: "DATE", "DESCRIPTION", "QTY.", "RATE", "AMOUNT", "COMPANY AMOUNT"
    - Patient information, bill metadata, page numbers

    ## DECISION TREE (APPLY THIS LOGIC)

    For each row in the table:
    1. **Is DESCRIPTION a category name** (not specific service) **AND QTY = 1** (or empty)? → LIKELY PARENT → SKIP
    2. **Does this row's amount equal sum of following rows** with more specific descriptions? → CONFIRMED PARENT → SKIP
    3. **Is QTY column empty or missing?** → SKIP (parent header)
    4. **Otherwise** (has QTY, specific description, individual amount) → EXTRACT (child item)

    ## VISUAL PATTERN RECOGNITION

    **SKIP (Parent Category - QTY=1, category total):**
    [Category Name] | [Ref] | 1 | | | [TOTAL] | [TOTAL]
    text

    **EXTRACT (Child Item - specific service, has QTY):**
    [Date] | [Specific Service Name] | [Ref] | [Qty] | [Rate] | [Amount]
    text

    **SKIP (Column Headers):**
    DATE | DESCRIPTION | REF | QTY | RATE | AMOUNT
    text

    ## FIELD EXTRACTION

    **item_name**: Full description from DESCRIPTION column (exclude category names)

    **item_quantity**: From QTY./QTY column (convert to float: 1.0, 2.0, 18.0)

    **item_rate**: From RATE column; if missing: rate = amount / quantity

    **item_amount**: From AMOUNT/COMPANY AMOUNT column (individual line amount only)

    ## CRITICAL INSTRUCTIONS

    1. **Identify category rows**: If DESCRIPTION is a broad category and QTY=1, it's likely a parent total
    2. **Verify with sum check**: If amount equals sum of following specific rows → SKIP
    3. **Ignore headers/metadata**: Patient names, addresses, "IP BILL", "Provisional", bill numbers don't determine page type
    4. **Look for the table**: Find the grid with QTY column - that's your extraction target
    5. **Multi-page bills**: Apply same rules to every page independently

    ## OUTPUT FORMAT

    Return ONE JSON object:
    {
    "page_no": "string",
    "page_type": "Pharmacy | Bill Detail | Final Bill",
    "bill_items": [
        {
        "item_name": "string",
        "item_amount": float,
        "item_rate": float,
        "item_quantity": float
        }
    ]
    }

    ## FINAL ACCURACY CHECKLIST

    Before returning, verify:
    - [ ] No category rows extracted (rows where QTY=1 and amount = sum of children)
    - [ ] No subtotal/total/tax rows extracted
    - [ ] Every extracted item has numeric QTY and individual amount
    - [ ] Extracted amount ≠ category total shown on page

    **Extract ONLY leaf nodes. Accuracy is paramount.**
    """



    # Ignored row patterns
IGNORED_PATTERNS = [
        "subtotal", "sub total", "sub-total",
        "grand total", "net total", "final total",
        "total amount", "amount payable",
        "cgst", "sgst", "gst", "tax",
        "discount", "round off", "roundoff",
        "description", "qty", "rate", "amount"
    ]
