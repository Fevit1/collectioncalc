"""
Comic Extraction Module
Extracts comic book information from photos using Claude Vision.
"""

import os
import base64
import json
import requests
from io import BytesIO

# Try to import barcode scanning library
try:
    from pyzbar import pyzbar
    from PIL import Image
    BARCODE_SCANNING_AVAILABLE = True
except ImportError:
    BARCODE_SCANNING_AVAILABLE = False
    print("pyzbar not available - barcode scanning disabled")

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')


def scan_barcode(image_data: bytes) -> dict:
    """
    Scan image for UPC barcode and extract the 5-digit supplement.
    
    Args:
        image_data: Raw image bytes (JPEG, PNG, etc.)
    
    Returns:
        dict with barcode info or None if not found
    """
    if not BARCODE_SCANNING_AVAILABLE:
        return None
    
    try:
        # Open image with PIL
        image = Image.open(BytesIO(image_data))
        
        # Scan for barcodes
        barcodes = pyzbar.decode(image)
        
        for barcode in barcodes:
            data = barcode.data.decode('utf-8')
            barcode_type = barcode.type
            
            # UPC-A is 12 digits, EAN-13 is 13 digits
            # The 5-digit supplement may be separate or appended
            if barcode_type in ['UPCA', 'EAN13', 'UPCE']:
                print(f"[Barcode] Found {barcode_type}: {data}")
                return {
                    'type': barcode_type,
                    'data': data,
                    'supplement': None  # Supplement usually separate
                }
            
            # EAN-5 is the 5-digit supplement we want!
            if barcode_type == 'EAN5' or (len(data) == 5 and data.isdigit()):
                print(f"[Barcode] Found 5-digit supplement: {data}")
                return {
                    'type': 'SUPPLEMENT',
                    'data': data,
                    'supplement': data
                }
        
        # No barcode found
        return None
        
    except Exception as e:
        print(f"[Barcode] Scan error: {e}")
        return None


def decode_barcode(digits: str) -> dict:
    """
    Decode 5-digit UPC supplement code from comic book barcode.
    
    Standard format (IIICP) since Diamond 2008/2009:
        - Digits 1-3: Issue number (001-999)
        - Digit 4: Cover variant (1=A, 2=B, 3=C, etc.)
        - Digit 5: Printing (1=1st, 2=2nd, etc.)
    
    Args:
        digits: 5-digit barcode supplement string
    
    Returns:
        dict with decoded info, or None if invalid
    """
    if not digits or len(digits) != 5 or not digits.isdigit():
        return None
    
    cover_num = int(digits[3])
    printing_num = int(digits[4])
    
    return {
        'issue': int(digits[0:3]),
        'cover': cover_num,
        'cover_letter': chr(64 + cover_num) if cover_num > 0 else None,  # 1=A, 2=B, etc.
        'printing': printing_num,
        'is_variant': cover_num > 1,      # True if not cover A
        'is_reprint': printing_num > 1,   # True if not 1st printing
    }


# Vision Guide prompt - JSON template FIRST for better compliance
EXTRACTION_PROMPT = """Analyze this comic book image and extract information.

YOU MUST RETURN EXACTLY THIS JSON STRUCTURE - NO OTHER FIELDS ALLOWED:
```json
{
  "title": "",
  "issue": "",
  "issue_type": "",
  "publisher": "",
  "year": null,
  "writer": "",
  "artist": "",
  "edition": "",
  "printing": "",
  "is_facsimile": false,
  "cover": "",
  "variant": "",
  "barcode_digits": "",
  "suggested_grade": "",
  "defects": [],
  "signatures": [],
  "grade_reasoning": ""
}
```

FIELD DEFINITIONS:

IDENTIFICATION FIELDS:
- title: Comic book title (largest text on cover). Main series name only - NOT "Annual" or "Special" (those go in issue_type).
- issue: Issue number. Look for "#" symbol, typically TOP-LEFT near price. IGNORE prices (60¢, $1.00, 25p). Just the number, no # symbol.
- issue_type: Check for these indicators:
  * "Annual" or "ANNUAL" → "Annual"
  * "King-Size Special" or "KING-SIZE SPECIAL" → "Annual"
  * "Giant-Size" or "GIANT-SIZE" → "Giant-Size"
  * "Special" or "SPECIAL" (standalone) → "Special"
  * "Special Edition" → "Special Edition"
  * None found → "Regular"
- publisher: Publisher name (Marvel, DC, Image, etc.)
- year: Publication year from copyright/indicia, or null if not visible
- writer: Writer credits on cover ("Written by NAME", "WRITER: NAME"). Empty string if not found.
- artist: Artist credits on cover ("Art by NAME", "ARTIST: NAME", "PENCILS"). Empty string if not found.
- edition: Check BOTTOM-LEFT CORNER. UPC BARCODE = "newsstand". ARTWORK/LOGO = "direct". Unclear = "unknown".
- printing: Look for "2nd Printing", "3rd Print", etc. Return "1st" if no indicator, otherwise "2nd", "3rd", etc.
- is_facsimile: true if "FACSIMILE", "FACSIMILE EDITION", or "FACSIMILE REPRINT" appears anywhere. These are modern reprints worth $5-15.
- cover: Variant indicators like "Cover A", "Cover B", "Variant Cover", "1:25", "Virgin", etc. Empty string if none.
- variant: Other variant description ("McFarlane variant", "Artgerm cover"). Empty string if none.
- barcode_digits: IMPORTANT - Find the 5-DIGIT ADD-ON CODE next to the main UPC barcode (bottom-left). It's a separate smaller barcode to the RIGHT of the main UPC. The 5 digits may be printed VERTICALLY or horizontally. Examples: "00111", "00121", "00412". Extract ONLY these 5 digits. Empty string if not readable. Do NOT return the main 12-digit UPC.

CONDITION FIELDS:
- suggested_grade: Based on visible condition: MT, NM, VF, FN, VG, G, FR, or PR. Be conservative.
- defects: Array of defects ON THE COMIC (not bag/sleeve). Examples: "Tear on front cover", "Spine roll", "Corner wear". Empty array [] if none.
- signatures: Array of signatures visible. Note if creator or unknown. Examples: "Creator signature - Jim Lee", "Unknown signature". Empty array [] if none.
- grade_reasoning: Brief explanation. Example: "NM - Sharp corners, clean colors, no visible defects"

GRADE GUIDE:
- MT (10.0): Perfect
- NM (9.4): Nearly perfect, minor imperfections only
- VF (8.0): Minor wear, small stress marks OK
- FN (6.0): Moderate wear, minor creases OK
- VG (4.0): Significant wear, small tears/creases
- G (2.0): Heavy wear, larger creases
- FR (1.5): Major wear, tears, pieces missing
- PR (1.0): Severe damage

IMPORTANT RULES:
1. Do NOT confuse prices (60¢, $1.50) with issue numbers
2. ALWAYS check for "Annual", "Giant-Size", "Special" - these are different series
3. ALWAYS check for "FACSIMILE" - these are reprints worth much less
4. Ignore bag/sleeve artifacts - assess the comic itself
5. Creator signatures ADD value, random writing is a defect
6. If image is UPSIDE-DOWN, add "is_upside_down": true

Return ONLY the JSON object with ALL fields shown above. Use empty string "" for unknown text fields, null for year, empty array [] for defects/signatures."""


def extract_from_photo(image_data: bytes, filename: str = "comic.jpg") -> dict:
    """
    Extract comic information from a photo using Claude Vision.
    
    Args:
        image_data: Raw image bytes
        filename: Original filename (used to determine media type)
    
    Returns:
        dict with extracted fields or error
    """
    if not ANTHROPIC_API_KEY:
        return {"success": False, "error": "ANTHROPIC_API_KEY not configured"}
    
    # Determine media type from filename
    ext = filename.lower().split('.')[-1] if '.' in filename else 'jpg'
    media_type_map = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'webp': 'image/webp',
        'heic': 'image/heic'
    }
    media_type = media_type_map.get(ext, 'image/jpeg')
    
    # Convert to base64
    base64_data = base64.b64encode(image_data).decode('utf-8')
    
    return extract_from_base64(base64_data, media_type)


def extract_from_base64(base64_data: str, media_type: str = "image/jpeg") -> dict:
    """
    Extract comic information from a base64-encoded image.
    
    Args:
        base64_data: Base64-encoded image string
        media_type: MIME type of the image
    
    Returns:
        dict with extracted fields or error
    """
    if not ANTHROPIC_API_KEY:
        return {"success": False, "error": "ANTHROPIC_API_KEY not configured"}
    
    # First, try to scan barcode with pyzbar (more reliable than vision)
    scanned_barcode = None
    try:
        image_bytes = base64.b64decode(base64_data)
        scanned_barcode = scan_barcode(image_bytes)
        if scanned_barcode:
            print(f"[Extraction] Barcode scanned: {scanned_barcode}")
    except Exception as e:
        print(f"[Extraction] Barcode scan failed: {e}")
    
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1000,
                "temperature": 0,
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_data
                            }
                        },
                        {
                            "type": "text",
                            "text": EXTRACTION_PROMPT
                        }
                    ]
                }]
            },
            timeout=60
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Anthropic API error: {response.status_code} - {response.text}"
            }
        
        data = response.json()
        
        # Extract text content
        text_content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text_content += block.get("text", "")
        
        # Parse JSON from response
        import re
        json_match = re.search(r'\{[\s\S]*\}', text_content)
        
        if json_match:
            extracted = json.loads(json_match.group())
            
            # Ensure all expected fields exist with defaults
            defaults = {
                "title": "",
                "issue": "",
                "issue_type": "Regular",
                "publisher": "",
                "year": None,
                "writer": "",
                "artist": "",
                "edition": "unknown",
                "printing": "1st",
                "is_facsimile": False,
                "cover": "",
                "variant": "",
                "barcode_digits": "",
                "suggested_grade": "",
                "defects": [],
                "signatures": [],
                "grade_reasoning": ""
            }
            
            # Apply defaults for missing fields
            for key, default_value in defaults.items():
                if key not in extracted:
                    extracted[key] = default_value
            
            # Migrate old field names if present
            if "signature_detected" in extracted:
                del extracted["signature_detected"]
            if "signature_analysis" in extracted:
                del extracted["signature_analysis"]
            
            # Use pyzbar barcode if Claude didn't find one
            if scanned_barcode and scanned_barcode.get('supplement'):
                if not extracted.get('barcode_digits'):
                    extracted['barcode_digits'] = scanned_barcode['supplement']
                    extracted['barcode_source'] = 'pyzbar'
                    print(f"[Extraction] Using pyzbar barcode: {scanned_barcode['supplement']}")
            
            # Decode barcode if present
            if extracted.get('barcode_digits'):
                barcode_decoded = decode_barcode(extracted['barcode_digits'])
                if barcode_decoded:
                    extracted['barcode_decoded'] = barcode_decoded
                    print(f"[Extraction] Barcode decoded: {barcode_decoded}")
            
            return {
                "success": True,
                "extracted": extracted
            }
        else:
            return {
                "success": False,
                "error": "Could not parse extraction response",
                "raw": text_content
            }
            
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timed out"}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"JSON parse error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
