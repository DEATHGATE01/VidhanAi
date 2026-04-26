"""Check if ministry is available on list page"""
import requests
from bs4 import BeautifulSoup

print("Checking PRS BillTrack list page for ministry field...")
resp = requests.get('https://prsindia.org/billtrack')
soup = BeautifulSoup(resp.content, 'html.parser')

# Get first few bill rows
rows = soup.find_all('div', class_='views-row')[:5]

print(f"Checking first {len(rows)} bills:\n")

for idx, row in enumerate(rows, 1):
    # Title
    title_field = row.find('div', class_='views-field-title-field')
    title = title_field.get_text(strip=True) if title_field else 'N/A'
    
    # Check for ministry field
    ministry_field = row.find('div', class_='views-field-field-ministry') or \
                     row.find('div', class_='field-name-field-ministry')
    
    # Check ALL divs with 'views-field' class
    all_fields = row.find_all('div', class_=lambda x: x and 'views-field' in x)
    
    print(f"{idx}. {title[:60]}")
    print(f"   Ministry field found: {ministry_field is not None}")
    
    if ministry_field:
        print(f"   Ministry: {ministry_field.get_text(strip=True)}")
    
    print(f"   All field classes found:")
    for field in all_fields:
        classes = ' '.join(field.get('class', []))
        content = field.get_text(strip=True)[:50]
        print(f"     - {classes}: {content}")
    print()
