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
        Medical Bill Extraction Prompt (Generalized & Double-Counting Proof)

        You are a precise medical bill data extraction system. Extract line items from any medical bill format with zero double-counting.

        PAGE CLASSIFICATION
            Classify each page as:
                Pharmacy: Medicines, drugs, batch numbers, HSN codes
                Bill Detail: Procedures, services, SAC codes, tests, consultations
                Final Bill: Summary page (extract only if individual items exist, skip pure totals)

        PARENT vs CHILD IDENTIFICATION (CRITICAL)
            SKIP PARENT ROWS - These cause double-counting:
                Category headers with empty cells: "IPD CONSUMABLE CHARGES", "BLOOD BANK CHARGES", "Radiological Investigation"
                Summary rows: "SUB TOTAL", "Total of...", "Grand Total", "NET AMT", "CGST", "SGST", "TAX ON", "ROUNDOFF"
                Header rows: Column names like "S.No.", "Description", "Qty", "Rate", "Amount"
                Indented descriptions with 0.00 amounts (parent descriptions)
                Rows where amount equals sum of following rows (category totals)

            EXTRACT CHILD ROWS ONLY - True line items:
                Specific items with distinct descriptions and individual amounts
                Medicines: "ERIDOT 1.5GM", "IV SET 1", "DYNAPAR AQ INJ"
                Procedures: "R1001 2D echocardiography", "CN002 Consultation"
                Consumables: "INJ-EMESET-4MG-2ML", "IV-CANNULA-VENFLON-18G"
                Must have: Description + individual amount (not a sum)

        VISUAL PATTERN RULES
            PARENT Pattern (SKIP):
                text
                CATEGORY NAME | [empty] | [empty] | [empty] | [empty] | [empty]

            CHILD Pattern (EXTRACT):
                text
                ITEM NAME | BATCH123 | 1 | 21.0 | [any] | [any]

            TOTAL Pattern (SKIP):
                text
                [empty] | [empty] | [empty] | [empty] | 1,797.56 | 1,797.56

        FIELD EXTRACTION
            item_name: Full specific description (drug/procedure name with strength/specs). 
                    Exclude: category names, batch numbers, HSN codes, dates.
            item_amount: Individual line amount only. Never category totals. Convert commas to float.
            item_quantity: Numeric value. From "Rate x Qty" format, extract multiplier. 
                        Default 1.0 if singular, 0.0 if unclear.
            item_rate: Rate per unit. From "Rate x Qty", extract base rate. 
                    If not explicit, calculate as amount/quantity or use 0.0.

        CROSS-PAGE CONTEXT
            Same item on multiple pages = separate line items (extract each occurrence)
            Parent continues across pages: Extract children from all pages, skip parent on each
            Never assume duplication: Extract what you see on each page

        OUTPUT FORMAT (JSON):
            {
            "page_no": "1",
            "page_type": "Bill Detail | Final Bill | Pharmacy",
            "fraud_suspected": false,
            "bill_items": [
                {
                "item_name": "string",
                "item_rate": 0.0,
                "item_quantity": 0.0,
                "item_amount": 0.0
                }
            ]
            }

        ACCURACY CHECKLIST
            Verify before returning:
                No category headers in extracted items
                No subtotal/total rows extracted
                No tax rows extracted
                Each item has distinct amount (not a sum)
                Sum of items ≠ any parent total on page
                Extract ONLY leaf nodes. Accuracy is paramount.
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
