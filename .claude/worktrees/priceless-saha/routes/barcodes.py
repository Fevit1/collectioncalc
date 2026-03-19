"""
Barcodes Blueprint - Barcode scanning endpoints
Routes: /api/barcode-test, /api/barcode-scan
"""
from flask import Blueprint, jsonify, request

# Create blueprint
barcodes_bp = Blueprint('barcodes', __name__, url_prefix='/api')


@barcodes_bp.route('/barcode-test', methods=['GET'])
def barcode_test():
    """Test if pyzbar/libzbar0 is working (requires Docker deployment)"""
    try:
        from pyzbar import pyzbar
        from PIL import Image
        import io
        
        # Create a tiny test image to verify full pipeline works
        test_image = Image.new('RGB', (10, 10), color='white')
        
        # Try to decode it (will find nothing, but proves library loads)
        results = pyzbar.decode(test_image)
        
        return jsonify({
            'status': 'success',
            'message': 'pyzbar and libzbar0 loaded successfully',
            'test_decode': 'working',
            'barcodes_found': len(results)  # Should be 0 for blank image
        })
    except ImportError as e:
        return jsonify({
            'status': 'error',
            'message': f'pyzbar import failed: {str(e)}',
            'hint': 'This endpoint requires Docker deployment with libzbar0'
        }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@barcodes_bp.route('/barcode-scan', methods=['POST'])
def barcode_scan():
    """
    Scan barcode from comic cover image.
    Returns UPC code including 5-digit add-on (used to identify reprints/variants).
    Automatically tries 0°, 90°, 180°, 270° rotations to find barcode.
    
    Body: {
        "image": "base64 encoded image data"
    }
    """
    try:
        from pyzbar import pyzbar
        from pyzbar.pyzbar import ZBarSymbol
        from PIL import Image
        import io
        import base64
        
        data = request.get_json() or {}
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'success': False, 'error': 'Image data required'}), 400
        
        # Remove data URL prefix if present
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decode base64 to image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if necessary (pyzbar works better with RGB)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Try scanning at different rotations (0°, 90°, 180°, 270°)
        barcodes = []
        rotation_found = 0
        
        for rotation in [0, 90, 180, 270]:
            if rotation == 0:
                rotated = image
            else:
                rotated = image.rotate(-rotation, expand=True)  # Negative for clockwise
            
            # Scan for barcodes
            found = pyzbar.decode(rotated, symbols=[ZBarSymbol.UPCA, ZBarSymbol.EAN13, ZBarSymbol.UPCE, ZBarSymbol.CODE128])
            
            if not found:
                # Try without symbol filter as fallback
                found = pyzbar.decode(rotated)
            
            if found:
                barcodes = found
                rotation_found = rotation
                break
        
        results = []
        for barcode in barcodes:
            results.append({
                'data': barcode.data.decode('utf-8'),
                'type': barcode.type,
                'rect': {
                    'left': barcode.rect.left,
                    'top': barcode.rect.top,
                    'width': barcode.rect.width,
                    'height': barcode.rect.height
                }
            })
        
        # Extract 5-digit add-on if present (used for print run identification)
        # Comics typically have UPC + 5-digit add-on
        upc_main = None
        upc_addon = None
        
        for result in results:
            code = result['data']
            # Full UPC with add-on is typically 17 digits (12 + 5)
            if len(code) >= 17:
                upc_main = code[:12]
                upc_addon = code[12:17]
            elif len(code) == 12:
                upc_main = code
            elif len(code) == 13:  # EAN-13
                upc_main = code
        
        return jsonify({
            'success': True,
            'barcodes': results,
            'count': len(results),
            'upc_main': upc_main,
            'upc_addon': upc_addon,
            'rotation_detected': rotation_found,
            'hint': 'upc_addon identifies print run: 00111 = 1st print issue 1, 00211 = 2nd print issue 1'
        })
        
    except ImportError as e:
        return jsonify({
            'success': False,
            'error': f'pyzbar not available: {str(e)}',
            'hint': 'Barcode scanning requires Docker deployment'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
