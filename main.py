import os
import re
import logging
import mimetypes
import base64
from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path
from PIL import Image
from io import BytesIO
from mistralai import Mistral

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()
BASE_DIR = Path(__file__).parent.resolve()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Mistral AI setup
load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    raise RuntimeError("MISTRAL_API_KEY environment variable not set")

client = Mistral(api_key=MISTRAL_API_KEY)

def validate_image(content: bytes) -> bool:
    try:
        Image.open(BytesIO(content)).verify()
        return True
    except Exception as e:
        logger.error(f"Invalid image: {str(e)}")
        return False

def clean_markdown(text: str) -> str:
    """Clean the OCR markdown text by removing unwanted markdown and normalizing spacing."""
    text = re.sub(r"!?\[.*?\]\(.*?\)", "", text)   # remove markdown images/links
    text = re.sub(r"[*#]", "", text)
    # Fix spaced-out words (e.g. T N D → TND, T 0 T A L → TOTAL)
    text = re.sub(r"\b([A-Z])\s+([A-Z])\b", r"\1\2", text)
    text = re.sub(r"(\w)\s+(\w)", r"\1\2", text)
    # Normalize number formats (e.g. 1 4 . 699 → 14.699)
    text = re.sub(r"(\d)\s+([.,])\s+(\d)", r"\1\2\3", text)
    text = re.sub(r"(\d)\s+(\d)", r"\1\2", text)
    return text.replace("<br>", "\n").strip()

def extract_total(text: str) -> str:
    """Extract the numeric total from the receipt text."""
    try:
        patterns = [
            r"(?i)(total\s*achats|t\s*0\s*t\s*a\s*l|total\s+général)\s*[\s:]*([\d\s.,]+)\s*(TND|USD|EUR)?",
            r"(?i)montant\s*à\s*payer\s*[\s:]*([\d\s.,]+)\s*(TND|USD|EUR)?",
            r"\b(\d{1,3}(?:[\s.,]\d{3})+(?:[\s.,]\d{2,3})?)\b",
            r"(?i)total\b[^0-9]*([\d\s.,]+)\s*(TND|USD|EUR)?",
        ]
        amounts = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                amount_str = match[1] if isinstance(match, tuple) else match
                currency = match[2] if len(match) > 2 else "TND"
                
                clean_amount = amount_str.replace(' ', '').replace(',', '.')
                if clean_amount.count('.') > 1:
                    parts = clean_amount.split('.')
                    if len(parts[-1]) == 3:
                        clean_amount = clean_amount.replace('.', '', 1)

                try:
                    amount = float(clean_amount)
                    amounts.append((amount, currency))
                except ValueError:
                    continue

        if amounts:
            valid_amounts = [a for a in amounts if a[0] > 1]
            if valid_amounts:
                max_amount = max(valid_amounts, key=lambda x: x[0])
                return f"{max_amount[0]:.3f} {max_amount[1]}"
        
        numbers = re.findall(r"\d+[\s.,]?\d+", text)
        if numbers:
            converted = [float(n.replace(' ', '').replace(',', '.')) for n in numbers]
            currency = extract_currency(text)
            return f"{max(converted):.3f} {currency}"
        
        return "Not found"
    except Exception as e:
        logger.error(f"Extraction error: {str(e)}")
        return "Error"

def extract_currency(text: str) -> str:
    match = re.search(r"(USD|EUR|TND)", text, re.IGNORECASE)
    return match.group(1).upper() if match else "TND"

def parse_markdown_table(text: str) -> list:
    rows = []
    skip_keywords = ["order", "total", "grandtotal", "salestax", "credit", "page"]
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("|") and line.endswith("|"):
            if any(kw in line.lower() for kw in skip_keywords):
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if not all(re.match(r"^:?-+:?$", c) for c in cells):
                rows.append(cells)
    return rows

def refine_item_row(row: list) -> tuple:
    if len(row) == 2:
        item, price = row
    elif len(row) >= 3:
        if re.match(r'\d+\.\d+\s*kg', row[0], re.IGNORECASE):
            return (row[0], row[1])
        elif row[0].strip().isdigit() or len(row[0].strip()) < 3:
            item, price = row[1], row[2]
        else:
            item, price = row[0], row[2]
    else:
        return None

    item = re.sub(r'\$x\$', '', item).strip()
    cleaned_price = re.sub(r"[^\d.]", "", price)
    
    try:
        price_val = float(cleaned_price)
        if price_val <= 0:
            return None
    except ValueError:
        return None

    return (item, cleaned_price) if item else None

def extract_items_from_markdown(text: str) -> list:
    rows = parse_markdown_table(text)
    items = []
    
    # First pass - basic extraction
    for row in rows:
        refined = refine_item_row(row)
        if refined:
            items.append(refined)
    
    # Second pass - merge quantities
    merged_items = []
    skip_next = False
    for i in range(len(items)):
        if skip_next:
            skip_next = False
            continue
            
        current_item = items[i]
        if i < len(items) - 1:
            next_item = items[i + 1]
            
            if quantity_match := re.search(r'(\d+\.\d+\s*kg)', next_item[0], re.I):
                merged_name = f"{current_item[0]} ({quantity_match.group(1).strip()})"
                merged_items.append((merged_name, current_item[1]))
                skip_next = True
            else:
                merged_items.append(current_item)
        else:
            merged_items.append(current_item)
    
    return merged_items

@app.get("/", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload/")
async def process_upload(request: Request, file: UploadFile = File(...)):
    try:
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(413, "File size exceeds 10MB limit")
        
        mime_type, _ = mimetypes.guess_type(file.filename)
        if mime_type not in ('image/jpeg', 'image/png'):
            raise HTTPException(400, "Only JPG/PNG images allowed")
        
        if not validate_image(content):
            raise HTTPException(400, "Invalid image file")

        base64_data = base64.b64encode(content).decode()
        image_url = f"data:{mime_type};base64,{base64_data}"

        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={"type": "image_url", "image_url": image_url}
        )
        
        if not ocr_response.pages:
            raise ValueError("No text found in OCR response")

        raw_text = ocr_response.pages[0].markdown
        cleaned_text = clean_markdown(raw_text)
        
        return templates.TemplateResponse("result.html", {
            "request": request,
            "filename": file.filename,
            "extracted_text": cleaned_text,
            "total_amount": extract_total(cleaned_text),
            "currency": extract_currency(cleaned_text),
            "extracted_data": extract_items_from_markdown(cleaned_text)
        })
    except HTTPException as he:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": he.detail
        })
    except Exception as e:
        logger.error(f"Processing error: {str(e)}", exc_info=True)
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": "Processing error. Please try again."
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)