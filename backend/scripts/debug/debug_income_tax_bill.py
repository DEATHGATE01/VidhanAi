"""Debug ministry and date extraction for Income Tax Bill"""
import requests
from bs4 import BeautifulSoup
import re

url = "https://prsindia.org/billtrack/the-income-tax-no2-bill-2025"

print(f"Testing: The Income-Tax (No.2) Bill, 2025")
print(f"URL: {url}")
print(f"{'='*80}\n")

try:
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Check for ministry
    print("1. MINISTRY CHECK:")
    ministry_field = soup.find('div', class_='field-name-field-ministry')
    if ministry_field:
        print(f"   ✅ Found ministry field div")
        ministry_items = ministry_field.find('div', class_='field-items')
        if ministry_items:
            ministry = ministry_items.get_text(strip=True)
            print(f"   ✅ Found ministry: '{ministry}'")
        else:
            print(f"   ⚠️ Found ministry field but no field-items div")
            print(f"   Full HTML of ministry field:")
            print(ministry_field.prettify())
    else:
        print(f"   ❌ No ministry field found with class 'field-name-field-ministry'")
        # Search for any div containing "Ministry" text
        all_divs_with_ministry = soup.find_all(string=re.compile(r'Ministry', re.IGNORECASE))
        print(f"\n   Found {len(all_divs_with_ministry)} elements containing 'Ministry':")
        for elem in all_divs_with_ministry[:3]:
            parent = elem.parent
            print(f"   - Tag: {parent.name}, Class: {parent.get('class')}, Text: {elem[:50]}")
    
    # Check for dates
    print("\n2. DATE CHECK:")
    date_fields = soup.find_all('div', class_='entity-field-collection-item')
    print(f"   Found {len(date_fields)} entity-field-collection-item divs")
    
    for i, field in enumerate(date_fields[:5]):
        status_text = field.get_text(strip=True)
        print(f"\n   Field {i+1}:")
        print(f"   Text: {status_text[:150]}")
        
        if 'Introduced' in status_text or 'Passed' in status_text:
            date_match = re.search(r'([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})', status_text)
            if date_match:
                print(f"   ✅ Date found: {date_match.group(1)}")
            else:
                print(f"   ⚠️ 'Introduced/Passed' found but no date pattern matched")
                # Try alternative date patterns
                alt_date = re.search(r'(\d{1,2}\s+[A-Z][a-z]+\s+\d{4})', status_text)
                if alt_date:
                    print(f"   ✅ Alternative date pattern: {alt_date.group(1)}")
    
    # Check for status details
    print("\n3. STATUS DETAILS CHECK:")
    status_details = soup.find_all('div', class_='field-name-field-own-status-details')
    print(f"   Found {len(status_details)} field-name-field-own-status-details divs")
    for detail in status_details[:2]:
        print(f"   Text: {detail.get_text(strip=True)[:100]}...")
    
    # Check ALL divs with 'field' class
    print("\n4. ALL FIELD DIVS (first 10):")
    field_divs = soup.find_all('div', class_=re.compile(r'field'))[:10]
    for div in field_divs:
        classes = div.get('class', [])
        text = div.get_text(strip=True)[:80]
        if text:
            print(f"   Classes: {classes}")
            print(f"   Text: {text}...\n")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*80}")
print("Debug complete!")
