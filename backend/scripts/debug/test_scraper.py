"""
Test script to debug scraper issues
"""
import sys
sys.path.insert(0, '.')

from src.scraping.prs_billtrack_scraper import PRSBillTrackScraper

print("🧪 Testing PRS scraper...")
scraper = PRSBillTrackScraper()

print("\n1️⃣ Testing fetch_bill_list()...")
bills = scraper.fetch_bill_list(max_items=10)

print(f"\n📊 Results: Found {len(bills)} bills")

if bills:
    print("\n✅ Sample bill:")
    print(f"   Title: {bills[0].get('title', 'N/A')}")
    print(f"   Ministry: {bills[0].get('ministry', 'N/A')}")
    print(f"   Status: {bills[0].get('status', 'N/A')}")
    print(f"   URL: {bills[0].get('url', 'N/A')}")
else:
    print("\n❌ No bills found! Scraper may be broken.")
    print("   Possible causes:")
    print("   - PRS website structure changed")
    print("   - Network issues")
    print("   - Website blocking requests")
