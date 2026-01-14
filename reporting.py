"""
CollectionCalc - Reporting Module
Analytics and reports on valuation feedback data

Phase 1: Pre-built reports with structured queries
Phase 2: Natural Language Query interface (on roadmap)
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

FEEDBACK_DB = "valuation_feedback.db"
USER_DB = "user_adjustments.db"


class ReportingEngine:
    """
    Generate reports and analytics on valuation feedback
    
    Reports available:
    - Accuracy overview
    - Grade analysis
    - Edition analysis  
    - Publisher analysis
    - User contribution analysis
    - Outlier detection
    - Time series trends
    """
    
    def __init__(self, feedback_db: str = FEEDBACK_DB, user_db: str = USER_DB):
        self.feedback_db = feedback_db
        self.user_db = user_db
    
    def _get_feedback_conn(self):
        return sqlite3.connect(self.feedback_db)
    
    def _get_user_conn(self):
        return sqlite3.connect(self.user_db)
    
    # ==================== CORE REPORTS ====================
    
    def accuracy_overview(self, exclude_flagged_users: bool = True) -> Dict:
        """
        Overall model accuracy report
        
        Returns:
            - Total corrections
            - Average delta (over/under estimation)
            - Average absolute error
            - Accuracy by confidence level
        """
        conn = self._get_feedback_conn()
        cursor = conn.cursor()
        
        # Build exclusion clause if needed
        exclusion_clause = ""
        if exclude_flagged_users:
            try:
                user_conn = self._get_user_conn()
                user_cursor = user_conn.cursor()
                user_cursor.execute('SELECT user_id FROM users WHERE is_excluded = 1')
                excluded = [row[0] for row in user_cursor.fetchall()]
                user_conn.close()
                
                if excluded:
                    placeholders = ','.join(['?' for _ in excluded])
                    exclusion_clause = f" WHERE user_id NOT IN ({placeholders})"
            except:
                excluded = []
        else:
            excluded = []
        
        # Overall stats
        query = f'''
            SELECT 
                COUNT(*) as total,
                AVG(delta_percent) as avg_delta,
                AVG(ABS(delta_percent)) as avg_abs_error,
                MIN(delta_percent) as min_delta,
                MAX(delta_percent) as max_delta,
                SUM(CASE WHEN ABS(delta_percent) <= 10 THEN 1 ELSE 0 END) as within_10_pct,
                SUM(CASE WHEN ABS(delta_percent) <= 20 THEN 1 ELSE 0 END) as within_20_pct,
                SUM(CASE WHEN ABS(delta_percent) <= 30 THEN 1 ELSE 0 END) as within_30_pct
            FROM feedback
            {exclusion_clause}
        '''
        
        cursor.execute(query, excluded if excluded else ())
        row = cursor.fetchone()
        
        total = row[0] or 0
        
        report = {
            'report_name': 'Accuracy Overview',
            'generated_at': datetime.now().isoformat(),
            'excluded_users': len(excluded),
            'total_corrections': total,
            'avg_delta_percent': round(row[1], 2) if row[1] else 0,
            'avg_absolute_error': round(row[2], 2) if row[2] else 0,
            'min_delta_percent': round(row[3], 2) if row[3] else 0,
            'max_delta_percent': round(row[4], 2) if row[4] else 0,
            'accuracy_bands': {
                'within_10_percent': row[5] or 0,
                'within_20_percent': row[6] or 0,
                'within_30_percent': row[7] or 0,
            },
            'accuracy_rates': {
                'within_10_percent': round((row[5] or 0) / total * 100, 1) if total else 0,
                'within_20_percent': round((row[6] or 0) / total * 100, 1) if total else 0,
                'within_30_percent': round((row[7] or 0) / total * 100, 1) if total else 0,
            }
        }
        
        # Breakdown by confidence level
        cursor.execute(f'''
            SELECT 
                CASE 
                    WHEN confidence_score >= 90 THEN 'high_confidence'
                    WHEN confidence_score >= 70 THEN 'medium_confidence'
                    ELSE 'low_confidence'
                END as conf_level,
                COUNT(*) as count,
                AVG(ABS(delta_percent)) as avg_error
            FROM feedback
            {exclusion_clause}
            GROUP BY conf_level
        ''', excluded if excluded else ())
        
        report['by_confidence'] = {}
        for row in cursor.fetchall():
            report['by_confidence'][row[0]] = {
                'count': row[1],
                'avg_absolute_error': round(row[2], 2) if row[2] else 0
            }
        
        conn.close()
        return report
    
    def grade_analysis(self, min_samples: int = 3) -> Dict:
        """
        Analyze accuracy by grade
        
        Identifies which grades need multiplier adjustments
        """
        conn = self._get_feedback_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                grade,
                COUNT(*) as samples,
                AVG(delta_percent) as avg_delta,
                AVG(ABS(delta_percent)) as avg_abs_error,
                MIN(delta_percent) as min_delta,
                MAX(delta_percent) as max_delta,
                AVG(model_predicted) as avg_predicted,
                AVG(user_corrected) as avg_corrected
            FROM feedback
            GROUP BY grade
            HAVING COUNT(*) >= ?
            ORDER BY COUNT(*) DESC
        ''', (min_samples,))
        
        grades = []
        for row in cursor.fetchall():
            grade_data = {
                'grade': row[0],
                'samples': row[1],
                'avg_delta_percent': round(row[2], 2) if row[2] else 0,
                'avg_absolute_error': round(row[3], 2) if row[3] else 0,
                'min_delta': round(row[4], 2) if row[4] else 0,
                'max_delta': round(row[5], 2) if row[5] else 0,
                'avg_predicted': round(row[6], 2) if row[6] else 0,
                'avg_corrected': round(row[7], 2) if row[7] else 0,
                'needs_adjustment': abs(row[2] or 0) > 10,
                'adjustment_direction': 'increase' if (row[2] or 0) > 0 else 'decrease'
            }
            grades.append(grade_data)
        
        conn.close()
        
        return {
            'report_name': 'Grade Analysis',
            'generated_at': datetime.now().isoformat(),
            'min_samples_threshold': min_samples,
            'grades': grades,
            'grades_needing_adjustment': [g['grade'] for g in grades if g['needs_adjustment']]
        }
    
    def edition_analysis(self, min_samples: int = 3) -> Dict:
        """Analyze accuracy by edition type"""
        conn = self._get_feedback_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                edition,
                COUNT(*) as samples,
                AVG(delta_percent) as avg_delta,
                AVG(ABS(delta_percent)) as avg_abs_error
            FROM feedback
            GROUP BY edition
            HAVING COUNT(*) >= ?
            ORDER BY COUNT(*) DESC
        ''', (min_samples,))
        
        editions = []
        for row in cursor.fetchall():
            editions.append({
                'edition': row[0],
                'samples': row[1],
                'avg_delta_percent': round(row[2], 2) if row[2] else 0,
                'avg_absolute_error': round(row[3], 2) if row[3] else 0,
                'needs_adjustment': abs(row[2] or 0) > 10
            })
        
        conn.close()
        
        return {
            'report_name': 'Edition Analysis',
            'generated_at': datetime.now().isoformat(),
            'editions': editions
        }
    
    def publisher_analysis(self, min_samples: int = 3) -> Dict:
        """Analyze accuracy by publisher"""
        conn = self._get_feedback_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                publisher,
                COUNT(*) as samples,
                AVG(delta_percent) as avg_delta,
                AVG(ABS(delta_percent)) as avg_abs_error,
                AVG(model_predicted) as avg_value
            FROM feedback
            GROUP BY publisher
            HAVING COUNT(*) >= ?
            ORDER BY COUNT(*) DESC
        ''', (min_samples,))
        
        publishers = []
        for row in cursor.fetchall():
            publishers.append({
                'publisher': row[0],
                'samples': row[1],
                'avg_delta_percent': round(row[2], 2) if row[2] else 0,
                'avg_absolute_error': round(row[3], 2) if row[3] else 0,
                'avg_value': round(row[4], 2) if row[4] else 0,
                'needs_adjustment': abs(row[2] or 0) > 10
            })
        
        conn.close()
        
        return {
            'report_name': 'Publisher Analysis',
            'generated_at': datetime.now().isoformat(),
            'publishers': publishers
        }
    
    def user_contribution_report(self) -> Dict:
        """
        Analyze contributions by user
        
        Identifies:
        - Most active contributors
        - Users with high variance (possible bad actors)
        - Users with consistent accuracy
        """
        conn = self._get_feedback_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                user_id,
                COUNT(*) as corrections,
                AVG(delta_percent) as avg_delta,
                AVG(ABS(delta_percent)) as avg_abs_error,
                MIN(delta_percent) as min_delta,
                MAX(delta_percent) as max_delta,
                MAX(delta_percent) - MIN(delta_percent) as variance_range
            FROM feedback
            WHERE user_id IS NOT NULL
            GROUP BY user_id
            ORDER BY COUNT(*) DESC
        ''')
        
        users = []
        flagged_users = []
        
        for row in cursor.fetchall():
            user_data = {
                'user_id': row[0],
                'corrections': row[1],
                'avg_delta_percent': round(row[2], 2) if row[2] else 0,
                'avg_absolute_error': round(row[3], 2) if row[3] else 0,
                'min_delta': round(row[4], 2) if row[4] else 0,
                'max_delta': round(row[5], 2) if row[5] else 0,
                'variance_range': round(row[6], 2) if row[6] else 0,
            }
            
            # Flag suspicious users
            flags = []
            if abs(user_data['avg_delta_percent']) > 50:
                flags.append('high_avg_delta')
            if user_data['variance_range'] > 100:
                flags.append('high_variance')
            if user_data['corrections'] > 5 and user_data['avg_absolute_error'] > 40:
                flags.append('consistently_inaccurate')
            
            user_data['flags'] = flags
            user_data['is_suspicious'] = len(flags) > 0
            
            users.append(user_data)
            
            if user_data['is_suspicious']:
                flagged_users.append(user_data)
        
        conn.close()
        
        return {
            'report_name': 'User Contribution Report',
            'generated_at': datetime.now().isoformat(),
            'total_contributing_users': len(users),
            'users': users,
            'flagged_users': flagged_users,
            'flagged_count': len(flagged_users)
        }
    
    def outlier_report(self, threshold_percent: float = 50) -> Dict:
        """
        Find individual corrections that are outliers
        
        These might be:
        - Data entry errors
        - Unusual market situations
        - Potential manipulation attempts
        """
        conn = self._get_feedback_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                timestamp,
                user_id,
                comic_title,
                issue_number,
                grade,
                model_predicted,
                user_corrected,
                delta,
                delta_percent,
                user_notes
            FROM feedback
            WHERE ABS(delta_percent) > ?
            ORDER BY ABS(delta_percent) DESC
            LIMIT 50
        ''', (threshold_percent,))
        
        outliers = []
        for row in cursor.fetchall():
            outliers.append({
                'timestamp': row[0],
                'user_id': row[1],
                'comic': f"{row[2]} #{row[3]}",
                'grade': row[4],
                'model_predicted': row[5],
                'user_corrected': row[6],
                'delta': row[7],
                'delta_percent': row[8],
                'notes': row[9]
            })
        
        conn.close()
        
        return {
            'report_name': 'Outlier Report',
            'generated_at': datetime.now().isoformat(),
            'threshold_percent': threshold_percent,
            'outlier_count': len(outliers),
            'outliers': outliers
        }
    
    def time_series_report(self, days: int = 30) -> Dict:
        """
        Analyze accuracy trends over time
        
        Shows if model is getting better or worse
        """
        conn = self._get_feedback_conn()
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as corrections,
                AVG(delta_percent) as avg_delta,
                AVG(ABS(delta_percent)) as avg_abs_error
            FROM feedback
            WHERE timestamp >= ?
            GROUP BY DATE(timestamp)
            ORDER BY date
        ''', (cutoff,))
        
        daily_data = []
        for row in cursor.fetchall():
            daily_data.append({
                'date': row[0],
                'corrections': row[1],
                'avg_delta_percent': round(row[2], 2) if row[2] else 0,
                'avg_absolute_error': round(row[3], 2) if row[3] else 0
            })
        
        conn.close()
        
        # Calculate trend
        if len(daily_data) >= 2:
            first_week_error = sum(d['avg_absolute_error'] for d in daily_data[:7]) / min(7, len(daily_data))
            last_week_error = sum(d['avg_absolute_error'] for d in daily_data[-7:]) / min(7, len(daily_data))
            trend = 'improving' if last_week_error < first_week_error else 'declining'
        else:
            trend = 'insufficient_data'
        
        return {
            'report_name': 'Time Series Report',
            'generated_at': datetime.now().isoformat(),
            'days_analyzed': days,
            'trend': trend,
            'daily_data': daily_data
        }
    
    def comic_specific_report(self, title: str, issue: str = None) -> Dict:
        """
        Analyze feedback for a specific comic or series
        """
        conn = self._get_feedback_conn()
        cursor = conn.cursor()
        
        if issue:
            cursor.execute('''
                SELECT 
                    grade,
                    edition,
                    COUNT(*) as samples,
                    AVG(model_predicted) as avg_predicted,
                    AVG(user_corrected) as avg_corrected,
                    AVG(delta_percent) as avg_delta
                FROM feedback
                WHERE comic_title LIKE ? AND issue_number = ?
                GROUP BY grade, edition
            ''', (f'%{title}%', issue))
        else:
            cursor.execute('''
                SELECT 
                    issue_number,
                    COUNT(*) as samples,
                    AVG(delta_percent) as avg_delta
                FROM feedback
                WHERE comic_title LIKE ?
                GROUP BY issue_number
                ORDER BY CAST(issue_number AS INTEGER)
            ''', (f'%{title}%',))
        
        results = []
        for row in cursor.fetchall():
            results.append(row)
        
        conn.close()
        
        return {
            'report_name': f'Comic Report: {title}' + (f' #{issue}' if issue else ''),
            'generated_at': datetime.now().isoformat(),
            'results': results
        }
    
    # ==================== SUMMARY DASHBOARD ====================
    
    def generate_dashboard(self) -> Dict:
        """
        Generate a complete dashboard with all key metrics
        """
        return {
            'report_name': 'Dashboard',
            'generated_at': datetime.now().isoformat(),
            'accuracy': self.accuracy_overview(),
            'grades': self.grade_analysis(),
            'editions': self.edition_analysis(),
            'publishers': self.publisher_analysis(),
            'users': self.user_contribution_report(),
            'outliers': self.outlier_report(),
            'trends': self.time_series_report()
        }
    
    def print_summary(self):
        """Print a human-readable summary"""
        accuracy = self.accuracy_overview()
        users = self.user_contribution_report()
        
        print("=" * 60)
        print("COLLECTIONCALC ANALYTICS DASHBOARD")
        print("=" * 60)
        
        print(f"\n📊 ACCURACY OVERVIEW")
        print(f"   Total corrections: {accuracy['total_corrections']}")
        print(f"   Average error: {accuracy['avg_absolute_error']}%")
        print(f"   Model bias: {accuracy['avg_delta_percent']:+.1f}% (negative=overvaluing)")
        print(f"   Within 10%: {accuracy['accuracy_rates']['within_10_percent']}%")
        print(f"   Within 20%: {accuracy['accuracy_rates']['within_20_percent']}%")
        
        print(f"\n👥 USER CONTRIBUTIONS")
        print(f"   Total contributors: {users['total_contributing_users']}")
        print(f"   Flagged users: {users['flagged_count']}")
        if users['flagged_users']:
            print(f"   ⚠️  Review needed:")
            for u in users['flagged_users'][:3]:
                print(f"      {u['user_id']}: {u['flags']}")
        
        grades = self.grade_analysis()
        if grades['grades_needing_adjustment']:
            print(f"\n🎯 GRADES NEEDING ADJUSTMENT")
            for g in grades['grades']:
                if g['needs_adjustment']:
                    print(f"   {g['grade']}: {g['adjustment_direction']} by ~{abs(g['avg_delta_percent']):.0f}%")


# Quick test
def test_reporting():
    """Test the reporting engine"""
    engine = ReportingEngine()
    
    print("=" * 60)
    print("REPORTING ENGINE TEST")
    print("=" * 60)
    
    # Try to generate reports (may fail if no data)
    try:
        accuracy = engine.accuracy_overview()
        print(f"\n✅ Accuracy Overview: {accuracy['total_corrections']} corrections analyzed")
        
        grades = engine.grade_analysis()
        print(f"✅ Grade Analysis: {len(grades['grades'])} grades analyzed")
        
        users = engine.user_contribution_report()
        print(f"✅ User Report: {users['total_contributing_users']} users")
        
    except Exception as e:
        print(f"\n⚠️  Reports require feedback data: {e}")
        print("   Run the app and submit some corrections first!")


if __name__ == "__main__":
    test_reporting()
