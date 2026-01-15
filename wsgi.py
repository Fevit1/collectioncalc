from flask import Flask, request, jsonify

app = Flask(__name__)

# CORS headers for frontend
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return response

# Simple health check
@app.route('/')
def home():
    return jsonify({
        "status": "CollectionCalc API is running",
        "version": "2.0",
        "features": ["database_lookup", "ebay_valuation", "recency_weighting"]
    })

@app.route('/api/valuate', methods=['POST', 'OPTIONS'])
def valuate():
    """Enhanced valuation with eBay data."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from comic_lookup import lookup_comic
        from ebay_valuation import get_valuation_with_ebay
        
        data = request.get_json()
        
        # Try database lookup first
        db_result = lookup_comic(
            title=data.get('title', ''),
            issue=data.get('issue', ''),
            publisher=data.get('publisher')
        )
        
        # Get valuation with eBay data
        result = get_valuation_with_ebay(
            title=data.get('title', ''),
            issue=data.get('issue', ''),
            grade=data.get('grade', 'NM'),
            publisher=data.get('publisher'),
            year=data.get('year'),
            db_result=db_result
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/valuate/simple', methods=['POST', 'OPTIONS'])
def valuate_simple():
    """Original simple valuation (database only, no eBay)."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from valuation_model import ValuationModel
        from comic_lookup import lookup_comic
        
        data = request.get_json()
        model = ValuationModel()
        
        # Try database lookup first
        db_result = lookup_comic(
            title=data.get('title', ''),
            issue=data.get('issue', ''),
            publisher=data.get('publisher')
        )
        
        base_value = db_result.get('base_value', 50.0) if db_result.get('found') else 50.0
        
        result = model.calculate_value(
            base_nm_value=base_value,
            grade=data.get('grade', 'NM'),
            edition=data.get('edition', 'direct'),
            year=data.get('year'),
            publisher=data.get('publisher', 'Unknown')
        )
        
        return jsonify({
            'final_value': result.final_value,
            'confidence': result.confidence_score,
            'db_found': db_result.get('found', False),
            'steps': result.calculation_steps
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/lookup', methods=['GET'])
def lookup():
    try:
        from comic_lookup import lookup_comic
        
        title = request.args.get('title', '')
        issue = request.args.get('issue', '')
        publisher = request.args.get('publisher')
        
        result = lookup_comic(title=title, issue=issue, publisher=publisher)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
