"""
CollectionCalc - Combined API Server
Serves database lookups with web search fallback via Anthropic API

This replaces/extends your existing proxy-server.py
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import sqlite3
from urllib.parse import parse_qs, urlparse
import anthropic
from datetime import datetime

# Import our lookup module
from comic_lookup import lookup_comic, batch_lookup, normalize_title, normalize_issue

# Configuration
PORT = 8000
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
DB_PATH = "comics_pricing.db"

# Stats tracking
stats = {
    'db_lookups': 0,
    'db_hits': 0,
    'web_searches': 0,
    'total_tokens': 0,
    'session_start': datetime.now().isoformat()
}


def get_valuation_from_web_search(comic_data: dict) -> dict:
    """
    Fall back to web search when database doesn't have the comic
    Uses Anthropic API with web search tool
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    title = comic_data.get('title', '')
    issue = comic_data.get('issue', '')
    publisher = comic_data.get('publisher', '')
    year = comic_data.get('year', '')
    grade = comic_data.get('grade', 'NM')
    edition = comic_data.get('edition', 'direct')
    cgc = comic_data.get('cgc', False)
    
    # Build search query
    query = f"{title} #{issue}"
    if publisher:
        query += f" {publisher}"
    query += " comic book value price"
    
    prompt = f"""Search for the current market value of this comic book:
    
Title: {title}
Issue: #{issue}
Publisher: {publisher or 'Unknown'}
Year: {year or 'Unknown'}
Grade: {grade}
Edition: {edition}
CGC Graded: {'Yes' if cgc else 'No'}

Search for recent sold prices on eBay, price guide values from GoCollect, ComicsPriceGuide, or similar sources.

Return a JSON object with:
{{
    "estimated_value": <number>,
    "value_range_low": <number>,
    "value_range_high": <number>,
    "grade_value": <number for the specified grade>,
    "sources": ["source1", "source2"],
    "notes": "any relevant notes about this comic"
}}

Only return the JSON, no other text."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Track token usage
        stats['web_searches'] += 1
        stats['total_tokens'] += response.usage.input_tokens + response.usage.output_tokens
        
        # Extract the response
        result_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                result_text += block.text
        
        # Parse JSON from response
        # Try to extract JSON from the response
        json_match = result_text
        if "```json" in result_text:
            json_match = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            json_match = result_text.split("```")[1].split("```")[0]
        
        try:
            parsed = json.loads(json_match.strip())
            return {
                'found': True,
                'source': 'web_search',
                **parsed
            }
        except json.JSONDecodeError:
            # Return raw response if JSON parsing fails
            return {
                'found': True,
                'source': 'web_search',
                'estimated_value': None,
                'raw_response': result_text,
                'error': 'Could not parse structured response'
            }
            
    except Exception as e:
        return {
            'found': False,
            'source': 'web_search',
            'error': str(e)
        }


class CollectionCalcHandler(BaseHTTPRequestHandler):
    """HTTP request handler with CORS and routing"""
    
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
            # Return current session stats
            self._send_response(stats)
        
        elif path == '/api/search':
            # Search for titles in database
            q = query.get('q', [''])[0]
            from comic_lookup import search_titles
            results = search_titles(q)
            self._send_response({'results': results})
        
        elif path == '/api/grades':
            # Get all grade multipliers
            from comic_lookup import get_all_grades
            grades = get_all_grades()
            self._send_response({'grades': grades})
        
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
        
        if path == '/api/lookup':
            # Single comic lookup
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
            elif data.get('fallback_web_search', True):
                # Fall back to web search
                web_result = get_valuation_from_web_search(data)
                result.update(web_result)
                self._send_response(result)
            else:
                self._send_response(result)
        
        elif path == '/api/batch_lookup':
            # Batch lookup multiple comics
            comics = data.get('comics', [])
            use_web_fallback = data.get('fallback_web_search', False)
            
            stats['db_lookups'] += len(comics)
            
            batch_result = batch_lookup(comics)
            
            if use_web_fallback and batch_result['need_web_search_count'] > 0:
                # Run web searches for comics not in database
                # Note: This can be slow! Consider async/background processing
                for idx in batch_result['need_web_search_indices']:
                    comic = comics[idx]
                    web_result = get_valuation_from_web_search(comic)
                    batch_result['results'][idx].update(web_result)
            
            stats['db_hits'] += batch_result['found_count']
            self._send_response(batch_result)
        
        elif path == '/api/anthropic':
            # Proxy to Anthropic API (for photo extraction, etc.)
            # This maintains compatibility with your existing frontend
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            
            try:
                response = client.messages.create(**data)
                
                # Track tokens
                stats['total_tokens'] += response.usage.input_tokens + response.usage.output_tokens
                
                # Convert response to dict
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
    """Start the API server"""
    server = HTTPServer(('localhost', PORT), CollectionCalcHandler)
    
    print("=" * 50)
    print("CollectionCalc API Server")
    print("=" * 50)
    print(f"\n🚀 Server running at http://localhost:{PORT}")
    print(f"\nEndpoints:")
    print(f"  POST /api/lookup      - Single comic lookup (DB + web fallback)")
    print(f"  POST /api/batch_lookup - Batch comic lookup")
    print(f"  POST /api/anthropic   - Proxy to Anthropic API")
    print(f"  GET  /api/stats       - Session statistics")
    print(f"  GET  /api/search?q=   - Search titles in database")
    print(f"  GET  /api/grades      - Get grade multipliers")
    print(f"\nPress Ctrl+C to stop\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n📊 Session Stats:")
        print(f"   DB Lookups: {stats['db_lookups']}")
        print(f"   DB Hits: {stats['db_hits']} ({stats['db_hits']/max(stats['db_lookups'],1)*100:.1f}%)")
        print(f"   Web Searches: {stats['web_searches']}")
        print(f"   Total Tokens: {stats['total_tokens']:,}")
        print("\nServer stopped.")


if __name__ == "__main__":
    # Check for API key
    if not ANTHROPIC_API_KEY:
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
