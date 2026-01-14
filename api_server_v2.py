"""
CollectionCalc - Enhanced API Server
Integrates database lookups, valuation model, and feedback logging

Features:
1. Database lookup for base values
2. Deterministic valuation model with breakdown
3. User feedback logging for model improvement
4. Web search fallback for unknowns
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import sqlite3
from urllib.parse import parse_qs, urlparse
from datetime import datetime

# Import our modules
from comic_lookup import lookup_comic, batch_lookup, normalize_title, search_titles
from valuation_model import ValuationModel
from feedback_logger import FeedbackLogger

# Optional: Anthropic for web search fallback
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Configuration
PORT = 8000
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
DB_PATH = "comics_pricing.db"

# Initialize components
valuation_model = ValuationModel()
feedback_logger = FeedbackLogger()

# Session stats
stats = {
    'db_lookups': 0,
    'db_hits': 0,
    'web_searches': 0,
    'valuations': 0,
    'corrections_logged': 0,
    'total_tokens': 0,
    'session_start': datetime.now().isoformat()
}


def get_valuation_with_breakdown(
    title: str,
    issue: str,
    grade: str = "NM",
    edition: str = "direct",
    publisher: str = None,
    year: int = None,
    cgc: bool = False,
    signatures: list = None,
    use_web_fallback: bool = True
) -> dict:
    """
    Get comic valuation with full breakdown
    
    1. Look up base value in database
    2. If not found, optionally use web search
    3. Apply valuation model
    4. Return breakdown
    """
    stats['valuations'] += 1
    stats['db_lookups'] += 1
    
    # Step 1: Database lookup
    db_result = lookup_comic(
        title=title,
        issue=issue,
        publisher=publisher,
        year=year,
        grade="NM"  # Always get NM base value
    )
    
    base_value = None
    base_source = "unknown"
    key_issue_reason = None
    
    if db_result['found']:
        stats['db_hits'] += 1
        base_value = db_result['base_value']
        base_source = "database"
        
        # Check for key issue info
        if db_result.get('match_details', {}).get('key_issue'):
            key_issue_reason = db_result['match_details'].get('key_reason')
    
    # Step 2: Web search fallback if needed
    elif use_web_fallback and ANTHROPIC_AVAILABLE and ANTHROPIC_API_KEY:
        web_result = get_base_value_from_web(title, issue, publisher, year)
        if web_result.get('found'):
            base_value = web_result.get('nm_value', 0)
            base_source = "web_search"
            stats['web_searches'] += 1
    
    # Step 3: If still no base value, estimate based on age/publisher
    if base_value is None:
        base_value = estimate_base_value(year, publisher)
        base_source = "estimated"
    
    # Step 4: Apply valuation model
    breakdown = valuation_model.calculate_value(
        base_nm_value=base_value,
        grade=grade,
        edition=edition,
        year=year,
        publisher=publisher or "Unknown",
        cgc=cgc,
        signatures=signatures,
        key_issue_reason=key_issue_reason,
        base_value_source=base_source,
        grade_source="estimated"  # Unless CGC
    )
    
    # Convert to dict for JSON
    result = valuation_model.to_dict(breakdown)
    
    # Add lookup metadata
    result['lookup'] = {
        'title_matched': db_result.get('title', title),
        'issue_matched': db_result.get('issue', issue),
        'publisher_matched': db_result.get('publisher', publisher),
        'db_found': db_result['found'],
        'db_confidence': db_result.get('confidence', 0)
    }
    
    return result


def get_base_value_from_web(title: str, issue: str, publisher: str = None, year: int = None) -> dict:
    """
    Get base NM value from web search
    Only called when database doesn't have the comic
    """
    if not ANTHROPIC_AVAILABLE or not ANTHROPIC_API_KEY:
        return {'found': False, 'error': 'Anthropic API not available'}
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    query_parts = [title, f"#{issue}"]
    if publisher:
        query_parts.append(publisher)
    if year:
        query_parts.append(str(year))
    query_parts.append("comic NM value price guide")
    
    prompt = f"""Find the Near Mint (NM/9.4) value for this comic:
Title: {title}
Issue: #{issue}
Publisher: {publisher or 'Unknown'}
Year: {year or 'Unknown'}

Search for price guide values from GoCollect, ComicsPriceGuide, or recent eBay sold listings.

Return ONLY a JSON object:
{{"found": true, "nm_value": <number>, "source": "<source name>"}}

If you cannot find reliable pricing, return:
{{"found": false, "reason": "<why>"}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}]
        )
        
        stats['total_tokens'] += response.usage.input_tokens + response.usage.output_tokens
        
        # Extract response text
        result_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                result_text += block.text
        
        # Parse JSON
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]
        
        return json.loads(result_text.strip())
        
    except Exception as e:
        return {'found': False, 'error': str(e)}


def estimate_base_value(year: int = None, publisher: str = None) -> float:
    """
    Estimate a base value when we have no data
    Very rough heuristic - better than nothing
    """
    base = 5.0  # Default for unknown modern comics
    
    if year:
        if year < 1960:
            base = 100.0  # Golden/early Silver Age
        elif year < 1975:
            base = 30.0   # Silver Age
        elif year < 1985:
            base = 15.0   # Bronze Age
        elif year < 1995:
            base = 8.0    # Copper Age
        else:
            base = 5.0    # Modern
    
    # Publisher adjustment
    if publisher:
        pub_lower = publisher.lower()
        if "marvel" in pub_lower or "dc" in pub_lower:
            base *= 1.0
        elif "image" in pub_lower:
            base *= 0.8
        else:
            base *= 0.6
    
    return base


class CollectionCalcHandler(BaseHTTPRequestHandler):
    """Enhanced HTTP request handler"""
    
    def _send_response(self, data, status=200):
        """Send JSON response with CORS headers"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        
        if path == '/api/stats':
            # Session stats + feedback summary
            feedback_count = feedback_logger.get_feedback_count()
            response = {
                **stats,
                'feedback_count': feedback_count,
                'model_version': valuation_model.weights.get('version', '1.0.0'),
                'weights_updated': valuation_model.weights.get('last_updated')
            }
            self._send_response(response)
        
        elif path == '/api/search':
            # Search for titles
            q = query.get('q', [''])[0]
            limit = int(query.get('limit', ['10'])[0])
            results = search_titles(q, limit=limit)
            self._send_response({'results': results})
        
        elif path == '/api/grades':
            # Get all grade multipliers
            grades = valuation_model.weights['grade_multipliers']
            self._send_response({'grades': grades})
        
        elif path == '/api/editions':
            # Get all edition multipliers
            editions = valuation_model.weights['edition_multipliers']
            self._send_response({'editions': editions})
        
        elif path == '/api/feedback/summary':
            # Get feedback analysis summary
            report = feedback_logger.generate_report()
            self._send_response(report)
        
        elif path == '/api/feedback/suggestions':
            # Get suggested weight adjustments
            min_samples = int(query.get('min_samples', ['5'])[0])
            suggestions = feedback_logger.get_suggested_adjustments(min_samples)
            self._send_response(suggestions)
        
        else:
            self._send_response({'error': 'Not found'}, 404)
    
    def do_POST(self):
        """Handle POST requests"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode()
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_response({'error': 'Invalid JSON'}, 400)
            return
        
        if path == '/api/valuate':
            # NEW: Get full valuation with breakdown
            result = get_valuation_with_breakdown(
                title=data.get('title', ''),
                issue=data.get('issue', ''),
                grade=data.get('grade', 'NM'),
                edition=data.get('edition', 'direct'),
                publisher=data.get('publisher'),
                year=data.get('year'),
                cgc=data.get('cgc', False),
                signatures=data.get('signatures'),
                use_web_fallback=data.get('use_web_fallback', True)
            )
            self._send_response(result)
        
        elif path == '/api/valuate/batch':
            # Batch valuation
            comics = data.get('comics', [])
            use_web_fallback = data.get('use_web_fallback', False)
            
            results = []
            for comic in comics:
                result = get_valuation_with_breakdown(
                    title=comic.get('title', ''),
                    issue=comic.get('issue', ''),
                    grade=comic.get('grade', 'NM'),
                    edition=comic.get('edition', 'direct'),
                    publisher=comic.get('publisher'),
                    year=comic.get('year'),
                    cgc=comic.get('cgc', False),
                    signatures=comic.get('signatures'),
                    use_web_fallback=use_web_fallback
                )
                results.append(result)
            
            self._send_response({
                'results': results,
                'count': len(results)
            })
        
        elif path == '/api/feedback':
            # Log a user correction
            try:
                entry = feedback_logger.log_correction(
                    comic_title=data.get('title', ''),
                    issue_number=data.get('issue', ''),
                    model_predicted=data.get('model_predicted', 0),
                    user_corrected=data.get('user_corrected', 0),
                    grade=data.get('grade', 'NM'),
                    edition=data.get('edition', 'direct'),
                    publisher=data.get('publisher', 'Unknown'),
                    year=data.get('year'),
                    cgc=data.get('cgc', False),
                    base_nm_value=data.get('base_nm_value', 0),
                    confidence_score=data.get('confidence_score', 0),
                    base_value_source=data.get('base_value_source', 'unknown'),
                    user_notes=data.get('notes')
                )
                
                stats['corrections_logged'] += 1
                
                self._send_response({
                    'success': True,
                    'delta': entry.delta,
                    'delta_percent': entry.delta_percent,
                    'message': f'Logged correction: {entry.delta_percent:+.1f}%'
                })
                
            except Exception as e:
                self._send_response({'error': str(e)}, 500)
        
        elif path == '/api/weights/adjust':
            # Manually adjust a weight
            category = data.get('category')
            key = data.get('key')
            value = data.get('value')
            
            if not all([category, key, value is not None]):
                self._send_response({'error': 'Missing category, key, or value'}, 400)
                return
            
            valuation_model.adjust_weight(category, key, value)
            
            if data.get('save', False):
                valuation_model.save_weights()
            
            self._send_response({
                'success': True,
                'category': category,
                'key': key,
                'new_value': value
            })
        
        elif path == '/api/weights/apply-suggestions':
            # Apply suggestions from feedback
            from feedback_logger import apply_suggestions_to_model
            
            min_samples = data.get('min_samples', 10)
            auto_save = data.get('save', False)
            
            apply_suggestions_to_model(
                feedback_logger, 
                valuation_model,
                min_samples=min_samples,
                auto_save=auto_save
            )
            
            self._send_response({
                'success': True,
                'message': 'Applied suggested adjustments',
                'saved': auto_save
            })
        
        elif path == '/api/lookup':
            # Legacy: Simple database lookup (backwards compatible)
            stats['db_lookups'] += 1
            
            result = lookup_comic(
                title=data.get('title', ''),
                issue=data.get('issue', ''),
                publisher=data.get('publisher'),
                year=data.get('year'),
                grade=data.get('grade', 'NM'),
                edition=data.get('edition', 'direct'),
                cgc=data.get('cgc', False)
            )
            
            if result['found']:
                stats['db_hits'] += 1
            
            self._send_response(result)
        
        elif path == '/api/anthropic':
            # Proxy to Anthropic API (for photo extraction)
            if not ANTHROPIC_AVAILABLE or not ANTHROPIC_API_KEY:
                self._send_response({'error': 'Anthropic API not available'}, 503)
                return
            
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            
            try:
                response = client.messages.create(**data)
                
                stats['total_tokens'] += response.usage.input_tokens + response.usage.output_tokens
                
                response_data = {
                    'id': response.id,
                    'type': response.type,
                    'role': response.role,
                    'content': [
                        {'type': block.type, 'text': getattr(block, 'text', '')}
                        for block in response.content
                    ],
                    'usage': {
                        'input_tokens': response.usage.input_tokens,
                        'output_tokens': response.usage.output_tokens
                    }
                }
                self._send_response(response_data)
                
            except Exception as e:
                self._send_response({'error': str(e)}, 500)
        
        else:
            self._send_response({'error': 'Not found'}, 404)


def run_server():
    """Start the enhanced API server"""
    server = HTTPServer(('localhost', PORT), CollectionCalcHandler)
    
    print("=" * 60)
    print("CollectionCalc Enhanced API Server")
    print("=" * 60)
    print(f"\n🚀 Server running at http://localhost:{PORT}")
    
    print(f"\n📊 Valuation Endpoints:")
    print(f"  POST /api/valuate        - Get valuation with full breakdown")
    print(f"  POST /api/valuate/batch  - Batch valuation")
    print(f"  POST /api/lookup         - Simple database lookup")
    
    print(f"\n📝 Feedback Endpoints:")
    print(f"  POST /api/feedback       - Log a user correction")
    print(f"  GET  /api/feedback/summary      - Get feedback analysis")
    print(f"  GET  /api/feedback/suggestions  - Get weight suggestions")
    
    print(f"\n⚙️  Weight Management:")
    print(f"  GET  /api/grades         - Get grade multipliers")
    print(f"  GET  /api/editions       - Get edition multipliers")
    print(f"  POST /api/weights/adjust - Manually adjust a weight")
    print(f"  POST /api/weights/apply-suggestions - Apply feedback")
    
    print(f"\n📈 Stats:")
    print(f"  GET  /api/stats          - Session statistics")
    print(f"  GET  /api/search?q=      - Search comic titles")
    
    print(f"\nPress Ctrl+C to stop\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n📊 Session Summary:")
        print(f"   Valuations: {stats['valuations']}")
        print(f"   DB Lookups: {stats['db_lookups']}")
        print(f"   DB Hits: {stats['db_hits']} ({stats['db_hits']/max(stats['db_lookups'],1)*100:.1f}%)")
        print(f"   Web Searches: {stats['web_searches']}")
        print(f"   Corrections Logged: {stats['corrections_logged']}")
        print(f"   Total Tokens: {stats['total_tokens']:,}")
        print("\nServer stopped.")


if __name__ == "__main__":
    # Check for dependencies
    if not ANTHROPIC_AVAILABLE:
        print("⚠️  Warning: anthropic package not installed")
        print("   Web search fallback will not work")
        print("   Install with: pip install anthropic")
        print()
    elif not ANTHROPIC_API_KEY:
        print("⚠️  Warning: ANTHROPIC_API_KEY not set")
        print("   Web search fallback will not work")
        print("   Set it with: set ANTHROPIC_API_KEY=your-key-here")
        print()
    
    # Check for database
    if not os.path.exists(DB_PATH):
        print("⚠️  Database not found!")
        print("   Run 'python database_setup.py' first")
        print()
    
    run_server()
