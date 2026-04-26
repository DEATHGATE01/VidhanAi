"""
Test scraping for gaming bill
"""
import sys
sys.path.insert(0, '.')

from src.scraping.prs_billtrack_scraper import PRSBillTrackScraper

print("🧪 Testing Gaming Bill scraping...")
scraper = PRSBillTrackScraper()

url = "https://prsindia.org/billtrack/the-promotion-and-regulation-of-online-gaming-bill-2025"
print(f"\n🌐 Fetching: {url}\n")

content = scraper.fetch_bill_content(url)

if content:
    print(f"\n✅ Content extracted:")
    print(f"   Full Text: {len(content.get('full_text', ''))} chars")
    print(f"   Sections: {len(content.get('sections', []))}")
    print(f"   Paragraphs: {len(content.get('paragraphs', []))}")
    print(f"   PDF Link: {content.get('pdf_link', 'None')}")
    
    if content.get('full_text'):
        print(f"\n📄 First 500 chars of full_text:")
        print(content['full_text'][:500])
    
    if content.get('paragraphs'):
        print(f"\n📋 Paragraphs found:")
        for i, para in enumerate(content['paragraphs'][:3]):
            print(f"   {i+1}. {para[:100]}...")
else:
    print("\n❌ No content extracted!")

scraper.close()
