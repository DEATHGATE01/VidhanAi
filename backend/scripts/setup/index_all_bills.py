"""Index all PRS bills into database"""
import sys
sys.path.append('.')

from app import create_app
from db_service import index_all_prs_bills

print("=" * 60)
print("🚀 INDEXING ALL PRS BILLS")
print("=" * 60)

app = create_app()
result = index_all_prs_bills(app)

print("\n" + "=" * 60)
print("✅ INDEXING COMPLETE")
print("=" * 60)
print(f"New bills added: {result.get('new_count', 0)}")
print(f"Existing bills updated: {result.get('updated_count', 0)}")
print(f"Total bills in database: {result.get('total_count', 0)}")
