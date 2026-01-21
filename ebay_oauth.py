"""
eBay OAuth Integration for CollectionCalc
Handles user authentication and token management for eBay API access.
"""

import os
import json
import base64
import requests
from datetime import datetime, timedelta
from urllib.parse import urlencode

# Try to import psycopg2 for PostgreSQL
try:
    import psycopg2
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

# eBay OAuth endpoints
EBAY_AUTH_URL = "https://auth.ebay.com/oauth2/authorize"
EBAY_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"

# Sandbox URLs (for testing)
EBAY_SANDBOX_AUTH_URL = "https://auth.sandbox.ebay.com/oauth2/authorize"
EBAY_SANDBOX_TOKEN_URL = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"

# Scopes we need for listing items
EBAY_SCOPES = [
    "https://api.ebay.com/oauth/api_scope",
    "https://api.ebay.com/oauth/api_scope/sell.inventory",
    "https://api.ebay.com/oauth/api_scope/sell.account",
    "https://api.ebay.com/oauth/api_scope/sell.fulfillment"
]

def get_db_connection():
    """Get PostgreSQL connection."""
    if not HAS_POSTGRES:
        return None
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return None
    
    try:
        conn = psycopg2.connect(database_url, sslmode='require')
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def init_ebay_tokens_table():
    """Create table for storing eBay OAuth tokens."""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ebay_tokens (
                id SERIAL PRIMARY KEY,
                user_id TEXT UNIQUE NOT NULL,
                access_token TEXT,
                refresh_token TEXT,
                token_expiry TIMESTAMP,
                ebay_username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating ebay_tokens table: {e}")
        try:
            conn.close()
        except:
            pass
        return False

def is_sandbox_mode() -> bool:
    """Check if we're using eBay sandbox environment."""
    return os.environ.get('EBAY_SANDBOX', '').lower() in ('true', '1', 'yes')

def get_auth_url(state: str = None, use_sandbox: bool = None) -> str:
    """
    Generate the eBay OAuth authorization URL.
    
    Args:
        state: Optional state parameter for CSRF protection
        use_sandbox: If True, use sandbox environment. If None, check EBAY_SANDBOX env var.
    
    Returns:
        URL to redirect user to for eBay authorization
    """
    if use_sandbox is None:
        use_sandbox = is_sandbox_mode()
    
    client_id = os.environ.get('EBAY_CLIENT_ID')
    runame = os.environ.get('EBAY_RUNAME')
    
    if not client_id or not runame:
        raise ValueError("EBAY_CLIENT_ID and EBAY_RUNAME must be set")
    
    base_url = EBAY_SANDBOX_AUTH_URL if use_sandbox else EBAY_AUTH_URL
    
    params = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': runame,
        'scope': ' '.join(EBAY_SCOPES)
    }
    
    if state:
        params['state'] = state
    
    return f"{base_url}?{urlencode(params)}"

def exchange_code_for_token(auth_code: str, use_sandbox: bool = None) -> dict:
    """
    Exchange authorization code for access token.
    
    Args:
        auth_code: The authorization code from eBay callback
        use_sandbox: If True, use sandbox environment. If None, check EBAY_SANDBOX env var.
    
    Returns:
        Dict with access_token, refresh_token, expires_in
    """
    if use_sandbox is None:
        use_sandbox = is_sandbox_mode()
    
    client_id = os.environ.get('EBAY_CLIENT_ID')
    client_secret = os.environ.get('EBAY_CLIENT_SECRET')
    runame = os.environ.get('EBAY_RUNAME')
    
    if not all([client_id, client_secret, runame]):
        raise ValueError("eBay credentials not configured")
    
    token_url = EBAY_SANDBOX_TOKEN_URL if use_sandbox else EBAY_TOKEN_URL
    
    # Create Basic auth header
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {encoded_credentials}'
    }
    
    data = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': runame
    }
    
    response = requests.post(token_url, headers=headers, data=data)
    
    if response.status_code != 200:
        print(f"eBay token exchange failed: {response.status_code} - {response.text}")
        raise Exception(f"Token exchange failed: {response.text}")
    
    return response.json()

def refresh_access_token(refresh_token: str, use_sandbox: bool = None) -> dict:
    """
    Refresh an expired access token.
    
    Args:
        refresh_token: The refresh token
        use_sandbox: If True, use sandbox environment. If None, check EBAY_SANDBOX env var.
    
    Returns:
        Dict with new access_token, expires_in
    """
    if use_sandbox is None:
        use_sandbox = is_sandbox_mode()
    
    client_id = os.environ.get('EBAY_CLIENT_ID')
    client_secret = os.environ.get('EBAY_CLIENT_SECRET')
    
    if not all([client_id, client_secret]):
        raise ValueError("eBay credentials not configured")
    
    token_url = EBAY_SANDBOX_TOKEN_URL if use_sandbox else EBAY_TOKEN_URL
    
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {encoded_credentials}'
    }
    
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'scope': ' '.join(EBAY_SCOPES)
    }
    
    response = requests.post(token_url, headers=headers, data=data)
    
    if response.status_code != 200:
        print(f"eBay token refresh failed: {response.status_code} - {response.text}")
        raise Exception(f"Token refresh failed: {response.text}")
    
    return response.json()

def save_user_token(user_id: str, token_data: dict) -> bool:
    """
    Save or update user's eBay tokens in database.
    
    Args:
        user_id: Unique identifier for the user (could be session ID for now)
        token_data: Dict with access_token, refresh_token, expires_in
    
    Returns:
        True if successful
    """
    init_ebay_tokens_table()
    
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Calculate expiry time
        expires_in = token_data.get('expires_in', 7200)  # Default 2 hours
        expiry_time = datetime.now() + timedelta(seconds=expires_in)
        
        cursor.execute('''
            INSERT INTO ebay_tokens (user_id, access_token, refresh_token, token_expiry, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id)
            DO UPDATE SET
                access_token = EXCLUDED.access_token,
                refresh_token = COALESCE(EXCLUDED.refresh_token, ebay_tokens.refresh_token),
                token_expiry = EXCLUDED.token_expiry,
                updated_at = EXCLUDED.updated_at
        ''', (
            user_id,
            token_data.get('access_token'),
            token_data.get('refresh_token'),
            expiry_time,
            datetime.now()
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving eBay token: {e}")
        try:
            conn.close()
        except:
            pass
        return False

def get_user_token(user_id: str) -> dict:
    """
    Get user's eBay access token, refreshing if expired.
    
    Args:
        user_id: Unique identifier for the user
    
    Returns:
        Dict with access_token, or None if not found/authenticated
    """
    init_ebay_tokens_table()
    
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT access_token, refresh_token, token_expiry
            FROM ebay_tokens
            WHERE user_id = %s
        ''', (user_id,))
        
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return None
        
        access_token, refresh_token, token_expiry = row
        
        # Check if token is expired (with 5 min buffer)
        if token_expiry and datetime.now() > (token_expiry - timedelta(minutes=5)):
            # Token expired, try to refresh
            if refresh_token:
                try:
                    new_token_data = refresh_access_token(refresh_token)
                    save_user_token(user_id, new_token_data)
                    return {'access_token': new_token_data.get('access_token')}
                except Exception as e:
                    print(f"Failed to refresh token: {e}")
                    return None
            else:
                return None
        
        return {'access_token': access_token}
    except Exception as e:
        print(f"Error getting eBay token: {e}")
        try:
            conn.close()
        except:
            pass
        return None

def is_user_connected(user_id: str) -> bool:
    """Check if user has a valid eBay connection."""
    token = get_user_token(user_id)
    return token is not None and token.get('access_token') is not None

def disconnect_user(user_id: str) -> bool:
    """Remove user's eBay connection."""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM ebay_tokens WHERE user_id = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error disconnecting user: {e}")
        try:
            conn.close()
        except:
            pass
        return False


# ============================================================
# GDPR / Account Deletion Support
# ============================================================

def save_ebay_user_id(user_id: str, ebay_user_id: str) -> bool:
    """
    Save eBay's user ID (from their system) to our database.
    Called after successful OAuth to link our user_id with eBay's user ID.
    
    Args:
        user_id: Our internal user identifier
        ebay_user_id: eBay's user ID (from token response or API)
    
    Returns:
        True if successful
    """
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE ebay_tokens 
            SET ebay_username = %s, updated_at = %s
            WHERE user_id = %s
        ''', (ebay_user_id, datetime.now(), user_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving eBay user ID: {e}")
        try:
            conn.close()
        except:
            pass
        return False


def delete_user_by_ebay_id(ebay_user_id: str) -> bool:
    """
    Delete user tokens by eBay's user ID.
    Called when eBay sends account deletion notification (GDPR compliance).
    
    Args:
        ebay_user_id: eBay's user ID from the deletion notification
    
    Returns:
        True if user was found and deleted, False otherwise
    """
    conn = get_db_connection()
    if not conn:
        print("No database connection for deletion")
        return False
    
    try:
        cursor = conn.cursor()
        
        # First check if user exists
        cursor.execute('SELECT user_id FROM ebay_tokens WHERE ebay_username = %s', (ebay_user_id,))
        row = cursor.fetchone()
        
        if not row:
            print(f"No user found with eBay ID: {ebay_user_id}")
            cursor.close()
            conn.close()
            return False
        
        # Delete the user's tokens
        cursor.execute('DELETE FROM ebay_tokens WHERE ebay_username = %s', (ebay_user_id,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"Deleted {deleted_count} token record(s) for eBay user: {ebay_user_id}")
        return deleted_count > 0
    except Exception as e:
        print(f"Error deleting user by eBay ID: {e}")
        try:
            conn.close()
        except:
            pass
        return False
