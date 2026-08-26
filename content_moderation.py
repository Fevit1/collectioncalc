"""
Content Moderation module for Slab Worthy.
Uses Amazon Rekognition to detect inappropriate content in uploaded images.

Checks run BEFORE any image is stored or processed.
Blocks: explicit content, graphic violence, hate symbols.
Warns (log-only): violence, visually disturbing.

The category sets below are written against Rekognition moderation model v7
(confirmed live: v7.0, Render shell, 2026-08-25) and each entry is annotated
with what it matches. HISTORY THAT MUST NOT REPEAT: the original set mixed
v6-era names with misremembered v7 names, so when AWS force-migrated every
account to v7 (June 2024) five of eight blocked entries silently stopped
matching anything — and stayed that way for 27 months, invisible, because a
label set that matches nothing looks identical to one that matches everything
clean. moderate_image() now persists ModerationModelVersion on every real
call and dependency_monitor alerts when it changes; when that alert fires,
re-verify every entry here against the new taxonomy BEFORE acknowledging.

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
# focus on the most severe categories).
#
# Matching semantics (see the loop in moderate_image): a returned label hits
# when its Name, its ParentName, or "ParentName: Name" is in the set. So an L1
# entry catches itself AND every L2 under it; it does NOT catch L3s two levels
# down — but AWS returns ancestor labels alongside any detected child, so the
# L1/L2 entry still fires on the same image.
#
# Verified against the live v7.0 taxonomy 2026-08-25 (docs + Render-shell
# probe). Set deliberately minimal — every entry says what it covers:
BLOCKED_CATEGORIES = {
    # v7 L1. Catches the L1 itself plus all current L2s via ParentName:
    # 'Explicit Nudity', 'Explicit Sexual Activity', 'Sex Toys' — and any L2
    # AWS adds under it later, which is why the L1 and not the L2s is listed.
    'Explicit',
    # v7 L2 under 'Violence'. Catches its L3s (Weapon/Physical Violence,
    # Self-Harm, Blood & Gore, Explosions and Blasts) via ParentName. The L1
    # 'Violence' stays warn-only: superhero comics fire it constantly.
    'Graphic Violence',
    # v7 L1, unchanged since v6. Catches Nazi Party / White Supremacy /
    # Extremist via ParentName.
    'Hate Symbols',
}
# ⚰️ DELIBERATELY DELETED from BLOCKED (Mike, 2026-08-25) — do not restore:
# - All 'Drugs & Tobacco' entries: drugs, tobacco and alcohol imagery are FINE
#   for comic content (covers depict all three constantly). These were removed
#   as a policy decision, not corrected to their v7 names.
# - 'Sexual Activity': subsumed — v7 renamed it 'Explicit Sexual Activity',
#   whose parent is 'Explicit', already blocked above.
# - 'Animated Explicit Nudity': never a v7 label. v7 moved animation to the
#   separate ContentTypes response field; animated explicit content still
#   labels as 'Explicit Nudity' under 'Explicit' and is caught above.
# - 'Non-Explicit Nudity of Intimate parts and Coverage': a misremembered
#   name (the real v7 L1 ends '... and Kissing') that never matched any
#   version — and we would not block that L1 anyway, for the same reason
#   'Suggestive' stays out (see below).

# Categories we log but don't block (comics may trigger these)
# These get logged for review but don't stop the upload
WARNING_CATEGORIES = {
    'Violence',              # v7 L1 — also pulls in 'Weapons' via ParentName
    'Visually Disturbing',   # v7 L1 — pulls in 'Death and Emaciation', 'Crashes'
}
# ⚰️ 'Suggestive' DELIBERATELY NOT RESTORED (Mike, 2026-08-25): v6 killed the
# label; v7 split it into 'Non-Explicit Nudity of Intimate parts and Kissing'
# and 'Swimwear or Underwear'. Comic covers are full of costumed figures and
# either successor would fire constantly on legitimate books. Do not "fix"
# this by adding the successors. ('Drugs & Tobacco: Tobacco Products' removed
# under the same policy decision as the blocked drug entries above.)

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
# MODEL VERSION TRACKING
# ============================================
#
# AWS returns ModerationModelVersion on every DetectModerationLabels call and
# we used to discard it. That is how the May-2024 v6→v7 migration silently
# unhooked most of BLOCKED_CATEGORIES for 27 months: a taxonomy change arrives
# as a version bump, and nothing was looking. Every observed version is now
# persisted; dependency_monitor alerts when more than one distinct version has
# been seen (i.e. AWS migrated the model under us). Acknowledging that alert =
# re-verifying the category sets above against the new taxonomy, then deleting
# the old version's row (SQL below, run in DBeaver):
#   DELETE FROM rekognition_model_versions WHERE version = '<old>';

_seen_model_versions = set()  # per-process cache: one DB write per version per boot


def _record_model_version(version):
    """Persist an observed ModerationModelVersion (once per process per version).

    Never raises — version tracking must not break moderation, and moderation
    must not break uploads. A failed write retries on the next call because the
    cache is only updated after commit.
    """
    if not version or version in _seen_model_versions:
        return
    conn = None
    try:
        import db as _dbpool
        conn = _dbpool.get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rekognition_model_versions (
                version TEXT PRIMARY KEY,
                first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("""
            INSERT INTO rekognition_model_versions (version)
            VALUES (%s)
            ON CONFLICT (version) DO UPDATE SET last_seen_at = NOW()
        """, (version,))
        conn.commit()
        cur.close()
        _seen_model_versions.add(version)
    except Exception as e:
        print(f"[MODERATION] Failed to record model version {version!r}: {e}")
        if conn is not None:
            try:
                conn.rollback()  # never return an aborted txn to the shared pool
            except Exception:
                pass
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


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

        # Track the model version so a taxonomy migration alerts instead of
        # silently unhooking the category sets (see MODEL VERSION TRACKING).
        _record_model_version(response.get('ModerationModelVersion'))

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
        import db as _dbpool
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            return
        
        conn = _dbpool.get_db()
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
        import db as _dbpool
        from psycopg2.extras import RealDictCursor
        database_url = os.environ.get('DATABASE_URL')
        
        conn = _dbpool.get_db(dict_rows=True)
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
        import db as _dbpool
        from psycopg2.extras import RealDictCursor
        database_url = os.environ.get('DATABASE_URL')
        
        conn = _dbpool.get_db(dict_rows=True)
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
