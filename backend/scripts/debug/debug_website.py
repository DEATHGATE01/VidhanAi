"""
Debug script to see current PRS website HTML structure
"""
import requests
from bs4 import BeautifulSoup

url = "https://prsindia.org/billtrack"
print(f"🌐 Fetching {url}\n")

try:
    response = requests.get(url, timeout=30, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Check for different table patterns
    print("🔍 Looking for tables...")
    tables = soup.find_all('table')
    print(f"   Found {len(tables)} table(s)\n")
    
    for i, table in enumerate(tables[:3]):
        print(f"📋 Table {i+1}:")
        print(f"   Classes: {table.get('class', 'None')}")
        print(f"   ID: {table.get('id', 'None')}")
        rows = table.find_all('tr')
        print(f"   Rows: {len(rows)}")
        if rows:
            first_row = rows[0]
            cells = first_row.find_all(['th', 'td'])
            print(f"   First row cells: {[cell.get_text(strip=True)[:30] for cell in cells[:5]]}")
        print()
    
    # Check for divs that might contain bill data
    print("\n🔍 Looking for bill containers...")
    bill_divs = soup.find_all('div', class_=lambda x: x and ('bill' in x.lower() or 'track' in x.lower()))
    print(f"   Found {len(bill_divs)} potential bill divs")
    
    # Check for specific data structures
    print("\n🔍 Looking for views/drupal structures...")
    views_table = soup.find('table', class_='views-table')
    print(f"   views-table: {'Found' if views_table else 'Not found'}")
    
    views_view = soup.find('div', class_=lambda x: x and 'views-view' in str(x))
    print(f"   views-view div: {'Found' if views_view else 'Not found'}")
    
    # Save HTML for manual inspection
    with open('prs_page_debug.html', 'w', encoding='utf-8') as f:
        f.write(soup.prettify())
    print(f"\n💾 Saved full HTML to prs_page_debug.html")
    
except Exception as e:
    print(f"❌ Error: {e}")
