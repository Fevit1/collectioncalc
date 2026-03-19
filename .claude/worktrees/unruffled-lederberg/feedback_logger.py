"""
CollectionCalc - Feedback Logger
Tracks user corrections to improve valuation model over time

This creates a learning loop:
1. Model provides valuation
2. User corrects if wrong
3. Correction is logged with context
4. Periodically analyze corrections to tune weights

Data collected:
- What the model predicted
- What the user corrected to
- The delta (over/under estimation)
- Context (grade, edition, publisher, etc.)
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
import statistics

FEEDBACK_DB = "valuation_feedback.db"
ANALYSIS_REPORT = "feedback_analysis.json"


@dataclass
class FeedbackEntry:
    """A single user correction"""
    timestamp: str
    user_id: Optional[str]
    comic_title: str
    issue_number: str
    publisher: str
    year: Optional[int]
    grade: str
    edition: str
    cgc: bool
    
    # Values
    base_nm_value: float
    model_predicted: float
    user_corrected: float
    delta: float
    delta_percent: float
    
    # Context
    confidence_score: float
    base_value_source: str
    
    # Optional notes
    user_notes: Optional[str]


class FeedbackLogger:
    """
    Logs user corrections and analyzes patterns for model improvement
    """
    
    def __init__(self, db_path: str = FEEDBACK_DB):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Create feedback database if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_id TEXT,
                comic_title TEXT,
                issue_number TEXT,
                publisher TEXT,
                year INTEGER,
                grade TEXT,
                edition TEXT,
                cgc BOOLEAN,
                base_nm_value REAL,
                model_predicted REAL,
                user_corrected REAL,
                delta REAL,
                delta_percent REAL,
                confidence_score REAL,
                base_value_source TEXT,
                user_notes TEXT
            )
        ''')
        
        # Create indexes for analysis
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_grade ON feedback(grade)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edition ON feedback(edition)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_publisher ON feedback(publisher)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_delta ON feedback(delta_percent)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user ON feedback(user_id)')
        
        conn.commit()
        conn.close()
    
    def log_correction(
        self,
        comic_title: str,
        issue_number: str,
        model_predicted: float,
        user_corrected: float,
        grade: str,
        edition: str = "direct",
        publisher: str = "Unknown",
        year: Optional[int] = None,
        cgc: bool = False,
        base_nm_value: float = 0,
        confidence_score: float = 0,
        base_value_source: str = "unknown",
        user_notes: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> FeedbackEntry:
        """
        Log a user correction
        
        Args:
            comic_title: Title of the comic
            issue_number: Issue number
            model_predicted: What the model calculated
            user_corrected: What the user corrected it to
            grade: Comic grade
            edition: Edition type
            publisher: Publisher name
            year: Publication year
            cgc: Whether CGC graded
            base_nm_value: The base NM value used
            confidence_score: Model's confidence score
            base_value_source: Where base value came from
            user_notes: Optional user explanation
            
        Returns:
            FeedbackEntry for confirmation
        """
        delta = user_corrected - model_predicted
        delta_percent = (delta / model_predicted * 100) if model_predicted > 0 else 0
        
        entry = FeedbackEntry(
            timestamp=datetime.now().isoformat(),
            user_id=user_id,
            comic_title=comic_title,
            issue_number=issue_number,
            publisher=publisher,
            year=year,
            grade=grade,
            edition=edition,
            cgc=cgc,
            base_nm_value=base_nm_value,
            model_predicted=model_predicted,
            user_corrected=user_corrected,
            delta=round(delta, 2),
            delta_percent=round(delta_percent, 2),
            confidence_score=confidence_score,
            base_value_source=base_value_source,
            user_notes=user_notes
        )
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO feedback (
                timestamp, user_id, comic_title, issue_number, publisher, year,
                grade, edition, cgc, base_nm_value, model_predicted,
                user_corrected, delta, delta_percent, confidence_score,
                base_value_source, user_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry.timestamp, entry.user_id, entry.comic_title, entry.issue_number,
            entry.publisher, entry.year, entry.grade, entry.edition,
            entry.cgc, entry.base_nm_value, entry.model_predicted,
            entry.user_corrected, entry.delta, entry.delta_percent,
            entry.confidence_score, entry.base_value_source, entry.user_notes
        ))
        
        conn.commit()
        conn.close()
        
        return entry
    
    def get_all_feedback(self) -> List[Dict]:
        """Retrieve all feedback entries"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM feedback ORDER BY timestamp DESC')
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
    def get_feedback_count(self) -> int:
        """Get total number of feedback entries"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM feedback')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def analyze_by_grade(self) -> Dict:
        """Analyze correction patterns by grade"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT grade, 
                   COUNT(*) as count,
                   AVG(delta_percent) as avg_delta_percent,
                   MIN(delta_percent) as min_delta,
                   MAX(delta_percent) as max_delta
            FROM feedback
            GROUP BY grade
            ORDER BY count DESC
        ''')
        
        results = {}
        for row in cursor.fetchall():
            results[row[0]] = {
                "count": row[1],
                "avg_delta_percent": round(row[2], 2) if row[2] else 0,
                "min_delta": round(row[3], 2) if row[3] else 0,
                "max_delta": round(row[4], 2) if row[4] else 0,
            }
        
        conn.close()
        return results
    
    def analyze_by_edition(self) -> Dict:
        """Analyze correction patterns by edition"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT edition, 
                   COUNT(*) as count,
                   AVG(delta_percent) as avg_delta_percent
            FROM feedback
            GROUP BY edition
            ORDER BY count DESC
        ''')
        
        results = {}
        for row in cursor.fetchall():
            results[row[0]] = {
                "count": row[1],
                "avg_delta_percent": round(row[2], 2) if row[2] else 0,
            }
        
        conn.close()
        return results
    
    def analyze_by_publisher(self) -> Dict:
        """Analyze correction patterns by publisher"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT publisher, 
                   COUNT(*) as count,
                   AVG(delta_percent) as avg_delta_percent
            FROM feedback
            GROUP BY publisher
            ORDER BY count DESC
        ''')
        
        results = {}
        for row in cursor.fetchall():
            results[row[0]] = {
                "count": row[1],
                "avg_delta_percent": round(row[2], 2) if row[2] else 0,
            }
        
        conn.close()
        return results
    
    def analyze_by_cgc(self) -> Dict:
        """Analyze CGC vs raw corrections"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT cgc, 
                   COUNT(*) as count,
                   AVG(delta_percent) as avg_delta_percent
            FROM feedback
            GROUP BY cgc
        ''')
        
        results = {}
        for row in cursor.fetchall():
            key = "cgc" if row[0] else "raw"
            results[key] = {
                "count": row[1],
                "avg_delta_percent": round(row[2], 2) if row[2] else 0,
            }
        
        conn.close()
        return results
    
    def get_suggested_adjustments(self, min_samples: int = 5, excluded_user_ids: List[str] = None) -> Dict:
        """
        Analyze feedback and suggest weight adjustments
        
        Args:
            min_samples: Minimum samples needed to suggest an adjustment
            excluded_user_ids: List of user IDs to exclude from analysis
        
        Returns suggested multiplier adjustments based on user corrections.
        Only suggests changes when there are enough samples.
        """
        suggestions = {
            "grade_multipliers": {},
            "edition_multipliers": {},
            "publisher_adjustments": {},
            "cgc_premiums": {},
            "overall_stats": {},
            "excluded_users": excluded_user_ids or []
        }
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build exclusion clause
        exclusion_clause = ""
        params = []
        if excluded_user_ids:
            placeholders = ','.join(['?' for _ in excluded_user_ids])
            exclusion_clause = f" WHERE (user_id IS NULL OR user_id NOT IN ({placeholders}))"
            params = list(excluded_user_ids)
        
        # Overall stats
        cursor.execute(f'''
            SELECT COUNT(*), AVG(delta_percent), 
                   AVG(ABS(delta_percent))
            FROM feedback
            {exclusion_clause}
        ''', params)
        row = cursor.fetchone()
        suggestions["overall_stats"] = {
            "total_corrections": row[0],
            "avg_delta_percent": round(row[1], 2) if row[1] else 0,
            "avg_abs_delta_percent": round(row[2], 2) if row[2] else 0,
        }
        
        # Grade adjustments
        having_clause = exclusion_clause.replace("WHERE", "AND") if exclusion_clause else ""
        cursor.execute(f'''
            SELECT grade, COUNT(*), AVG(delta_percent)
            FROM feedback
            {exclusion_clause}
            GROUP BY grade
            HAVING COUNT(*) >= ?
        ''', params + [min_samples])
        
        for row in cursor.fetchall():
            grade, count, avg_delta = row
            if avg_delta and abs(avg_delta) > 5:  # Only suggest if >5% off
                # Calculate suggested multiplier adjustment
                # If we're undervaluing by 10%, multiply current by 1.10
                adjustment = 1 + (avg_delta / 100)
                suggestions["grade_multipliers"][grade] = {
                    "samples": count,
                    "avg_delta_percent": round(avg_delta, 2),
                    "suggested_adjustment": round(adjustment, 3),
                    "direction": "increase" if avg_delta > 0 else "decrease"
                }
        
        # Edition adjustments
        cursor.execute(f'''
            SELECT edition, COUNT(*), AVG(delta_percent)
            FROM feedback
            {exclusion_clause}
            GROUP BY edition
            HAVING COUNT(*) >= ?
        ''', params + [min_samples])
        
        for row in cursor.fetchall():
            edition, count, avg_delta = row
            if avg_delta and abs(avg_delta) > 5:
                adjustment = 1 + (avg_delta / 100)
                suggestions["edition_multipliers"][edition] = {
                    "samples": count,
                    "avg_delta_percent": round(avg_delta, 2),
                    "suggested_adjustment": round(adjustment, 3),
                    "direction": "increase" if avg_delta > 0 else "decrease"
                }
        
        # Publisher adjustments
        cursor.execute(f'''
            SELECT publisher, COUNT(*), AVG(delta_percent)
            FROM feedback
            {exclusion_clause}
            GROUP BY publisher
            HAVING COUNT(*) >= ?
        ''', params + [min_samples])
        
        for row in cursor.fetchall():
            publisher, count, avg_delta = row
            if avg_delta and abs(avg_delta) > 5:
                adjustment = 1 + (avg_delta / 100)
                suggestions["publisher_adjustments"][publisher] = {
                    "samples": count,
                    "avg_delta_percent": round(avg_delta, 2),
                    "suggested_adjustment": round(adjustment, 3),
                    "direction": "increase" if avg_delta > 0 else "decrease"
                }
        
        # CGC adjustments
        cursor.execute('''
            SELECT cgc, COUNT(*), AVG(delta_percent)
            FROM feedback
            GROUP BY cgc
            HAVING COUNT(*) >= ?
        ''', (min_samples,))
        
        for row in cursor.fetchall():
            cgc_status, count, avg_delta = row
            if avg_delta and abs(avg_delta) > 5:
                adjustment = 1 + (avg_delta / 100)
                key = "cgc" if cgc_status else "raw"
                suggestions["cgc_premiums"][key] = {
                    "samples": count,
                    "avg_delta_percent": round(avg_delta, 2),
                    "suggested_adjustment": round(adjustment, 3),
                    "direction": "increase" if avg_delta > 0 else "decrease"
                }
        
        conn.close()
        return suggestions
    
    def generate_report(self) -> Dict:
        """Generate a full analysis report"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_feedback": self.get_feedback_count(),
            "by_grade": self.analyze_by_grade(),
            "by_edition": self.analyze_by_edition(),
            "by_publisher": self.analyze_by_publisher(),
            "by_cgc": self.analyze_by_cgc(),
            "suggested_adjustments": self.get_suggested_adjustments(),
        }
        
        # Save report
        with open(ANALYSIS_REPORT, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report
    
    def print_summary(self):
        """Print a human-readable summary"""
        report = self.generate_report()
        
        print("=" * 60)
        print("FEEDBACK ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"\nTotal corrections logged: {report['total_feedback']}")
        
        if report['total_feedback'] == 0:
            print("\nNo feedback data yet. Start using the app and correct valuations!")
            return
        
        stats = report['suggested_adjustments']['overall_stats']
        print(f"\nOverall accuracy:")
        print(f"  Average delta: {stats['avg_delta_percent']:+.1f}%")
        print(f"  Average absolute error: {stats['avg_abs_delta_percent']:.1f}%")
        
        # Grade analysis
        if report['by_grade']:
            print("\n📊 By Grade:")
            for grade, data in sorted(report['by_grade'].items(), key=lambda x: x[1]['count'], reverse=True)[:5]:
                print(f"  {grade}: {data['count']} samples, avg delta {data['avg_delta_percent']:+.1f}%")
        
        # Suggested adjustments
        suggestions = report['suggested_adjustments']
        
        if suggestions['grade_multipliers']:
            print("\n💡 Suggested Grade Adjustments:")
            for grade, data in suggestions['grade_multipliers'].items():
                print(f"  {grade}: {data['direction']} by {abs(data['avg_delta_percent']):.1f}% (based on {data['samples']} samples)")
        
        if suggestions['edition_multipliers']:
            print("\n💡 Suggested Edition Adjustments:")
            for edition, data in suggestions['edition_multipliers'].items():
                print(f"  {edition}: {data['direction']} by {abs(data['avg_delta_percent']):.1f}% (based on {data['samples']} samples)")


def apply_suggestions_to_model(logger: FeedbackLogger, model, min_samples: int = 10, auto_save: bool = False):
    """
    Apply suggested adjustments from feedback to the model
    
    Args:
        logger: FeedbackLogger instance
        model: ValuationModel instance
        min_samples: Minimum samples needed to apply adjustment
        auto_save: Whether to automatically save weights
    """
    suggestions = logger.get_suggested_adjustments(min_samples=min_samples)
    
    print("\n🔧 Applying Suggested Adjustments")
    print("-" * 40)
    
    applied = 0
    
    # Apply grade adjustments
    for grade, data in suggestions['grade_multipliers'].items():
        current = model.get_weight('grade_multipliers', grade)
        if current:
            new_value = current * data['suggested_adjustment']
            print(f"Grade {grade}: {current:.3f} → {new_value:.3f}")
            model.adjust_weight('grade_multipliers', grade, round(new_value, 3))
            applied += 1
    
    # Apply edition adjustments
    for edition, data in suggestions['edition_multipliers'].items():
        current = model.get_weight('edition_multipliers', edition)
        if current:
            new_value = current * data['suggested_adjustment']
            print(f"Edition {edition}: {current:.3f} → {new_value:.3f}")
            model.adjust_weight('edition_multipliers', edition, round(new_value, 3))
            applied += 1
    
    if applied > 0 and auto_save:
        model.save_weights()
        print(f"\n✅ Applied {applied} adjustments and saved weights")
    elif applied > 0:
        print(f"\n⚠️  Applied {applied} adjustments (not saved)")
        print("   Call model.save_weights() to persist changes")
    else:
        print("\nNo adjustments needed based on current feedback")


# Test with sample data
def test_feedback_logger():
    """Test the feedback logger with sample corrections"""
    logger = FeedbackLogger("test_feedback.db")
    
    print("=" * 60)
    print("FEEDBACK LOGGER TEST")
    print("=" * 60)
    
    # Log some sample corrections
    sample_corrections = [
        {"comic_title": "Amazing Spider-Man", "issue_number": "300", "grade": "VF", 
         "model_predicted": 900.00, "user_corrected": 850.00, "edition": "direct",
         "publisher": "Marvel Comics", "year": 1988},
        {"comic_title": "Amazing Spider-Man", "issue_number": "300", "grade": "VF", 
         "model_predicted": 900.00, "user_corrected": 825.00, "edition": "newsstand",
         "publisher": "Marvel Comics", "year": 1988},
        {"comic_title": "Batman", "issue_number": "423", "grade": "NM", 
         "model_predicted": 250.00, "user_corrected": 300.00, "edition": "direct",
         "publisher": "DC Comics", "year": 1988},
        {"comic_title": "X-Men", "issue_number": "1", "grade": "NM", 
         "model_predicted": 45.00, "user_corrected": 40.00, "edition": "direct",
         "publisher": "Marvel Comics", "year": 1991},
        {"comic_title": "Spawn", "issue_number": "1", "grade": "NM", 
         "model_predicted": 125.00, "user_corrected": 100.00, "edition": "direct",
         "publisher": "Image Comics", "year": 1992, "cgc": True},
    ]
    
    print("\n📝 Logging sample corrections...")
    for correction in sample_corrections:
        entry = logger.log_correction(**correction)
        print(f"   {entry.comic_title} #{entry.issue_number}: ${entry.model_predicted} → ${entry.user_corrected} ({entry.delta_percent:+.1f}%)")
    
    print(f"\n✅ Logged {len(sample_corrections)} corrections")
    
    # Generate and print summary
    logger.print_summary()
    
    # Clean up test database
    os.remove("test_feedback.db")
    print("\n(Test database cleaned up)")


if __name__ == "__main__":
    test_feedback_logger()
