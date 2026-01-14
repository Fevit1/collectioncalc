"""
CollectionCalc - User Adjustments Module
Handles personal weight overrides (Tier 2 of the three-tier system)

Tier 1: Global Model (protected, curated by admin)
Tier 2: User Personal Adjustments (this module)
Tier 3: Feedback Analytics (insight only, never auto-applied)
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Dict, Optional, List

USER_DB = "user_adjustments.db"


class UserAdjustments:
    """
    Manages per-user weight overrides
    
    Usage:
        ua = UserAdjustments()
        
        # Set a personal override
        ua.set_adjustment("user_123", "grade_multipliers", "VF", 0.80)
        
        # Get user's effective weights (global + overrides)
        weights = ua.get_effective_weights("user_123", global_weights)
    """
    
    def __init__(self, db_path: str = USER_DB):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Create user adjustments database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # User profiles
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                display_name TEXT,
                created_at TEXT,
                last_active TEXT,
                is_excluded BOOLEAN DEFAULT 0,
                exclusion_reason TEXT,
                excluded_at TEXT,
                trust_score REAL DEFAULT 1.0,
                total_corrections INTEGER DEFAULT 0,
                notes TEXT
            )
        ''')
        
        # Personal weight adjustments
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS adjustments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value REAL NOT NULL,
                created_at TEXT,
                updated_at TEXT,
                reason TEXT,
                UNIQUE(user_id, category, key),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Adjustment history (audit trail)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS adjustment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                old_value REAL,
                new_value REAL,
                changed_at TEXT,
                reason TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_or_create_user(self, user_id: str, display_name: str = None) -> Dict:
        """Get user profile or create if doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if row:
            columns = [desc[0] for desc in cursor.description]
            user = dict(zip(columns, row))
            
            # Update last active
            cursor.execute('''
                UPDATE users SET last_active = ? WHERE user_id = ?
            ''', (datetime.now().isoformat(), user_id))
            conn.commit()
        else:
            # Create new user
            now = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO users (user_id, display_name, created_at, last_active)
                VALUES (?, ?, ?, ?)
            ''', (user_id, display_name or user_id, now, now))
            conn.commit()
            
            user = {
                'user_id': user_id,
                'display_name': display_name or user_id,
                'created_at': now,
                'last_active': now,
                'is_excluded': False,
                'trust_score': 1.0,
                'total_corrections': 0
            }
        
        conn.close()
        return user
    
    def set_adjustment(
        self, 
        user_id: str, 
        category: str, 
        key: str, 
        value: float,
        reason: str = None
    ) -> Dict:
        """
        Set a personal weight override
        
        Args:
            user_id: User identifier
            category: Weight category (e.g., "grade_multipliers")
            key: Specific key (e.g., "VF")
            value: Override value
            reason: Optional reason for the adjustment
            
        Returns:
            The adjustment record
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Ensure user exists
        self.get_or_create_user(user_id)
        
        now = datetime.now().isoformat()
        
        # Get old value for history
        cursor.execute('''
            SELECT value FROM adjustments 
            WHERE user_id = ? AND category = ? AND key = ?
        ''', (user_id, category, key))
        old_row = cursor.fetchone()
        old_value = old_row[0] if old_row else None
        
        # Upsert adjustment
        cursor.execute('''
            INSERT INTO adjustments (user_id, category, key, value, created_at, updated_at, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, category, key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at,
                reason = excluded.reason
        ''', (user_id, category, key, value, now, now, reason))
        
        # Log to history
        cursor.execute('''
            INSERT INTO adjustment_history (user_id, category, key, old_value, new_value, changed_at, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, category, key, old_value, value, now, reason))
        
        conn.commit()
        conn.close()
        
        return {
            'user_id': user_id,
            'category': category,
            'key': key,
            'old_value': old_value,
            'new_value': value,
            'reason': reason
        }
    
    def get_user_adjustments(self, user_id: str) -> Dict:
        """Get all adjustments for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT category, key, value, reason, updated_at
            FROM adjustments
            WHERE user_id = ?
        ''', (user_id,))
        
        adjustments = {}
        for row in cursor.fetchall():
            category, key, value, reason, updated_at = row
            if category not in adjustments:
                adjustments[category] = {}
            adjustments[category][key] = {
                'value': value,
                'reason': reason,
                'updated_at': updated_at
            }
        
        conn.close()
        return adjustments
    
    def delete_adjustment(self, user_id: str, category: str, key: str) -> bool:
        """Remove a personal adjustment (revert to global)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current value for history
        cursor.execute('''
            SELECT value FROM adjustments
            WHERE user_id = ? AND category = ? AND key = ?
        ''', (user_id, category, key))
        row = cursor.fetchone()
        
        if row:
            old_value = row[0]
            
            # Log deletion
            cursor.execute('''
                INSERT INTO adjustment_history (user_id, category, key, old_value, new_value, changed_at, reason)
                VALUES (?, ?, ?, ?, NULL, ?, 'Reverted to global')
            ''', (user_id, category, key, old_value, datetime.now().isoformat()))
            
            # Delete
            cursor.execute('''
                DELETE FROM adjustments
                WHERE user_id = ? AND category = ? AND key = ?
            ''', (user_id, category, key))
            
            conn.commit()
            conn.close()
            return True
        
        conn.close()
        return False
    
    def clear_all_adjustments(self, user_id: str) -> int:
        """Clear all personal adjustments for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Log all deletions
        cursor.execute('''
            SELECT category, key, value FROM adjustments WHERE user_id = ?
        ''', (user_id,))
        
        now = datetime.now().isoformat()
        for row in cursor.fetchall():
            cursor.execute('''
                INSERT INTO adjustment_history (user_id, category, key, old_value, new_value, changed_at, reason)
                VALUES (?, ?, ?, ?, NULL, ?, 'Bulk reset to global')
            ''', (user_id, row[0], row[1], row[2], now))
        
        cursor.execute('DELETE FROM adjustments WHERE user_id = ?', (user_id,))
        deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        return deleted
    
    def get_effective_weights(self, user_id: str, global_weights: Dict) -> Dict:
        """
        Merge global weights with user's personal overrides
        
        Args:
            user_id: User identifier
            global_weights: The global/default weights
            
        Returns:
            Merged weights dict (global values overridden by user values where set)
        """
        import copy
        
        # Start with copy of global weights
        effective = copy.deepcopy(global_weights)
        
        # Get user adjustments
        user_adj = self.get_user_adjustments(user_id)
        
        # Apply overrides
        for category, overrides in user_adj.items():
            if category in effective:
                for key, data in overrides.items():
                    if key in effective[category]:
                        effective[category][key] = data['value']
        
        return effective
    
    # ==================== USER MANAGEMENT ====================
    
    def exclude_user(self, user_id: str, reason: str = None) -> bool:
        """
        Exclude a user's feedback from model consideration
        Their personal adjustments still work for them, but their
        feedback won't influence global model suggestions.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        self.get_or_create_user(user_id)
        
        cursor.execute('''
            UPDATE users 
            SET is_excluded = 1, exclusion_reason = ?, excluded_at = ?
            WHERE user_id = ?
        ''', (reason, datetime.now().isoformat(), user_id))
        
        conn.commit()
        conn.close()
        return True
    
    def include_user(self, user_id: str) -> bool:
        """Re-include a previously excluded user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET is_excluded = 0, exclusion_reason = NULL, excluded_at = NULL
            WHERE user_id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
        return True
    
    def is_user_excluded(self, user_id: str) -> bool:
        """Check if user is excluded from feedback consideration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT is_excluded FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        conn.close()
        return bool(row[0]) if row else False
    
    def set_trust_score(self, user_id: str, score: float, notes: str = None) -> bool:
        """
        Set a trust score for a user (0.0 to 1.0)
        Can be used to weight their feedback in suggestions.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        self.get_or_create_user(user_id)
        
        cursor.execute('''
            UPDATE users SET trust_score = ?, notes = ?
            WHERE user_id = ?
        ''', (max(0.0, min(1.0, score)), notes, user_id))
        
        conn.commit()
        conn.close()
        return True
    
    def increment_correction_count(self, user_id: str) -> int:
        """Increment the correction count for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        self.get_or_create_user(user_id)
        
        cursor.execute('''
            UPDATE users SET total_corrections = total_corrections + 1
            WHERE user_id = ?
        ''', (user_id,))
        
        cursor.execute('SELECT total_corrections FROM users WHERE user_id = ?', (user_id,))
        count = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        return count
    
    def get_excluded_users(self) -> List[Dict]:
        """Get all excluded users"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, display_name, exclusion_reason, excluded_at, total_corrections
            FROM users WHERE is_excluded = 1
        ''')
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'user_id': row[0],
                'display_name': row[1],
                'exclusion_reason': row[2],
                'excluded_at': row[3],
                'total_corrections': row[4]
            })
        
        conn.close()
        return users
    
    def get_all_users(self, include_excluded: bool = True) -> List[Dict]:
        """Get all users with stats"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = 'SELECT * FROM users'
        if not include_excluded:
            query += ' WHERE is_excluded = 0'
        query += ' ORDER BY total_corrections DESC'
        
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        
        users = []
        for row in cursor.fetchall():
            users.append(dict(zip(columns, row)))
        
        conn.close()
        return users
    
    def get_user_stats(self, user_id: str) -> Dict:
        """Get detailed stats for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Basic info
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        columns = [desc[0] for desc in cursor.description]
        user = dict(zip(columns, row))
        
        # Count adjustments
        cursor.execute('''
            SELECT COUNT(*) FROM adjustments WHERE user_id = ?
        ''', (user_id,))
        user['adjustment_count'] = cursor.fetchone()[0]
        
        # Adjustment history count
        cursor.execute('''
            SELECT COUNT(*) FROM adjustment_history WHERE user_id = ?
        ''', (user_id,))
        user['history_count'] = cursor.fetchone()[0]
        
        conn.close()
        return user


# Test
def test_user_adjustments():
    """Test the user adjustments system"""
    import os
    
    # Use test database
    test_db = "test_user_adjustments.db"
    ua = UserAdjustments(test_db)
    
    print("=" * 60)
    print("USER ADJUSTMENTS TEST")
    print("=" * 60)
    
    # Test user creation
    print("\n1. Creating users...")
    user1 = ua.get_or_create_user("user_123", "Comic Collector")
    user2 = ua.get_or_create_user("user_456", "Bronze Age Specialist")
    print(f"   Created: {user1['display_name']}, {user2['display_name']}")
    
    # Test setting adjustments
    print("\n2. Setting personal adjustments...")
    ua.set_adjustment("user_123", "grade_multipliers", "VF", 0.80, 
                      "I think VF is undervalued")
    ua.set_adjustment("user_123", "edition_multipliers", "newsstand", 1.75,
                      "Newsstand premiums are higher in my experience")
    ua.set_adjustment("user_456", "grade_multipliers", "FN", 0.55,
                      "Bronze Age FN books hold value better")
    print("   Set 3 adjustments")
    
    # Test getting adjustments
    print("\n3. Getting user adjustments...")
    adj = ua.get_user_adjustments("user_123")
    print(f"   user_123 adjustments: {json.dumps(adj, indent=2)}")
    
    # Test effective weights
    print("\n4. Testing effective weights merge...")
    global_weights = {
        "grade_multipliers": {"NM": 1.0, "VF": 0.75, "FN": 0.50},
        "edition_multipliers": {"direct": 1.0, "newsstand": 1.25}
    }
    effective = ua.get_effective_weights("user_123", global_weights)
    print(f"   Global VF: 0.75 → User effective VF: {effective['grade_multipliers']['VF']}")
    print(f"   Global newsstand: 1.25 → User effective: {effective['edition_multipliers']['newsstand']}")
    
    # Test user exclusion
    print("\n5. Testing user exclusion...")
    ua.exclude_user("user_456", "Consistently submitting outlier values")
    excluded = ua.get_excluded_users()
    print(f"   Excluded users: {[u['user_id'] for u in excluded]}")
    print(f"   user_456 excluded: {ua.is_user_excluded('user_456')}")
    
    # Test re-inclusion
    ua.include_user("user_456")
    print(f"   After re-inclusion: {ua.is_user_excluded('user_456')}")
    
    # Test trust score
    print("\n6. Testing trust scores...")
    ua.set_trust_score("user_123", 0.9, "Reliable collector")
    ua.set_trust_score("user_456", 0.5, "New user, need more data")
    
    # Get all users
    print("\n7. All users:")
    for user in ua.get_all_users():
        print(f"   {user['user_id']}: trust={user['trust_score']}, corrections={user['total_corrections']}")
    
    # Cleanup
    os.remove(test_db)
    print("\n✅ Test complete (database cleaned up)")


if __name__ == "__main__":
    test_user_adjustments()
