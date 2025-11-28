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
   - item_rate: Price per unit **ONLY if explicitly shown on the bill**
   - item_quantity: Number of units **ONLY if explicitly shown on the bill**
   - item_amount: Total amount for that item (ALWAYS extract this)

4. **RATE AND QUANTITY EXTRACTION (CRITICAL):**
   ⚠️ DO NOT calculate or infer item_rate or item_quantity using math/division
   ⚠️ DO NOT use unitary method (e.g., rate = amount ÷ quantity)
   ⚠️ ONLY extract rate/quantity if they are EXPLICITLY PRINTED on the bill
    
   ⚠️⚠️⚠️ COMMON MISTAKES - DO NOT DO THESE ⚠️⚠️⚠️

    ❌ MISTAKE 1 - Using "Gross" column for item_rate:
    Bill columns: [Date, Qty, Gross, Net]
    Item: BLOOD TEST | 13/11/25 | 1 No | 80.00 | 73.60

    WRONG extraction:
    {
    "item_rate": 80.0,  // ❌ This is from Gross column, not Rate!
    "item_quantity": 1.0,
    "item_amount": 73.60
    }

    CORRECT extraction:
    {
    "item_rate": 0.0,  // ✓ No Rate column exists
    "item_quantity": 1.0,
    "item_amount": 73.60
    }

    ❌ MISTAKE 2 - Assuming Gross = Rate when Qty = 1:
    Even if Quantity is 1, Gross is still NOT the Rate if there's no Rate column.

    ❌ MISTAKE 3 - Using "Total" or "Amount" for item_rate:
    These are total amounts, not rates per unit.



    
    If item_rate is NOT shown on bill → set item_rate = 0.0
    If item_quantity is NOT shown on bill → set item_quantity = 0.0
    
    EXAMPLES:
    ✓ Bill shows: "Blood Test | Qty: 2 | Rate: 500 | Amt: 1000"
        → item_rate=500.0, item_quantity=2.0, item_amount=1000.0
    
    ✓ Bill shows: "X-Ray ........... ₹800" (no rate/qty columns)
        → item_rate=0.0, item_quantity=0.0, item_amount=800.0
    
    ✗ Bill shows: "MRI Scan ........ ₹5000" (no rate/qty shown)
        → item_rate=0.0, item_quantity=0.0, item_amount=5000.0
        ❌ DO NOT calculate rate=5000, quantity=1
    
    !!!In case if some information is missing do not do any kind of calculations just keep it as 0.0 DO NOT ASSUME AS WELL!!!

5. DATA QUALITY RULES:
   - If item_amount is 0 or missing, skip that row (unless part of a bundle)
   - If handwritten text exists, transcribe it accurately
   - If text is in Hindi/regional languages, translate item_name to English
   - Keep numerical values as-is (don't add currency symbols)

6. FRAUD DETECTION:
   - Check for font inconsistencies (different fonts/sizes in amount columns)
   - Look for signs of overwriting or whiteout
   - Look for misaligned text or suspicious alterations
   - Set fraud_suspected=true if you detect any tampering

7. PAGE CLASSIFICATION:
   - "Bill Detail": Contains itemized charges
   - "Final Bill": Contains summary/total page
   - "Pharmacy": Medicine/drug bills
   Identify the page type based on the STRUCTURE of information:

        **Decision Question:** "Does this page show INDIVIDUAL items with specific names, or only CATEGORY totals?"

        📋 **"Bill Detail"** - Pages showing INDIVIDUAL itemized charges:
        
        ✓ Characteristics:
        - Each row = ONE specific item/medicine/test/procedure
        - You can see actual item names (e.g., "BLOOD SUGAR BY GLUCOMETER", "X-RAY CHEST", "PARACETAMOL 500MG")
        - May have dates per item, quantities per item
        - Has detailed line-by-line breakdown
        - May have subtotals for categories (e.g., "Investigation Total: 15,020.00")
        
        ✓ Example structure:
            BLOOD SUGAR BY GLUCOMETER | 13/11/25 | 1 No | 80.00 | 73.60
            X-RAY CHEST | 14/11/25 | 1 No | 500.00 | 460.00
            LUMBAR PUNCTURE | 17/11/25 | 1 No | 1000.00 | 920.00
            SYRINGE/INFUSION PUMP | 07/11/25 | 4 No | 1320.00 | 1214.40
        → Each line is a DIFFERENT specific service/item
        

        📊 **"Final Bill"** - Pages showing CATEGORY summaries only:

        ✓ Characteristics:
        - Each row = ONE entire category (e.g., "Consultation", "Equipment", "Pharmacy")
        - NO specific item names - only category labels
        - NO dates per item, NO individual quantities
        - Shows aggregated/consolidated amounts per category
        - Usually has payment details, grand totals, "Total Payable Amount"
        - Categories are broad service types, not specific items

        ✓ Example structure:
            Consultation | 79,750.00
            Equipment | 213,250.00
            Investigations | 173,010.00
            Pharmacy Consumables | 334,504.78
            Room Rent | 235,800.00
            Total Payable Amount | 2,209,763.00
        → Each line is a CATEGORY total, not an individual item

        💊 **"Pharmacy"** - Pages showing ONLY medicines/drugs with pharmacy-specific details:

        ✓ Characteristics:
        - Shows drug/medicine names with batch numbers and expiry dates
        - Columns like: Drug Name, Batch No, Exp Date, Qty, MRP
        - Examples: PARACETAMOL 500MG, INJECTION CEFTRIAXONE, SYRUP AZITHROMYCIN

        ⚠️ CLASSIFICATION LOGIC - Follow this decision tree:

        Step 1: Look at the first 3-5 rows of data
        Step 2: Ask: "Are these specific item names or just category labels?"
        - If you see "BLOOD SUGAR TEST", "MRI SCAN", "PARACETAMOL" → Specific items → "Bill Detail"
        - If you see "Consultation", "Equipment", "Investigations" → Category labels → "Final Bill"

        Step 3: Verify by checking structure:
        - Many similar items grouped together → "Bill Detail"
        - Few broad categories with large totals → "Final Bill"

        ⚠️ COMMON MISTAKES TO AVOID:

        ❌ WRONG: Seeing "Consultation | 79,750.00" and classifying as "Bill Detail"
        → This is a category summary, not an itemized list

        ✓ CORRECT: "Consultation | 79,750.00" → "Final Bill"

        ❌ WRONG: Seeing a page with subtotals and calling it "Final Bill"
        → If it has individual items BEFORE the subtotal, it's still "Bill Detail"

        ✓ CORRECT: 
        BLOOD TEST | 80.00
        X-RAY | 500.00
        Subtotal | 580.00 
        ← This page is "Bill Detail" (has individual items)


        Examples for Practice:

        Example 1:
            
            Service Name | Amount
            Consultation | 79,750.00
            Equipment | 213,250.00
            → page_type = "Final Bill" ✓ (only category names, no specific services)

        Example 2:

            Item Name | Date | Qty | Amount
            BLOOD SUGAR BY GLUCOMETER | 13/11/25 | 1 | 73.60
            ADVANCED VENTILATION (BEAR 750) | 07/11/25 | 1 | 2760.00
        
            → page_type = "Bill Detail" ✓ (specific item names listed)

     



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

IMPORTANT: Return ONLY the JSON object. No additional text or explanation.
DO NOT calculate missing rate or quantity values. Extract only what is visible."""


# Ignored row patterns
IGNORED_PATTERNS = [
    "subtotal", "sub total", "sub-total",
    "grand total", "net total", "final total",
    "total amount", "amount payable",
    "cgst", "sgst", "gst", "tax",
    "discount", "round off", "roundoff",
    "description", "qty", "rate", "amount"
]
