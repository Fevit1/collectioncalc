"""
Admin module for CollectionCalc.
Provides Natural Language Query (NLQ) interface for database exploration,
request logging, and analytics.

Uses Claude to convert natural language questions into SQL queries.
"""

import os
import json
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

# Optional: Anthropic for NLQ
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# ============================================
# DATABASE HELPERS
# ============================================

def get_db_connection():
    """Get database connection from environment."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)

# ============================================
# REQUEST LOGGING
# ============================================

def log_request(user_id, endpoint, method, status_code, response_time_ms, 
                error_message=None, request_size=None, response_size=None,
                user_agent=None, ip_address=None, device_type=None,
                request_data=None, response_summary=None):
    """
    Log an API request for analytics and debugging.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO request_logs (
                user_id, endpoint, method, status_code, response_time_ms,
                error_message, request_size_bytes, response_size_bytes,
                user_agent, ip_address, device_type, request_data, response_summary
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id, endpoint, method, status_code, response_time_ms,
            error_message, request_size, response_size,
            user_agent, ip_address, device_type,
            json.dumps(request_data) if request_data else None,
            response_summary
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error logging request: {e}")
    finally:
        cur.close()
        conn.close()

def log_api_usage(user_id, endpoint, model, input_tokens, output_tokens):
    """
    Log Anthropic API usage for cost tracking.
    """
    # Estimate cost based on model
    # Sonnet: $3/M input, $15/M output
    # Opus: $15/M input, $75/M output
    if 'opus' in model.lower():
        cost = (input_tokens * 15 / 1_000_000) + (output_tokens * 75 / 1_000_000)
    else:  # Sonnet
        cost = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO api_usage (user_id, endpoint, model, input_tokens, output_tokens, estimated_cost_usd)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, endpoint, model, input_tokens, output_tokens, cost))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error logging API usage: {e}")
    finally:
        cur.close()
        conn.close()

# ============================================
# ANALYTICS QUERIES
# ============================================

def get_dashboard_stats():
    """Get overview stats for admin dashboard."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        stats = {}
        
        # User stats
        cur.execute("""
            SELECT 
                COUNT(*) as total_users,
                COUNT(*) FILTER (WHERE is_approved = TRUE) as approved_users,
                COUNT(*) FILTER (WHERE is_approved = FALSE AND is_admin = FALSE) as pending_users,
                COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') as new_users_week,
                COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as new_users_today
            FROM users
        """)
        stats['users'] = dict(cur.fetchone())
        
        # Request stats (last 24 hours)
        cur.execute("""
            SELECT 
                COUNT(*) as total_requests,
                COUNT(*) FILTER (WHERE error_message IS NOT NULL) as failed_requests,
                AVG(response_time_ms) as avg_response_time,
                COUNT(DISTINCT user_id) as active_users
            FROM request_logs
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """)
        row = cur.fetchone()
        stats['requests_24h'] = {
            'total': row['total_requests'],
            'failed': row['failed_requests'],
            'avg_response_time_ms': round(row['avg_response_time'] or 0, 2),
            'active_users': row['active_users']
        }
        
        # API usage (current month)
        cur.execute("""
            SELECT 
                COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                COALESCE(SUM(estimated_cost_usd), 0) as total_cost,
                COUNT(*) as api_calls
            FROM api_usage
            WHERE created_at > DATE_TRUNC('month', CURRENT_DATE)
        """)
        row = cur.fetchone()
        stats['api_usage_month'] = {
            'input_tokens': int(row['total_input_tokens']),
            'output_tokens': int(row['total_output_tokens']),
            'estimated_cost_usd': round(float(row['total_cost']), 4),
            'api_calls': row['api_calls']
        }
        
        # Sales stats
        cur.execute("""
            SELECT 
                COUNT(*) as total_sales,
                COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as sales_today,
                COALESCE(AVG(price), 0) as avg_price
            FROM market_sales
        """)
        row = cur.fetchone()
        stats['sales'] = {
            'total': row['total_sales'],
            'today': row['sales_today'],
            'avg_price': round(float(row['avg_price']), 2)
        }
        
        # Beta codes
        cur.execute("""
            SELECT 
                COUNT(*) as total_codes,
                COUNT(*) FILTER (WHERE uses_remaining > 0 AND is_active = TRUE) as available_codes,
                COUNT(*) FILTER (WHERE uses_remaining = 0) as used_codes
            FROM beta_codes
        """)
        stats['beta_codes'] = dict(cur.fetchone())
        
        return stats
    finally:
        cur.close()
        conn.close()

def get_recent_errors(limit=20):
    """Get recent failed requests for debugging."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 
                rl.id, rl.endpoint, rl.method, rl.status_code, 
                rl.error_message, rl.response_time_ms, rl.device_type,
                rl.created_at, u.email as user_email
            FROM request_logs rl
            LEFT JOIN users u ON rl.user_id = u.id
            WHERE rl.error_message IS NOT NULL
            ORDER BY rl.created_at DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

def get_endpoint_stats(hours=24):
    """Get stats by endpoint for the last N hours."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 
                endpoint,
                COUNT(*) as total_calls,
                COUNT(*) FILTER (WHERE error_message IS NOT NULL) as errors,
                AVG(response_time_ms) as avg_time_ms,
                MAX(response_time_ms) as max_time_ms
            FROM request_logs
            WHERE created_at > NOW() - INTERVAL '%s hours'
            GROUP BY endpoint
            ORDER BY total_calls DESC
        """, (hours,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

def get_device_breakdown(hours=24):
    """Get request breakdown by device type."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 
                COALESCE(device_type, 'unknown') as device,
                COUNT(*) as requests,
                COUNT(*) FILTER (WHERE error_message IS NOT NULL) as errors
            FROM request_logs
            WHERE created_at > NOW() - INTERVAL '%s hours'
            GROUP BY device_type
            ORDER BY requests DESC
        """, (hours,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

# ============================================
# NATURAL LANGUAGE QUERY (NLQ)
# ============================================

# Database schema for Claude to understand
DB_SCHEMA = """
Tables in the CollectionCalc database:

1. users
   - id (SERIAL PRIMARY KEY)
   - email (TEXT UNIQUE)
   - password_hash (TEXT)
   - email_verified (BOOLEAN)
   - is_approved (BOOLEAN) - whether user can access the app
   - is_admin (BOOLEAN)
   - approved_at (TIMESTAMPTZ)
   - approved_by (INTEGER FK users.id)
   - beta_code_used (TEXT)
   - created_at (TIMESTAMPTZ)
   - updated_at (TIMESTAMPTZ)

2. beta_codes
   - id (SERIAL PRIMARY KEY)
   - code (TEXT UNIQUE)
   - created_by (INTEGER FK users.id)
   - uses_allowed (INTEGER)
   - uses_remaining (INTEGER)
   - expires_at (TIMESTAMPTZ)
   - note (TEXT)
   - is_active (BOOLEAN)
   - created_at (TIMESTAMPTZ)

3. request_logs
   - id (SERIAL PRIMARY KEY)
   - user_id (INTEGER FK users.id)
   - endpoint (TEXT)
   - method (TEXT)
   - status_code (INTEGER)
   - response_time_ms (INTEGER)
   - error_message (TEXT)
   - request_size_bytes (INTEGER)
   - response_size_bytes (INTEGER)
   - user_agent (TEXT)
   - ip_address (TEXT)
   - device_type (TEXT) - 'mobile', 'desktop', 'tablet'
   - request_data (JSONB)
   - response_summary (TEXT)
   - created_at (TIMESTAMPTZ)

4. api_usage
   - id (SERIAL PRIMARY KEY)
   - user_id (INTEGER FK users.id)
   - endpoint (TEXT)
   - model (TEXT) - 'claude-sonnet-4-20250514', etc.
   - input_tokens (INTEGER)
   - output_tokens (INTEGER)
   - estimated_cost_usd (NUMERIC)
   - created_at (TIMESTAMPTZ)

5. market_sales
   - id (SERIAL PRIMARY KEY)
   - source (TEXT) - 'whatnot', 'ebay_auction', 'ebay_bin'
   - title (TEXT)
   - series (TEXT)
   - issue (TEXT)
   - grade (NUMERIC)
   - grade_source (TEXT)
   - slab_type (TEXT)
   - variant (TEXT)
   - is_key (BOOLEAN)
   - price (NUMERIC)
   - sold_at (TIMESTAMPTZ)
   - created_at (TIMESTAMPTZ)
   - raw_title (TEXT)
   - seller (TEXT)
   - bids (INTEGER)
   - viewers (INTEGER)
   - image_url (TEXT)
   - source_id (TEXT)

6. collections
   - id (SERIAL PRIMARY KEY)
   - user_id (INTEGER FK users.id)
   - title (TEXT)
   - issue (TEXT)
   - grade (TEXT)
   - value (NUMERIC)
   - created_at (TIMESTAMPTZ)

7. search_cache
   - id (SERIAL PRIMARY KEY)
   - search_key (TEXT UNIQUE)
   - result (JSONB)
   - created_at (TIMESTAMPTZ)
   - expires_at (TIMESTAMPTZ)
"""

def natural_language_query(question, admin_id):
    """
    Convert a natural language question into SQL, execute it, and return results.
    
    Args:
        question: Natural language question like "How many users signed up this week?"
        admin_id: ID of the admin making the query
    
    Returns:
        dict with query, results, and metadata
    """
    if not ANTHROPIC_AVAILABLE or not ANTHROPIC_API_KEY:
        return {'success': False, 'error': 'Anthropic API not available for NLQ'}
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    prompt = f"""You are a SQL expert helping an admin query the CollectionCalc database.

{DB_SCHEMA}

The admin asks: "{question}"

Generate a PostgreSQL query to answer this question. 

IMPORTANT RULES:
1. Return ONLY the SQL query, no explanations
2. Use safe, read-only queries (SELECT only, no INSERT/UPDATE/DELETE)
3. Limit results to 100 rows maximum
4. Use proper date/time functions for PostgreSQL (NOW(), INTERVAL, DATE_TRUNC)
5. Format dates nicely in output
6. If the question is unclear, make reasonable assumptions
7. Join tables when needed to provide useful context (e.g., user emails)

Return ONLY the SQL query, nothing else."""

    try:
        start_time = time.time()
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        
        sql_query = response.content[0].text.strip()
        
        # Clean up the query (remove markdown code blocks if present)
        if sql_query.startswith("```"):
            sql_query = sql_query.split("```")[1]
            if sql_query.startswith("sql"):
                sql_query = sql_query[3:]
            sql_query = sql_query.strip()
        
        # Safety check - only allow SELECT statements
        sql_lower = sql_query.lower().strip()
        if not sql_lower.startswith('select'):
            return {
                'success': False, 
                'error': 'Only SELECT queries are allowed',
                'generated_sql': sql_query
            }
        
        # Check for dangerous keywords
        dangerous = ['insert', 'update', 'delete', 'drop', 'truncate', 'alter', 'create', 'grant', 'revoke']
        for word in dangerous:
            if word in sql_lower:
                return {
                    'success': False,
                    'error': f'Query contains forbidden keyword: {word}',
                    'generated_sql': sql_query
                }
        
        # Execute the query
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute(sql_query)
            results = cur.fetchall()
            execution_time = int((time.time() - start_time) * 1000)
            
            # Log the query for history
            cur.execute("""
                INSERT INTO admin_nlq_history (admin_id, natural_query, generated_sql, result_count, execution_time_ms)
                VALUES (%s, %s, %s, %s, %s)
            """, (admin_id, question, sql_query, len(results), execution_time))
            conn.commit()
            
            # Convert results to JSON-serializable format
            json_results = []
            for row in results:
                json_row = {}
                for key, value in row.items():
                    if isinstance(value, datetime):
                        json_row[key] = value.isoformat()
                    elif hasattr(value, '__float__'):
                        json_row[key] = float(value)
                    else:
                        json_row[key] = value
                json_results.append(json_row)
            
            return {
                'success': True,
                'question': question,
                'generated_sql': sql_query,
                'results': json_results,
                'result_count': len(results),
                'execution_time_ms': execution_time
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Query execution failed: {str(e)}',
                'generated_sql': sql_query
            }
        finally:
            cur.close()
            conn.close()
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Failed to generate query: {str(e)}'
        }

def get_nlq_history(admin_id=None, limit=20):
    """Get history of NLQ queries."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if admin_id:
            cur.execute("""
                SELECT h.*, u.email as admin_email
                FROM admin_nlq_history h
                LEFT JOIN users u ON h.admin_id = u.id
                WHERE h.admin_id = %s
                ORDER BY h.created_at DESC
                LIMIT %s
            """, (admin_id, limit))
        else:
            cur.execute("""
                SELECT h.*, u.email as admin_email
                FROM admin_nlq_history h
                LEFT JOIN users u ON h.admin_id = u.id
                ORDER BY h.created_at DESC
                LIMIT %s
            """, (limit,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

# ============================================
# ANTHROPIC USAGE STATS
# ============================================

def get_anthropic_usage_summary(days=30):
    """Get Anthropic API usage summary."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Daily breakdown
        cur.execute("""
            SELECT 
                DATE(created_at) as date,
                SUM(input_tokens) as input_tokens,
                SUM(output_tokens) as output_tokens,
                SUM(estimated_cost_usd) as cost,
                COUNT(*) as api_calls
            FROM api_usage
            WHERE created_at > NOW() - INTERVAL '%s days'
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """, (days,))
        daily = cur.fetchall()
        
        # By endpoint
        cur.execute("""
            SELECT 
                endpoint,
                SUM(input_tokens) as input_tokens,
                SUM(output_tokens) as output_tokens,
                SUM(estimated_cost_usd) as cost,
                COUNT(*) as api_calls
            FROM api_usage
            WHERE created_at > NOW() - INTERVAL '%s days'
            GROUP BY endpoint
            ORDER BY cost DESC
        """, (days,))
        by_endpoint = cur.fetchall()
        
        # By user (top 10)
        cur.execute("""
            SELECT 
                u.email,
                SUM(a.input_tokens) as input_tokens,
                SUM(a.output_tokens) as output_tokens,
                SUM(a.estimated_cost_usd) as cost,
                COUNT(*) as api_calls
            FROM api_usage a
            LEFT JOIN users u ON a.user_id = u.id
            WHERE a.created_at > NOW() - INTERVAL '%s days'
            GROUP BY u.email
            ORDER BY cost DESC
            LIMIT 10
        """, (days,))
        by_user = cur.fetchall()
        
        # Totals
        cur.execute("""
            SELECT 
                SUM(input_tokens) as total_input,
                SUM(output_tokens) as total_output,
                SUM(estimated_cost_usd) as total_cost,
                COUNT(*) as total_calls
            FROM api_usage
            WHERE created_at > NOW() - INTERVAL '%s days'
        """, (days,))
        totals = cur.fetchone()
        
        return {
            'period_days': days,
            'totals': {
                'input_tokens': int(totals['total_input'] or 0),
                'output_tokens': int(totals['total_output'] or 0),
                'cost_usd': round(float(totals['total_cost'] or 0), 4),
                'api_calls': totals['total_calls'] or 0
            },
            'daily': [dict(row) for row in daily],
            'by_endpoint': [dict(row) for row in by_endpoint],
            'by_user': [dict(row) for row in by_user]
        }
    finally:
        cur.close()
        conn.close()
