"""Check PRS BillTrack pagination"""
import requests
from bs4 import BeautifulSoup

print("Checking PRS BillTrack page structure...")
resp = requests.get('https://prsindia.org/billtrack')
soup = BeautifulSoup(resp.content, 'html.parser')

# Count bills on first page
rows = soup.find_all('div', class_='views-row')
print(f"✅ Bills on first page: {len(rows)}")

# Check for pagination elements
pager = soup.find('ul', class_='pager')
if pager:
    print(f"✅ Pagination found!")
    pages = pager.find_all('li')
    print(f"   Pages available: {len(pages)}")
    
    # Check for next/last links
    next_link = pager.find('a', rel='next')
    last_link = pager.find('li', class_='pager-last')
    
    if next_link:
        print(f"   Next page URL: {next_link.get('href')}")
    if last_link:
        last_a = last_link.find('a')
        if last_a:
            print(f"   Last page URL: {last_a.get('href')}")
else:
    print("❌ No pagination found")

# Check for total count indicator
view_header = soup.find('div', class_='view-header')
if view_header:
    print(f"✅ View header: {view_header.get_text(strip=True)}")

# Check view footer for count
view_footer = soup.find('div', class_='view-footer')
if view_footer:
    print(f"✅ View footer: {view_footer.get_text(strip=True)}")

print("\n📊 Summary:")
print(f"   - Bills visible on page 1: {len(rows)}")
print(f"   - Pagination exists: {pager is not None}")
