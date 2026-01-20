"""
Comic Extraction for CollectionCalc
Extracts comic book information from photos using Claude's vision API.
"""

import os
import requests
import json
import base64

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


def extract_from_photo(image_data: bytes, filename: str = "comic.jpg") -> dict:
    """
    Extract comic book information from a photo using Claude's vision API.
    
    Args:
        image_data: Raw image bytes
        filename: Original filename (for content type detection)
    
    Returns:
        Dict with extracted fields or error
    """
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return {'success': False, 'error': 'ANTHROPIC_API_KEY not configured'}
    
    # Determine media type from filename
    extension = filename.split('.')[-1].lower()
    media_type_map = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'webp': 'image/webp',
        'heic': 'image/heic',
        'gif': 'image/gif'
    }
    media_type = media_type_map.get(extension, 'image/jpeg')
    
    # Convert to base64
    base64_data = base64.b64encode(image_data).decode('utf-8')
    
    prompt = """Analyze this comic book image and extract information. Return ONLY a JSON object with these fields:
- title: Comic book title
- issue: Issue number (just the number, no #)
- publisher: Publisher name (Marvel, DC, Image, etc.)
- year: Publication year
- grade: Estimated condition grade (PR, FR, G, VG, FN, VF, NM, MT) - be conservative
- edition: Look at the BOTTOM-LEFT CORNER. If you see a UPC BARCODE, return "newsstand". If you see ARTWORK or LOGO, return "direct". If unclear, return "unknown".
- printing: Look for "2nd Printing", "3rd Print", "Second Printing", etc. anywhere on cover. Return "1st" if no printing indicator found, otherwise "2nd", "3rd", etc.
- cover: Look for cover variant indicators like "Cover A", "Cover B", "Variant Cover", "1:25", "1:50", "Incentive", "Virgin", etc. Return the variant info if found, otherwise empty string.
- variant: Other variant description if applicable (e.g., "McFarlane variant", "Artgerm cover"), otherwise empty string

Be accurate. If unsure about any field, use reasonable estimates."""

    try:
        response = requests.post(
            ANTHROPIC_API_URL,
            headers={
                'Content-Type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01'
            },
            json={
                'model': 'claude-sonnet-4-20250514',
                'max_tokens': 1000,
                'messages': [{
                    'role': 'user',
                    'content': [
                        {
                            'type': 'image',
                            'source': {
                                'type': 'base64',
                                'media_type': media_type,
                                'data': base64_data
                            }
                        },
                        {
                            'type': 'text',
                            'text': prompt
                        }
                    ]
                }]
            },
            timeout=60
        )
        
        if response.status_code != 200:
            error_detail = response.text
            print(f"Anthropic API error: {response.status_code} - {error_detail}")
            return {
                'success': False,
                'error': f'API error: {response.status_code}',
                'detail': error_detail
            }
        
        data = response.json()
        
        # Extract text content from response
        text_content = ''
        for item in data.get('content', []):
            if item.get('type') == 'text':
                text_content += item.get('text', '')
        
        # Parse JSON from response
        import re
        json_match = re.search(r'\{[\s\S]*\}', text_content)
        
        if json_match:
            extracted = json.loads(json_match.group())
            return {
                'success': True,
                'extracted': extracted
            }
        else:
            return {
                'success': False,
                'error': 'Could not extract structured data from response',
                'raw_response': text_content
            }
            
    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'Request timed out'}
    except json.JSONDecodeError as e:
        return {'success': False, 'error': f'JSON parse error: {str(e)}'}
    except Exception as e:
        print(f"Extraction error: {e}")
        return {'success': False, 'error': str(e)}


def extract_from_base64(base64_data: str, filename: str = "comic.jpg") -> dict:
    """
    Extract comic book information from a base64-encoded image.
    
    Args:
        base64_data: Base64 encoded image (with or without data URL prefix)
        filename: Original filename (for content type detection)
    
    Returns:
        Dict with extracted fields or error
    """
    try:
        # Remove data URL prefix if present
        if ',' in base64_data:
            base64_data = base64_data.split(',')[1]
        
        image_data = base64.b64decode(base64_data)
        return extract_from_photo(image_data, filename)
    except Exception as e:
        return {'success': False, 'error': f'Invalid base64 data: {str(e)}'}
