"""
Content Moderation module for Slab Worthy.
Uses Amazon Rekognition to detect inappropriate content in uploaded images.

Checks run BEFORE any image is stored or processed.
Flags: explicit nudity, violence, drugs, hate symbols, etc.

Setup:
    - AWS IAM user with AmazonRekognitionReadOnlyAccess policy
    - Env vars: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
"""

import os
import base64
import json
from datetime import datetime

# ============================================
# CONFIGURATION
# ============================================

AWS_REGION = os.environ.get('AWS_REGION', 'us-west-2')
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')

# Minimum confidence threshold for flagging (0-100)
# 80 = reasonable balance between catching bad content and false positives
MODERATION_CONFIDENCE_THRESHOLD = 80

# Categories we block entirely (even comic covers can be suggestive, so we
# focus on the most severe categories)
BLOCKED_CATEGORIES = {
    'Explicit Nudity',
    'Non-Explicit Nudity of Intimate parts and Coverage',
    'Graphic Violence',
    'Drugs & Tobacco: Drug Products',
    'Drugs & Tobacco: Drug Use',
    'Hate Symbols',
    'Sexual Activity',
    'Animated Explicit Nudity',
}

# Categories we log but don't block (comics may trigger these)
# These get logged for review but don't stop the upload
WARNING_CATEGORIES = {
    'Suggestive',
    'Violence',
    'Visually Disturbing',
    'Drugs & Tobacco: Tobacco Products',
}

# Initialize boto3 client
rekognition_client = None

try:
    import boto3
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        rekognition_client = boto3.client(
            'rekognition',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        print(f"[MODERATION] Rekognition client initialized (region: {AWS_REGION})")
    else:
        print("[MODERATION] AWS credentials not set - moderation disabled")
except ImportError:
    print("[MODERATION] boto3 not installed - moderation disabled")
except Exception as e:
    print(f"[MODERATION] Failed to initialize Rekognition: {e}")

MODERATION_AVAILABLE = rekognition_client is not None


# ============================================
# CORE MODERATION FUNCTION
# ============================================

def moderate_image(image_base64):
    """
    Check an image for inappropriate content using AWS Rekognition.
    
    Args:
        image_base64: Base64-encoded image string (with or without data URI prefix)
    
    Returns:
        dict with:
            - allowed (bool): True if image passes moderation
            - blocked (bool): True if image was blocked
            - reason (str): Why it was blocked (if blocked)
            - labels (list): All detected moderation labels
            - warnings (list): Non-blocking labels that were detected
    """
    if not MODERATION_AVAILABLE:
        # If moderation isn't configured, allow but log warning
        print("[MODERATION] WARNING: Moderation not available, allowing image through")
        return {
            'allowed': True,
            'blocked': False,
            'reason': None,
            'labels': [],
            'warnings': ['Moderation not configured']
        }
    
    try:
        # Strip data URI prefix if present
        image_data = image_base64
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decode base64 to bytes
        image_bytes = base64.b64decode(image_data)
        
        # Call Rekognition
        response = rekognition_client.detect_moderation_labels(
            Image={'Bytes': image_bytes},
            MinConfidence=MODERATION_CONFIDENCE_THRESHOLD
        )
        
        labels = response.get('ModerationLabels', [])
        
        # Check for blocked categories
        blocked_labels = []
        warning_labels = []
        
        for label in labels:
            label_name = label.get('Name', '')
            parent_name = label.get('ParentName', '')
            confidence = label.get('Confidence', 0)
            
            # Build full category path for matching
            full_name = f"{parent_name}: {label_name}" if parent_name else label_name
            
            # Check if this label or its parent is in blocked list
            if (label_name in BLOCKED_CATEGORIES or 
                parent_name in BLOCKED_CATEGORIES or
                full_name in BLOCKED_CATEGORIES):
                blocked_labels.append({
                    'name': label_name,
                    'parent': parent_name,
                    'confidence': round(confidence, 1)
                })
            elif (label_name in WARNING_CATEGORIES or
                  parent_name in WARNING_CATEGORIES):
                warning_labels.append({
                    'name': label_name,
                    'parent': parent_name,
                    'confidence': round(confidence, 1)
                })
        
        if blocked_labels:
            # Image is blocked
            primary_reason = blocked_labels[0]['name']
            print(f"[MODERATION] BLOCKED: {primary_reason} (confidence: {blocked_labels[0]['confidence']}%)")
            return {
                'allowed': False,
                'blocked': True,
                'reason': f'Image contains inappropriate content ({primary_reason})',
                'labels': blocked_labels,
                'warnings': warning_labels
            }
        
        if warning_labels:
            print(f"[MODERATION] WARNING (allowed): {[w['name'] for w in warning_labels]}")
        
        return {
            'allowed': True,
            'blocked': False,
            'reason': None,
            'labels': blocked_labels,
            'warnings': warning_labels
        }
        
    except Exception as e:
        # If Rekognition fails, log error but allow the image through
        # We don't want a Rekognition outage to break the entire app
        print(f"[MODERATION] ERROR: {e}")
        return {
            'allowed': True,
            'blocked': False,
            'reason': None,
            'labels': [],
            'warnings': [f'Moderation check failed: {str(e)}']
        }


# ============================================
# DATABASE LOGGING
# ============================================

def log_moderation_incident(user_id, endpoint, result, image_hash=None):
    """
    Log a moderation event to the database.
    Only logs blocked images and warnings (not clean passes).
    
    Args:
        user_id: The user who uploaded the image
        endpoint: Which API endpoint was used
        result: The moderation result dict from moderate_image()
        image_hash: Optional SHA256 hash of the image (for dedup, NOT the image itself)
    """
    if not result.get('blocked') and not result.get('warnings'):
        return  # Don't log clean images
    
    try:
        import psycopg2
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            return
        
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO content_incidents 
                (user_id, endpoint, was_blocked, reason, labels, image_hash, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (
            user_id,
            endpoint,
            result.get('blocked', False),
            result.get('reason'),
            json.dumps(result.get('labels', []) + result.get('warnings', [])),
            image_hash
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        if result.get('blocked'):
            print(f"[MODERATION] Incident logged: user={user_id}, endpoint={endpoint}, reason={result.get('reason')}")
    
    except Exception as e:
        print(f"[MODERATION] Failed to log incident: {e}")


def get_image_hash(image_base64):
    """Generate a SHA256 hash of the image for logging (not the image itself)."""
    import hashlib
    if ',' in image_base64:
        image_base64 = image_base64.split(',')[1]
    return hashlib.sha256(image_base64.encode()).hexdigest()[:16]


# ============================================
# ADMIN HELPERS
# ============================================

def get_moderation_incidents(limit=50, blocked_only=False):
    """
    Get recent moderation incidents (admin only).
    Returns list of incidents for the admin dashboard.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        database_url = os.environ.get('DATABASE_URL')
        
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        if blocked_only:
            cur.execute("""
                SELECT ci.*, u.email
                FROM content_incidents ci
                LEFT JOIN users u ON ci.user_id = u.id
                WHERE ci.was_blocked = TRUE
                ORDER BY ci.created_at DESC
                LIMIT %s
            """, (limit,))
        else:
            cur.execute("""
                SELECT ci.*, u.email
                FROM content_incidents ci
                LEFT JOIN users u ON ci.user_id = u.id
                ORDER BY ci.created_at DESC
                LIMIT %s
            """, (limit,))
        
        incidents = cur.fetchall()
        cur.close()
        conn.close()
        
        # Convert datetimes to strings
        for inc in incidents:
            if inc.get('created_at'):
                inc['created_at'] = inc['created_at'].isoformat()
        
        return incidents
    
    except Exception as e:
        print(f"[MODERATION] Failed to get incidents: {e}")
        return []


def get_moderation_stats():
    """Get moderation statistics for admin dashboard."""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        database_url = os.environ.get('DATABASE_URL')
        
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                COUNT(*) as total_incidents,
                COUNT(*) FILTER (WHERE was_blocked = TRUE) as total_blocked,
                COUNT(*) FILTER (WHERE was_blocked = FALSE) as total_warnings,
                COUNT(DISTINCT user_id) FILTER (WHERE was_blocked = TRUE) as users_blocked
            FROM content_incidents
        """)
        
        stats = cur.fetchone()
        cur.close()
        conn.close()
        
        return dict(stats) if stats else {
            'total_incidents': 0,
            'total_blocked': 0,
            'total_warnings': 0,
            'users_blocked': 0
        }
    
    except Exception as e:
        print(f"[MODERATION] Failed to get stats: {e}")
        return {'total_incidents': 0, 'total_blocked': 0, 'total_warnings': 0, 'users_blocked': 0}
