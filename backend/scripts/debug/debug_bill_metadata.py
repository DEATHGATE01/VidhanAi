"""
Debug script to check gaming bill page structure
"""
import requests
from bs4 import BeautifulSoup

url = "https://prsindia.org/billtrack/the-promotion-and-regulation-of-online-gaming-bill-2025"
print(f"🌐 Fetching {url}\n")

response = requests.get(url, timeout=30, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

soup = BeautifulSoup(response.content, 'html.parser')

# Look for metadata fields
print("🔍 Looking for ministry and date information...\n")

# Try different metadata selectors
metadata_divs = soup.find_all('div', class_=lambda x: x and ('field' in x.lower() or 'meta' in x.lower()))
print(f"Found {len(metadata_divs)} potential metadata divs\n")

for div in metadata_divs[:20]:
    text = div.get_text(strip=True)
    if any(word in text.lower() for word in ['ministry', 'date', 'introduced', 'status']):
        print(f"Class: {div.get('class')}")
        print(f"Text: {text[:200]}")
        print("-" * 80)

# Look for any table or list with metadata
tables = soup.find_all('table')
print(f"\n\nFound {len(tables)} tables")
for i, table in enumerate(tables[:2]):
    print(f"\nTable {i+1}:")
    rows = table.find_all('tr')
    for row in rows[:5]:
        cells = row.find_all(['th', 'td'])
        if len(cells) >= 2:
            print(f"  {cells[0].get_text(strip=True)}: {cells[1].get_text(strip=True)}")
