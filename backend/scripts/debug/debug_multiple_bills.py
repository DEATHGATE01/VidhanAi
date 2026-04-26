"""Debug ministry and date extraction for multiple bills"""
from src.scraping.prs_billtrack_scraper import PRSBillTrackScraper
import requests
from bs4 import BeautifulSoup

# Test URLs for different bills
test_bills = [
    ("Gaming Bill", "https://prsindia.org/billtrack/the-promotion-and-regulation-of-online-gaming-bill-2025"),
    ("Tax Bill", "https://prsindia.org/billtrack/the-taxation-laws-amendment-bill-2024"),
    ("Constitution Bill", "https://prsindia.org/billtrack/the-constitution-one-hundred-and-twenty-ninth-amendment-bill-2024"),
]

scraper = PRSBillTrackScraper()

for bill_name, url in test_bills:
    print(f"\n{'='*80}")
    print(f"Testing: {bill_name}")
    print(f"URL: {url}")
    print(f"{'='*80}")
    
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check for ministry
        print("\n1. MINISTRY CHECK:")
        ministry_field = soup.find('div', class_='field-name-field-ministry')
        if ministry_field:
            ministry_items = ministry_field.find('div', class_='field-items')
            if ministry_items:
                ministry = ministry_items.get_text(strip=True)
                print(f"   ✅ Found ministry: {ministry}")
            else:
                print(f"   ⚠️ Found ministry field but no field-items div")
                print(f"   HTML: {ministry_field.prettify()[:300]}")
        else:
            print(f"   ❌ No ministry field found")
            # Check alternative ministry locations
            alt_ministry = soup.find('div', class_='field-ministry')
            if alt_ministry:
                print(f"   Found alternative: {alt_ministry.get_text(strip=True)}")
        
        # Check for dates
        print("\n2. DATE CHECK:")
        date_fields = soup.find_all('div', class_='entity-field-collection-item')
        print(f"   Found {len(date_fields)} entity-field-collection-item divs")
        
        for i, field in enumerate(date_fields[:3]):  # Check first 3
            status_text = field.get_text(strip=True)
            print(f"   Field {i+1}: {status_text[:100]}...")
            if 'Introduced' in status_text or 'Passed' in status_text:
                import re
                date_match = re.search(r'([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})', status_text)
                if date_match:
                    print(f"      ✅ Date found: {date_match.group(1)}")
                else:
                    print(f"      ⚠️ 'Introduced/Passed' found but no date pattern matched")
        
        # Check alternative date location
        print("\n3. ALTERNATIVE DATE LOCATIONS:")
        alt_dates = soup.find_all('div', class_='field-name-field-own-status-details')
        print(f"   Found {len(alt_dates)} field-name-field-own-status-details divs")
        for alt_date in alt_dates[:2]:
            print(f"   Text: {alt_date.get_text(strip=True)[:100]}...")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")

print(f"\n{'='*80}")
print("Debug complete!")
