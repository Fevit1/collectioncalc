"""
CollectionCalc - MyComicShop Scraper
Scrapes comic pricing data from mycomicshop.com

LEGAL NOTE: This is for personal/educational use.
For production, consider partnering with pricing APIs.
"""

import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import re
import json
from datetime import datetime
from urllib.parse import urljoin, quote

# Configuration
DB_PATH = "comics_pricing.db"
BASE_URL = "https://www.mycomicshop.com"
DELAY_BETWEEN_REQUESTS = 2  # Be respectful to the server

# Headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


def normalize_title(title):
    """Normalize title for consistent matching"""
    if not title:
        return ""
    
    # Lowercase
    normalized = title.lower().strip()
    
    # Remove common prefixes
    prefixes_to_remove = ['the ', 'a ']
    for prefix in prefixes_to_remove:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
    
    # Standardize punctuation
    normalized = re.sub(r'[:\-–—]', ' ', normalized)
    normalized = re.sub(r'[\'\"''""]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized.strip()


def extract_issue_number(issue_text):
    """Extract issue number from various formats"""
    if not issue_text:
        return ""
    
    # Handle formats like "#1", "No. 1", "Issue 1", etc.
    patterns = [
        r'#(\d+[a-zA-Z]?)',      # #1, #1A
        r'No\.?\s*(\d+)',         # No. 1, No 1
        r'Issue\s*(\d+)',         # Issue 1
        r'^(\d+)$',               # Just the number
        r'\((\d+)\)',             # (1)
    ]
    
    for pattern in patterns:
        match = re.search(pattern, str(issue_text), re.IGNORECASE)
        if match:
            return match.group(1)
    
    return str(issue_text).strip()


def extract_price(price_text):
    """Extract numeric price from text like '$45.00' or '45'"""
    if not price_text:
        return None
    
    # Remove $ and commas, find the number
    match = re.search(r'[\$]?\s*([\d,]+\.?\d*)', str(price_text))
    if match:
        price_str = match.group(1).replace(',', '')
        try:
            return float(price_str)
        except ValueError:
            return None
    return None


def get_publisher_search_urls():
    """Get URLs for major publishers on MyComicShop"""
    return {
        'Marvel Comics': '/search?TID=47072',
        'DC Comics': '/search?TID=109995',
        'Image Comics': '/search?TID=95279',
        'Dark Horse Comics': '/search?TID=100264',
        'IDW Publishing': '/search?TID=104379',
        'BOOM! Studios': '/search?TID=204890',
        'Valiant Comics': '/search?TID=87829',
        'Archie Comics': '/search?TID=74740',
    }


def scrape_mycomicshop_series(series_url, publisher="Unknown"):
    """
    Scrape all issues from a comic series page
    Returns list of comic data dictionaries
    """
    comics = []
    
    try:
        response = requests.get(series_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # MyComicShop structure - look for issue listings
        # This will need adjustment based on actual page structure
        issue_rows = soup.find_all('tr', class_='hoverable')
        
        for row in issue_rows:
            try:
                # Extract title/issue
                title_elem = row.find('a', class_='issue')
                if not title_elem:
                    continue
                    
                full_title = title_elem.get_text(strip=True)
                
                # Extract price
                price_elem = row.find('td', class_='price')
                if price_elem:
                    price = extract_price(price_elem.get_text())
                else:
                    price = None
                
                # Parse title and issue number
                # Format is usually "Amazing Spider-Man #1"
                title_match = re.match(r'(.+?)\s*#(\d+[a-zA-Z]?)', full_title)
                if title_match:
                    title = title_match.group(1).strip()
                    issue = title_match.group(2)
                else:
                    title = full_title
                    issue = "1"
                
                if title and price:
                    comics.append({
                        'title': title,
                        'title_normalized': normalize_title(title),
                        'issue_number': issue,
                        'publisher': publisher,
                        'nm_value': price,
                        'source': 'mycomicshop.com',
                        'last_updated': datetime.now().strftime('%Y-%m-%d')
                    })
                    
            except Exception as e:
                print(f"  Error parsing row: {e}")
                continue
                
    except Exception as e:
        print(f"Error scraping {series_url}: {e}")
    
    return comics


def scrape_search_results(search_query, max_pages=5):
    """
    Search MyComicShop and scrape results
    """
    comics = []
    
    # URL encode the search query
    encoded_query = quote(search_query)
    
    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}/search?q={encoded_query}&page={page}"
        print(f"  Scraping page {page}: {url}")
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find comic listings
            listings = soup.find_all('div', class_='listing')
            
            if not listings:
                print(f"  No more results on page {page}")
                break
            
            for listing in listings:
                try:
                    # This structure will need adjustment based on actual HTML
                    title_elem = listing.find('a', class_='title')
                    price_elem = listing.find('span', class_='price')
                    
                    if title_elem and price_elem:
                        full_title = title_elem.get_text(strip=True)
                        price = extract_price(price_elem.get_text())
                        
                        # Parse title and issue
                        title_match = re.match(r'(.+?)\s*#(\d+[a-zA-Z]?)', full_title)
                        if title_match:
                            title = title_match.group(1).strip()
                            issue = title_match.group(2)
                        else:
                            continue
                        
                        comics.append({
                            'title': title,
                            'title_normalized': normalize_title(title),
                            'issue_number': issue,
                            'nm_value': price,
                            'source': 'mycomicshop.com',
                            'last_updated': datetime.now().strftime('%Y-%m-%d')
                        })
                        
                except Exception as e:
                    continue
            
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
        except Exception as e:
            print(f"  Error on page {page}: {e}")
            break
    
    return comics


def save_comics_to_db(comics):
    """Save scraped comics to the database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    saved = 0
    updated = 0
    
    for comic in comics:
        try:
            # Try to insert, update on conflict
            cursor.execute('''
                INSERT INTO comics (title, title_normalized, issue_number, publisher, nm_value, source, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(title_normalized, issue_number, publisher) 
                DO UPDATE SET 
                    nm_value = excluded.nm_value,
                    last_updated = excluded.last_updated
            ''', (
                comic.get('title'),
                comic.get('title_normalized'),
                comic.get('issue_number'),
                comic.get('publisher', 'Unknown'),
                comic.get('nm_value'),
                comic.get('source'),
                comic.get('last_updated')
            ))
            
            if cursor.rowcount > 0:
                saved += 1
                
        except Exception as e:
            print(f"  Error saving {comic.get('title')} #{comic.get('issue_number')}: {e}")
    
    conn.commit()
    conn.close()
    
    return saved


def scrape_popular_titles():
    """
    Scrape the most popular/common comic titles
    These are the ones most likely to be in someone's collection
    """
    
    popular_titles = [
        # Marvel
        "Amazing Spider-Man",
        "Uncanny X-Men", 
        "X-Men",
        "Avengers",
        "Fantastic Four",
        "Iron Man",
        "Captain America",
        "Thor",
        "Hulk",
        "Daredevil",
        "Wolverine",
        "Spider-Man",
        "Spawn",
        
        # DC
        "Batman",
        "Superman",
        "Wonder Woman",
        "Justice League",
        "Detective Comics",
        "Action Comics",
        "Flash",
        "Green Lantern",
        "Aquaman",
        
        # Image
        "Spawn",
        "Invincible",
        "Walking Dead",
        "Saga",
        
        # Other popular
        "Teenage Mutant Ninja Turtles",
        "Star Wars",
        "Transformers",
    ]
    
    all_comics = []
    
    for title in popular_titles:
        print(f"\n📚 Scraping: {title}")
        comics = scrape_search_results(title, max_pages=10)
        print(f"   Found {len(comics)} issues")
        all_comics.extend(comics)
        
        # Save periodically
        if len(all_comics) >= 100:
            saved = save_comics_to_db(all_comics)
            print(f"   💾 Saved {saved} comics to database")
            all_comics = []
        
        time.sleep(DELAY_BETWEEN_REQUESTS * 2)  # Extra delay between titles
    
    # Save remaining
    if all_comics:
        saved = save_comics_to_db(all_comics)
        print(f"\n💾 Saved final {saved} comics to database")


# Alternative: Manual data import
def import_from_json(json_file):
    """
    Import comic data from a JSON file
    Format: [{"title": "...", "issue": "...", "publisher": "...", "nm_value": 0.00}, ...]
    """
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    comics = []
    for item in data:
        comics.append({
            'title': item.get('title'),
            'title_normalized': normalize_title(item.get('title')),
            'issue_number': extract_issue_number(item.get('issue')),
            'publisher': item.get('publisher', 'Unknown'),
            'nm_value': item.get('nm_value') or item.get('price'),
            'source': 'json_import',
            'last_updated': datetime.now().strftime('%Y-%m-%d')
        })
    
    saved = save_comics_to_db(comics)
    print(f"✅ Imported {saved} comics from {json_file}")
    return saved


def import_from_csv(csv_file):
    """
    Import comic data from a CSV file
    Expected columns: title, issue, publisher, nm_value
    """
    import csv
    
    comics = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            comics.append({
                'title': row.get('title'),
                'title_normalized': normalize_title(row.get('title')),
                'issue_number': extract_issue_number(row.get('issue')),
                'publisher': row.get('publisher', 'Unknown'),
                'nm_value': extract_price(row.get('nm_value') or row.get('price')),
                'source': 'csv_import',
                'last_updated': datetime.now().strftime('%Y-%m-%d')
            })
    
    saved = save_comics_to_db(comics)
    print(f"✅ Imported {saved} comics from {csv_file}")
    return saved


if __name__ == "__main__":
    print("=" * 50)
    print("CollectionCalc - MyComicShop Scraper")
    print("=" * 50)
    
    print("\nOptions:")
    print("1. Scrape popular titles (takes ~30 mins)")
    print("2. Search specific title")
    print("3. Import from JSON file")
    print("4. Import from CSV file")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        print("\n⚠️  This will scrape MyComicShop for popular titles.")
        print("   Estimated time: 30-60 minutes")
        confirm = input("Continue? (y/n): ").strip().lower()
        if confirm == 'y':
            scrape_popular_titles()
    
    elif choice == "2":
        title = input("Enter comic title to search: ").strip()
        if title:
            print(f"\nSearching for: {title}")
            comics = scrape_search_results(title, max_pages=5)
            saved = save_comics_to_db(comics)
            print(f"\n✅ Found and saved {saved} issues")
    
    elif choice == "3":
        json_file = input("Enter JSON file path: ").strip()
        import_from_json(json_file)
    
    elif choice == "4":
        csv_file = input("Enter CSV file path: ").strip()
        import_from_csv(csv_file)
    
    else:
        print("Invalid choice")
