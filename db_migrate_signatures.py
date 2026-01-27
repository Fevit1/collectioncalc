"""
Database migration for creator signature reference database.
Run this script on Render shell to create the signature tables.

Usage:
    python db_migrate_signatures.py
"""

import os
import psycopg2

def migrate():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not set")
        return False
    
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    
    try:
        # Create creator_signatures table
        print("Creating creator_signatures table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS creator_signatures (
                id SERIAL PRIMARY KEY,
                creator_name VARCHAR(255) NOT NULL,
                role VARCHAR(50),
                reference_image_url TEXT,
                signature_style TEXT,
                verified BOOLEAN DEFAULT FALSE,
                source VARCHAR(255),
                notes TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        print("✅ creator_signatures table created")
        
        # Create index on creator_name for fast lookups
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_creator_signatures_name 
            ON creator_signatures (LOWER(creator_name))
        """)
        print("✅ Index on creator_name created")
        
        # Create signature_matches table for tracking successful matches
        print("Creating signature_matches table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS signature_matches (
                id SERIAL PRIMARY KEY,
                sale_id INTEGER REFERENCES market_sales(id),
                signature_id INTEGER REFERENCES creator_signatures(id),
                confidence DECIMAL(3,2),
                match_method VARCHAR(50),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        print("✅ signature_matches table created")
        
        # Insert some initial creator data (no images yet)
        # These are common comic creators whose signatures appear frequently
        print("Inserting initial creator records...")
        
        creators = [
            # Artists
            ('Jim Lee', 'artist', 'Large flowing signature, often dated'),
            ('Todd McFarlane', 'artist', 'Distinctive loops, often includes spider'),
            ('Rob Liefeld', 'artist', 'Block letters, energetic style'),
            ('John Romita Jr.', 'artist', 'Compact, professional'),
            ('John Romita Sr.', 'artist', 'Classic cursive style'),
            ('Neal Adams', 'artist', 'Elegant cursive'),
            ('Frank Miller', 'artist', 'Bold, angular'),
            ('George Pérez', 'artist', 'Detailed, often includes date'),
            ('Jim Steranko', 'artist', 'Stylized, artistic'),
            ('Jack Kirby', 'artist', 'Simple block signature'),
            ('Steve Ditko', 'artist', 'Rare, simple signature'),
            ('John Byrne', 'artist', 'Clean, readable'),
            ('Art Adams', 'artist', 'Detailed, often with character sketch'),
            ('Alex Ross', 'artist', 'Elegant, sometimes painted'),
            ('J. Scott Campbell', 'artist', 'Stylized, often with date'),
            ('Adam Hughes', 'artist', 'Clean, often AH monogram'),
            ('Mike Mignola', 'artist', 'Distinctive, sometimes with Hellboy sketch'),
            ('Jae Lee', 'artist', 'Minimalist'),
            ('Greg Capullo', 'artist', 'Flowing, energetic'),
            ('Ivan Reis', 'artist', 'Professional, often dated'),
            
            # Writers
            ('Stan Lee', 'writer', 'Large, iconic EXCELSIOR sometimes added'),
            ('Chris Claremont', 'writer', 'Neat cursive'),
            ('Brian Michael Bendis', 'writer', 'Bold, readable'),
            ('Geoff Johns', 'writer', 'Clean, professional'),
            ('Grant Morrison', 'writer', 'Artistic, sometimes with sigil'),
            ('Alan Moore', 'writer', 'Rare, distinctive'),
            ('Neil Gaiman', 'writer', 'Elegant cursive'),
            ('Jonathan Hickman', 'writer', 'Modern, clean'),
            ('Scott Snyder', 'writer', 'Energetic, often with personal note'),
            ('Mark Millar', 'writer', 'Bold, readable'),
            ('Ed Brubaker', 'writer', 'Professional'),
            ('Tom King', 'writer', 'Clean, modern'),
            ('James Tynion IV', 'writer', 'Contemporary style'),
            
            # Cover Artists (not interior)
            ('Stanley "Artgerm" Lau', 'cover_artist', 'Detailed, often ARTGERM'),
            ('Gabriele Dell\'Otto', 'cover_artist', 'European style'),
            ('Peach Momoko', 'cover_artist', 'Japanese characters sometimes'),
            
            # Legends (often higher value signatures)
            ('Bob Kane', 'creator', 'Historic, rare'),
            ('Bill Finger', 'creator', 'Extremely rare'),
            ('Jerry Siegel', 'creator', 'Historic Superman creator'),
            ('Joe Shuster', 'creator', 'Historic Superman creator'),
        ]
        
        for name, role, style in creators:
            cur.execute("""
                INSERT INTO creator_signatures (creator_name, role, signature_style, verified)
                VALUES (%s, %s, %s, FALSE)
                ON CONFLICT DO NOTHING
            """, (name, role, style))
        
        print(f"✅ Inserted {len(creators)} creator records")
        
        conn.commit()
        print("\n✅ Migration complete!")
        
        # Show summary
        cur.execute("SELECT COUNT(*) FROM creator_signatures")
        count = cur.fetchone()[0]
        print(f"\n📊 Total creators in database: {count}")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def show_stats():
    """Show current signature database stats."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not set")
        return
    
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT role, COUNT(*) as count
            FROM creator_signatures
            GROUP BY role
            ORDER BY count DESC
        """)
        roles = cur.fetchall()
        
        print("\n📊 Signature Database Stats:")
        print("-" * 30)
        for role, count in roles:
            print(f"  {role}: {count}")
        
        cur.execute("""
            SELECT COUNT(*) FROM creator_signatures WHERE reference_image_url IS NOT NULL
        """)
        with_images = cur.fetchone()[0]
        print(f"\n  With reference images: {with_images}")
        
        cur.execute("""
            SELECT COUNT(*) FROM creator_signatures WHERE verified = TRUE
        """)
        verified = cur.fetchone()[0]
        print(f"  Verified signatures: {verified}")
        
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'stats':
        show_stats()
    else:
        migrate()
        show_stats()
