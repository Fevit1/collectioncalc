"""
CollectionCalc - API Server v3
Complete API with valuation, user management, and reporting

Endpoints:
- Valuation (single + batch)
- User adjustments (personal overrides)
- User management (exclusion, trust scores)
- Feedback logging and analysis
- Reporting and analytics
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
from user_adjustments import UserAdjustments
from reporting import ReportingEngine

# Optional: Anthropic for web search fallback
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Configuration
PORT = int(os.environ.get('PORT', 8000))
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
DB_PATH = "comics_pricing.db"

# Initialize components
valuation_model = ValuationModel()
feedback_logger = FeedbackLogger()
user_adjustments = UserAdjustments()
reporting_engine = ReportingEngine()

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


def get_excluded_user_ids():
    """Get list of excluded user IDs for filtering feedback"""
    excluded = user_adjustments.get_excluded_users()
    return [u['user_id'] for u in excluded]


def get_valuation_with_breakdown(
    title: str,
    issue: str,
    grade: str = "NM",
    edition: str = "direct",
    publisher: str = None,
    year: int = None,
    cgc: bool = False,
    signatures: list = None,
    user_id: str = None,
    use_web_fallback: bool = True
) -> dict:
    """
    Get comic valuation with full breakdown
    Applies user's personal adjustments if user_id provided
    """
    stats['valuations'] += 1
    stats['db_lookups'] += 1
    
    # Step 1: Database lookup
    db_result = lookup_comic(
        title=title,
        issue=issue,
        publisher=publisher,
        year=year,
        grade="NM"
    )
    
    base_value = None
    base_source = "unknown"
    key_issue_reason = None
    
    if db_result['found']:
        stats['db_hits'] += 1
        base_value = db_result['base_value']
        base_source = "database"
        
        if db_result.get('match_details', {}).get('key_issue'):
            key_issue_reason = db_result['match_details'].get('key_reason')
    
    # Step 2: Web search fallback
    elif use_web_fallback and ANTHROPIC_AVAILABLE and ANTHROPIC_API_KEY:
        web_result = get_base_value_from_web(title, issue, publisher, year)
        if web_result.get('found'):
            base_value = web_result.get('nm_value', 0)
            base_source = "web_search"
            stats['web_searches'] += 1
    
    # Step 3: Estimate if no data
    if base_value is None:
        base_value = estimate_base_value(year, publisher)
        base_source = "estimated"
    
    # Step 4: Get effective weights (global + user overrides)
    if user_id:
        effective_weights = user_adjustments.get_effective_weights(
            user_id, 
            valuation_model.weights
        )
        # Temporarily use user's weights
        original_weights = valuation_model.weights
        valuation_model.weights = effective_weights
    
    # Step 5: Calculate valuation
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
        grade_source="verified" if cgc else "estimated"
    )
    
    # Restore original weights
    if user_id:
        valuation_model.weights = original_weights
    
    result = valuation_model.to_dict(breakdown)
    
    result['lookup'] = {
        'title_matched': db_result.get('title', title),
        'issue_matched': db_result.get('issue', issue),
        'publisher_matched': db_result.get('publisher', publisher),
        'db_found': db_result['found'],
        'db_confidence': db_result.get('confidence', 0)
    }
    
    if user_id:
        result['user_adjustments_applied'] = True
        result['user_id'] = user_id
    
    return result


def get_base_value_from_web(title: str, issue: str, publisher: str = None, year: int = None) -> dict:
    """Get base NM value from web search"""
    if not ANTHROPIC_AVAILABLE or not ANTHROPIC_API_KEY:
        return {'found': False, 'error': 'Anthropic API not available'}
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    prompt = f"""Find the Near Mint (NM/9.4) value for this comic:
Title: {title}
Issue: #{issue}
Publisher: {publisher or 'Unknown'}
Year: {year or 'Unknown'}

Search for price guide values. Return ONLY JSON:
{{"found": true, "nm_value": <number>, "source": "<source>"}}
or {{"found": false, "reason": "<why>"}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}]
        )
        
        stats['total_tokens'] += response.usage.input_tokens + response.usage.output_tokens
        
        result_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                result_text += block.text
        
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]
        
        return json.loads(result_text.strip())
        
    except Exception as e:
        return {'found': False, 'error': str(e)}


def estimate_base_value(year: int = None, publisher: str = None) -> float:
    """Estimate base value when no data available"""
    base = 5.0
    
    if year:
        if year < 1960:
            base = 100.0
        elif year < 1975:
            base = 30.0
        elif year < 1985:
            base = 15.0
        elif year < 1995:
            base = 8.0
    
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
    """Complete API handler"""
    
    def _send_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-User-ID')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-User-ID')
        self.end_headers()
    
    def _get_user_id(self):
        """Extract user ID from headers"""
        return self.headers.get('X-User-ID')
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        user_id = self._get_user_id()
        
        # ==================== STATS ====================
        if path == '/api/stats':
            feedback_count = feedback_logger.get_feedback_count()
            response = {
                **stats,
                'feedback_count': feedback_count,
                'model_version': valuation_model.weights.get('version', '1.0.0'),
                'weights_updated': valuation_model.weights.get('last_updated')
            }
            self._send_response(response)
        
        # ==================== SEARCH ====================
        elif path == '/api/search':
            q = query.get('q', [''])[0]
            limit = int(query.get('limit', ['10'])[0])
            results = search_titles(q, limit=limit)
            self._send_response({'results': results})
        
        # ==================== WEIGHTS ====================
        elif path == '/api/grades':
            grades = valuation_model.weights['grade_multipliers']
            self._send_response({'grades': grades})
        
        elif path == '/api/editions':
            editions = valuation_model.weights['edition_multipliers']
            self._send_response({'editions': editions})
        
        # ==================== USER ADJUSTMENTS ====================
        elif path == '/api/user/adjustments':
            if not user_id:
                self._send_response({'error': 'X-User-ID header required'}, 400)
                return
            adjustments = user_adjustments.get_user_adjustments(user_id)
            self._send_response({'user_id': user_id, 'adjustments': adjustments})
        
        elif path == '/api/user/profile':
            if not user_id:
                self._send_response({'error': 'X-User-ID header required'}, 400)
                return
            profile = user_adjustments.get_user_stats(user_id)
            self._send_response(profile or {'error': 'User not found'})
        
        # ==================== ADMIN: USER MANAGEMENT ====================
        elif path == '/api/admin/users':
            include_excluded = query.get('include_excluded', ['true'])[0].lower() == 'true'
            users = user_adjustments.get_all_users(include_excluded)
            self._send_response({'users': users, 'count': len(users)})
        
        elif path == '/api/admin/users/excluded':
            excluded = user_adjustments.get_excluded_users()
            self._send_response({'excluded_users': excluded, 'count': len(excluded)})
        
        # ==================== FEEDBACK ====================
        elif path == '/api/feedback/suggestions':
            min_samples = int(query.get('min_samples', ['5'])[0])
            exclude_flagged = query.get('exclude_flagged', ['true'])[0].lower() == 'true'
            
            excluded_ids = get_excluded_user_ids() if exclude_flagged else []
            suggestions = feedback_logger.get_suggested_adjustments(
                min_samples=min_samples,
                excluded_user_ids=excluded_ids
            )
            self._send_response(suggestions)
        
        elif path == '/api/feedback/all':
            limit = int(query.get('limit', ['100'])[0])
            feedback = feedback_logger.get_all_feedback()[:limit]
            self._send_response({'feedback': feedback, 'count': len(feedback)})
        
        # ==================== REPORTS ====================
        elif path == '/api/reports/accuracy':
            report = reporting_engine.accuracy_overview()
            self._send_response(report)
        
        elif path == '/api/reports/grades':
            min_samples = int(query.get('min_samples', ['3'])[0])
            report = reporting_engine.grade_analysis(min_samples)
            self._send_response(report)
        
        elif path == '/api/reports/editions':
            min_samples = int(query.get('min_samples', ['3'])[0])
            report = reporting_engine.edition_analysis(min_samples)
            self._send_response(report)
        
        elif path == '/api/reports/publishers':
            min_samples = int(query.get('min_samples', ['3'])[0])
            report = reporting_engine.publisher_analysis(min_samples)
            self._send_response(report)
        
        elif path == '/api/reports/users':
            report = reporting_engine.user_contribution_report()
            self._send_response(report)
        
        elif path == '/api/reports/outliers':
            threshold = float(query.get('threshold', ['50'])[0])
            report = reporting_engine.outlier_report(threshold)
            self._send_response(report)
        
        elif path == '/api/reports/trends':
            days = int(query.get('days', ['30'])[0])
            report = reporting_engine.time_series_report(days)
            self._send_response(report)
        
        elif path == '/api/reports/dashboard':
            report = reporting_engine.generate_dashboard()
            self._send_response(report)
        
        # ==================== HEALTH ====================
        elif path == '/api/health':
            self._send_response({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'version': '3.0.0'
            })
        
        else:
            self._send_response({'error': 'Not found'}, 404)
    
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        user_id = self._get_user_id()
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode()
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_response({'error': 'Invalid JSON'}, 400)
            return
        
        # ==================== VALUATION ====================
        if path == '/api/valuate':
            result = get_valuation_with_breakdown(
                title=data.get('title', ''),
                issue=data.get('issue', ''),
                grade=data.get('grade', 'NM'),
                edition=data.get('edition', 'direct'),
                publisher=data.get('publisher'),
                year=data.get('year'),
                cgc=data.get('cgc', False),
                signatures=data.get('signatures'),
                user_id=user_id or data.get('user_id'),
                use_web_fallback=data.get('use_web_fallback', True)
            )
            self._send_response(result)
        
        elif path == '/api/valuate/batch':
            comics = data.get('comics', [])
            use_web_fallback = data.get('use_web_fallback', False)
            batch_user_id = user_id or data.get('user_id')
            
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
                    user_id=batch_user_id,
                    use_web_fallback=use_web_fallback
                )
                results.append(result)
            
            self._send_response({'results': results, 'count': len(results)})
        
        # ==================== FEEDBACK ====================
        elif path == '/api/feedback':
            feedback_user_id = user_id or data.get('user_id')
            
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
                user_notes=data.get('notes'),
                user_id=feedback_user_id
            )
            
            # Update user's correction count
            if feedback_user_id:
                user_adjustments.increment_correction_count(feedback_user_id)
            
            stats['corrections_logged'] += 1
            
            self._send_response({
                'success': True,
                'delta': entry.delta,
                'delta_percent': entry.delta_percent,
                'message': f'Logged correction: {entry.delta_percent:+.1f}%'
            })
        
        # ==================== USER ADJUSTMENTS ====================
        elif path == '/api/user/adjustments':
            if not user_id:
                user_id = data.get('user_id')
            if not user_id:
                self._send_response({'error': 'user_id required'}, 400)
                return
            
            category = data.get('category')
            key = data.get('key')
            value = data.get('value')
            reason = data.get('reason')
            
            if not all([category, key, value is not None]):
                self._send_response({'error': 'category, key, and value required'}, 400)
                return
            
            result = user_adjustments.set_adjustment(user_id, category, key, value, reason)
            self._send_response({'success': True, **result})
        
        elif path == '/api/user/adjustments/reset':
            if not user_id:
                user_id = data.get('user_id')
            if not user_id:
                self._send_response({'error': 'user_id required'}, 400)
                return
            
            deleted = user_adjustments.clear_all_adjustments(user_id)
            self._send_response({'success': True, 'adjustments_cleared': deleted})
        
        # ==================== ADMIN: USER MANAGEMENT ====================
        elif path == '/api/admin/users/exclude':
            target_user_id = data.get('user_id')
            reason = data.get('reason', 'No reason provided')
            
            if not target_user_id:
                self._send_response({'error': 'user_id required'}, 400)
                return
            
            user_adjustments.exclude_user(target_user_id, reason)
            self._send_response({
                'success': True,
                'user_id': target_user_id,
                'action': 'excluded',
                'reason': reason
            })
        
        elif path == '/api/admin/users/include':
            target_user_id = data.get('user_id')
            
            if not target_user_id:
                self._send_response({'error': 'user_id required'}, 400)
                return
            
            user_adjustments.include_user(target_user_id)
            self._send_response({
                'success': True,
                'user_id': target_user_id,
                'action': 'included'
            })
        
        elif path == '/api/admin/users/trust':
            target_user_id = data.get('user_id')
            score = data.get('trust_score')
            notes = data.get('notes')
            
            if not target_user_id or score is None:
                self._send_response({'error': 'user_id and trust_score required'}, 400)
                return
            
            user_adjustments.set_trust_score(target_user_id, score, notes)
            self._send_response({
                'success': True,
                'user_id': target_user_id,
                'trust_score': score
            })
        
        # ==================== ADMIN: WEIGHTS ====================
        elif path == '/api/admin/weights/adjust':
            category = data.get('category')
            key = data.get('key')
            value = data.get('value')
            
            if not all([category, key, value is not None]):
                self._send_response({'error': 'category, key, and value required'}, 400)
                return
            
            valuation_model.adjust_weight(category, key, value)
            
            if data.get('save', False):
                valuation_model.save_weights()
            
            self._send_response({
                'success': True,
                'category': category,
                'key': key,
                'new_value': value,
                'saved': data.get('save', False)
            })
        
        elif path == '/api/admin/weights/apply-suggestions':
            from feedback_logger import apply_suggestions_to_model
            
            min_samples = data.get('min_samples', 10)
            auto_save = data.get('save', False)
            exclude_flagged = data.get('exclude_flagged', True)
            
            # Get excluded users if needed
            if exclude_flagged:
                excluded_ids = get_excluded_user_ids()
            else:
                excluded_ids = []
            
            apply_suggestions_to_model(
                feedback_logger,
                valuation_model,
                min_samples=min_samples,
                auto_save=auto_save
            )
            
            self._send_response({
                'success': True,
                'message': 'Applied suggested adjustments',
                'saved': auto_save,
                'excluded_users': len(excluded_ids)
            })
        
        elif path == '/api/admin/weights/save':
            valuation_model.save_weights()
            self._send_response({
                'success': True,
                'message': 'Weights saved',
                'version': valuation_model.weights.get('version')
            })
        
        # ==================== LEGACY ====================
        elif path == '/api/lookup':
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
    
    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        user_id = self._get_user_id()
        
        # Delete specific adjustment
        if path.startswith('/api/user/adjustments/'):
            if not user_id:
                self._send_response({'error': 'X-User-ID header required'}, 400)
                return
            
            parts = path.split('/')
            if len(parts) >= 5:
                category = parts[4]
                key = parts[5] if len(parts) > 5 else None
                
                if key:
                    deleted = user_adjustments.delete_adjustment(user_id, category, key)
                    self._send_response({
                        'success': deleted,
                        'message': f'Deleted {category}.{key}' if deleted else 'Not found'
                    })
                else:
                    self._send_response({'error': 'key required'}, 400)
            else:
                self._send_response({'error': 'Invalid path'}, 400)
        else:
            self._send_response({'error': 'Not found'}, 404)


def run_server():
    server = HTTPServer(('0.0.0.0', PORT), CollectionCalcHandler)
    
    print("=" * 60)
    print("CollectionCalc API Server v3")
    print("=" * 60)
    print(f"\n🚀 Server running at http://localhost:{PORT}")
    
    print(f"\n📊 VALUATION")
    print(f"  POST /api/valuate         - Single comic valuation")
    print(f"  POST /api/valuate/batch   - Batch valuation")
    
    print(f"\n👤 USER ADJUSTMENTS")
    print(f"  GET  /api/user/adjustments      - Get personal overrides")
    print(f"  POST /api/user/adjustments      - Set personal override")
    print(f"  POST /api/user/adjustments/reset - Clear all overrides")
    print(f"  DEL  /api/user/adjustments/:cat/:key - Delete override")
    
    print(f"\n📝 FEEDBACK")
    print(f"  POST /api/feedback              - Log correction")
    print(f"  GET  /api/feedback/suggestions  - Get weight suggestions")
    print(f"  GET  /api/feedback/all          - View all feedback")
    
    print(f"\n📈 REPORTS")
    print(f"  GET /api/reports/accuracy    - Accuracy overview")
    print(f"  GET /api/reports/grades      - Grade analysis")
    print(f"  GET /api/reports/users       - User contributions")
    print(f"  GET /api/reports/outliers    - Outlier detection")
    print(f"  GET /api/reports/dashboard   - Full dashboard")
    
    print(f"\n🔧 ADMIN")
    print(f"  GET  /api/admin/users           - List all users")
    print(f"  POST /api/admin/users/exclude   - Exclude user")
    print(f"  POST /api/admin/users/include   - Include user")
    print(f"  POST /api/admin/users/trust     - Set trust score")
    print(f"  POST /api/admin/weights/adjust  - Adjust weight")
    print(f"  POST /api/admin/weights/apply-suggestions")
    
    print(f"\nPress Ctrl+C to stop\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n📊 Session Summary:")
        print(f"   Valuations: {stats['valuations']}")
        print(f"   DB Hits: {stats['db_hits']}/{stats['db_lookups']}")
        print(f"   Web Searches: {stats['web_searches']}")
        print(f"   Corrections: {stats['corrections_logged']}")
        print("\nServer stopped.")


if __name__ == "__main__":
    if not ANTHROPIC_AVAILABLE:
        print("⚠️  anthropic package not installed - web fallback disabled")
    elif not ANTHROPIC_API_KEY:
        print("⚠️  ANTHROPIC_API_KEY not set - web fallback disabled")
    
    if not os.path.exists(DB_PATH):
        print("⚠️  Database not found - run database_setup.py first")
    
    run_server()
