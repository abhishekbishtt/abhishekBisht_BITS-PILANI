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
EXTRACTION_PROMPT = """You are an expert Medical Bill Auditor with forensic accounting skills.

TASK: Extract line items from this medical bill page into JSON format.

CRITICAL EXTRACTION RULES:
1. ONLY extract INDIVIDUAL CHARGEABLE ITEMS (medicines, procedures, tests, consultations, room charges)
2. STRICTLY IGNORE these rows (they are NOT line items):
   - Headers (e.g., "Description", "Qty", "Rate", "Amount")
   - Subtotals (e.g., "Subtotal", "Department Total", "Sub Total")
   - Tax rows (e.g., "GST", "CGST", "SGST", "Tax")
   - Discount rows (unless the discount is embedded in item_amount)
   - Grand totals (e.g., "Total", "Net Amount", "Final Total", "Amount Payable")
   - Round-off adjustments
   - Summary sections

3. For each valid line item, extract:
   - item_name: Exact name from the bill (translate to English if non-English)
   - item_rate: Price per unit
   - item_quantity: Number of units
   - item_amount: Total amount for that item (rate × quantity, post any item-level discounts)

4. DATA QUALITY RULES:
   - If item_amount is 0 or missing, skip that row (unless part of a bundle)
   - If handwritten text exists, transcribe it accurately
   - If text is in Hindi/regional languages, translate item_name to English
   - Keep numerical values as-is (don't add currency symbols)

5. FRAUD DETECTION:
   - Check for font inconsistencies (different fonts/sizes in amount columns)
   - Look for signs of overwriting or whiteout
   - Look for misaligned text or suspicious alterations
   - Set fraud_suspected=true if you detect any tampering

6. PAGE CLASSIFICATION:
   - "Bill Detail": Contains itemized charges
   - "Final Bill": Contains summary/total page
   - "Pharmacy": Medicine/drug bills

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

IMPORTANT: Return ONLY the JSON object. No additional text or explanation."""


# Ignored row patterns
IGNORED_PATTERNS = [
    "subtotal", "sub total", "sub-total",
    "grand total", "net total", "final total",
    "total amount", "amount payable",
    "cgst", "sgst", "gst", "tax",
    "discount", "round off", "roundoff",
    "description", "qty", "rate", "amount"
]
