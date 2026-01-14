"""
CollectionCalc Database Setup
Creates SQLite database for comic book pricing lookups
"""

import sqlite3
import os

DB_PATH = "comics_pricing.db"

def create_database():
    """Create the comics pricing database with all necessary tables"""
    
    # Remove existing database if it exists
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed existing database: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Main comics table - stores base NM (Near Mint) values
    cursor.execute('''
        CREATE TABLE comics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            title_normalized TEXT NOT NULL,  -- lowercase, no "the", standardized
            issue_number TEXT NOT NULL,
            publisher TEXT,
            year INTEGER,
            nm_value DECIMAL(10,2),          -- Near Mint base value
            vf_value DECIMAL(10,2),          -- Very Fine value (if available)
            fn_value DECIMAL(10,2),          -- Fine value (if available)
            source TEXT,                      -- Where we got this price
            last_updated DATE,
            notes TEXT,
            UNIQUE(title_normalized, issue_number, publisher)
        )
    ''')
    
    # Grade multipliers - convert NM price to other grades
    cursor.execute('''
        CREATE TABLE grade_multipliers (
            grade TEXT PRIMARY KEY,
            grade_numeric DECIMAL(3,1),
            multiplier DECIMAL(4,2),
            description TEXT
        )
    ''')
    
    # Insert standard grade multipliers
    grade_data = [
        ('MT', 10.0, 1.50, 'Mint - Perfect condition'),
        ('NM+', 9.6, 1.20, 'Near Mint+ - Almost perfect'),
        ('NM', 9.4, 1.00, 'Near Mint - Base reference grade'),
        ('NM-', 9.2, 0.90, 'Near Mint- - Minor imperfections'),
        ('VF/NM', 9.0, 0.85, 'Very Fine/Near Mint'),
        ('VF+', 8.5, 0.80, 'Very Fine+'),
        ('VF', 8.0, 0.75, 'Very Fine'),
        ('VF-', 7.5, 0.70, 'Very Fine-'),
        ('FN/VF', 7.0, 0.60, 'Fine/Very Fine'),
        ('FN+', 6.5, 0.55, 'Fine+'),
        ('FN', 6.0, 0.50, 'Fine'),
        ('FN-', 5.5, 0.45, 'Fine-'),
        ('VG/FN', 5.0, 0.40, 'Very Good/Fine'),
        ('VG+', 4.5, 0.35, 'Very Good+'),
        ('VG', 4.0, 0.30, 'Very Good'),
        ('VG-', 3.5, 0.25, 'Very Good-'),
        ('GD/VG', 3.0, 0.22, 'Good/Very Good'),
        ('GD+', 2.5, 0.18, 'Good+'),
        ('GD', 2.0, 0.15, 'Good'),
        ('GD-', 1.8, 0.12, 'Good-'),
        ('FR/GD', 1.5, 0.10, 'Fair/Good'),
        ('FR', 1.0, 0.08, 'Fair'),
        ('PR', 0.5, 0.05, 'Poor'),
    ]
    
    cursor.executemany('''
        INSERT INTO grade_multipliers (grade, grade_numeric, multiplier, description)
        VALUES (?, ?, ?, ?)
    ''', grade_data)
    
    # Special editions multipliers (newsstand, variants, etc.)
    cursor.execute('''
        CREATE TABLE edition_multipliers (
            edition_type TEXT PRIMARY KEY,
            multiplier DECIMAL(4,2),
            description TEXT
        )
    ''')
    
    edition_data = [
        ('direct', 1.00, 'Direct Edition - Standard retail'),
        ('newsstand', 1.25, 'Newsstand Edition - 25% premium'),
        ('newsstand_rare', 1.50, 'Rare Newsstand (post-1995) - 50% premium'),
        ('variant', 1.50, 'Variant Cover - 50% premium average'),
        ('signed', 2.00, 'Signed by creator - 100% premium'),
        ('cgc', 1.30, 'CGC Graded - 30% premium for certification'),
        ('first_print', 1.00, 'First Print - Standard'),
        ('second_print', 0.50, 'Second Print - 50% of first'),
        ('later_print', 0.30, 'Later Print - 30% of first'),
    ]
    
    cursor.executemany('''
        INSERT INTO edition_multipliers (edition_type, multiplier, description)
        VALUES (?, ?, ?)
    ''', edition_data)
    
    # Key issues table - comics worth significantly more
    cursor.execute('''
        CREATE TABLE key_issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title_normalized TEXT NOT NULL,
            issue_number TEXT NOT NULL,
            reason TEXT,                      -- "First appearance of...", etc.
            premium_multiplier DECIMAL(4,2),  -- Additional multiplier for key status
            UNIQUE(title_normalized, issue_number)
        )
    ''')
    
    # Publisher aliases for matching
    cursor.execute('''
        CREATE TABLE publisher_aliases (
            alias TEXT PRIMARY KEY,
            canonical_name TEXT NOT NULL
        )
    ''')
    
    publisher_aliases = [
        ('marvel', 'Marvel Comics'),
        ('marvel comics', 'Marvel Comics'),
        ('marvel comics group', 'Marvel Comics'),
        ('dc', 'DC Comics'),
        ('dc comics', 'DC Comics'),
        ('detective comics', 'DC Comics'),
        ('image', 'Image Comics'),
        ('image comics', 'Image Comics'),
        ('dark horse', 'Dark Horse Comics'),
        ('dark horse comics', 'Dark Horse Comics'),
        ('idw', 'IDW Publishing'),
        ('idw publishing', 'IDW Publishing'),
        ('boom', 'BOOM! Studios'),
        ('boom!', 'BOOM! Studios'),
        ('boom! studios', 'BOOM! Studios'),
        ('valiant', 'Valiant Comics'),
        ('valiant comics', 'Valiant Comics'),
        ('archie', 'Archie Comics'),
        ('archie comics', 'Archie Comics'),
        ('dynamite', 'Dynamite Entertainment'),
        ('dynamite entertainment', 'Dynamite Entertainment'),
    ]
    
    cursor.executemany('''
        INSERT INTO publisher_aliases (alias, canonical_name)
        VALUES (?, ?)
    ''', publisher_aliases)
    
    # Create indexes for fast lookups
    cursor.execute('CREATE INDEX idx_title_normalized ON comics(title_normalized)')
    cursor.execute('CREATE INDEX idx_issue ON comics(issue_number)')
    cursor.execute('CREATE INDEX idx_publisher ON comics(publisher)')
    cursor.execute('CREATE INDEX idx_title_issue ON comics(title_normalized, issue_number)')
    
    conn.commit()
    conn.close()
    
    print(f"✅ Database created: {DB_PATH}")
    print(f"   - comics table (empty, ready for data)")
    print(f"   - grade_multipliers table ({len(grade_data)} grades)")
    print(f"   - edition_multipliers table ({len(edition_data)} editions)")
    print(f"   - key_issues table (empty, ready for data)")
    print(f"   - publisher_aliases table ({len(publisher_aliases)} aliases)")


def get_database_stats():
    """Print current database statistics"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM comics")
    comic_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT publisher) FROM comics")
    publisher_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT title_normalized) FROM comics")
    title_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n📊 Database Statistics:")
    print(f"   Total comics: {comic_count:,}")
    print(f"   Unique titles: {title_count:,}")
    print(f"   Publishers: {publisher_count}")


if __name__ == "__main__":
    create_database()
    get_database_stats()
