"""Export database data for EDA analysis"""
import sys
import os
import json
import pandas as pd

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app import create_app
from models import db, Bill, BillContent, BillSummary, SearchHistory, User

def export_data():
    app = create_app()
    
    with app.app_context():
        # Export Bills
        print("📊 Exporting Bills data...")
        bills = Bill.query.all()
        bills_data = []
        
        for bill in bills:
            bill_dict = {
                'id': bill.id,
                'bill_id': bill.bill_id,
                'title': bill.title,
                'ministry': bill.ministry,
                'status': bill.status,
                'url': bill.url,
                'introduction_date': bill.introduction_date.isoformat() if bill.introduction_date else None,
                'date_scraped': bill.date_scraped.isoformat() if bill.date_scraped else None,
                'last_updated': bill.last_updated.isoformat() if bill.last_updated else None,
                'has_content': bill.content is not None,
                'has_summary': bill.summary is not None,
            }
            
            # Add content metadata if available
            if bill.content:
                bill_dict['content_length'] = len(bill.content.full_text) if bill.content.full_text else 0
                bill_dict['num_sections'] = len(bill.content.sections) if bill.content.sections else 0
                bill_dict['num_paragraphs'] = len(bill.content.paragraphs) if bill.content.paragraphs else 0
                bill_dict['has_pdf'] = bill.content.pdf_link is not None
            else:
                bill_dict['content_length'] = 0
                bill_dict['num_sections'] = 0
                bill_dict['num_paragraphs'] = 0
                bill_dict['has_pdf'] = False
            
            # Add summary metadata if available
            if bill.summary:
                bill_dict['summary_length'] = len(bill.summary.summary) if bill.summary.summary else 0
                bill_dict['summary_type'] = bill.summary.summary_type
            else:
                bill_dict['summary_length'] = 0
                bill_dict['summary_type'] = None
                
            bills_data.append(bill_dict)
        
        # Create DataFrame
        df_bills = pd.DataFrame(bills_data)
        
        # Export to CSV
        df_bills.to_csv('data_export/bills.csv', index=False)
        print(f"✅ Exported {len(df_bills)} bills to data_export/bills.csv")
        
        # Export to JSON for detailed analysis
        with open('data_export/bills.json', 'w', encoding='utf-8') as f:
            json.dump(bills_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Exported bills to data_export/bills.json")
        
        # Export SearchHistory
        print("\n📊 Exporting Search History...")
        searches = SearchHistory.query.all()
        search_data = [{
            'id': s.id,
            'user_id': s.user_id,
            'keyword': s.keyword,
            'results_count': s.results_count,
            'timestamp': s.timestamp.isoformat()
        } for s in searches]
        
        df_searches = pd.DataFrame(search_data)
        df_searches.to_csv('data_export/search_history.csv', index=False)
        print(f"✅ Exported {len(df_searches)} searches to data_export/search_history.csv")
        
        # Print summary statistics
        print("\n" + "="*60)
        print("📈 DATA SUMMARY")
        print("="*60)
        print(f"\n📋 Total Bills: {len(bills)}")
        print(f"   - With Content: {df_bills['has_content'].sum()}")
        print(f"   - With Summary: {df_bills['has_summary'].sum()}")
        print(f"   - With Ministry: {df_bills['ministry'].notna().sum()}")
        print(f"   - With Introduction Date: {df_bills['introduction_date'].notna().sum()}")
        
        print(f"\n🏛️ Top 10 Ministries:")
        ministry_counts = df_bills['ministry'].value_counts().head(10)
        for ministry, count in ministry_counts.items():
            print(f"   - {ministry}: {count}")
        
        print(f"\n📊 Bill Status Distribution:")
        status_counts = df_bills['status'].value_counts()
        for status, count in status_counts.items():
            print(f"   - {status}: {count}")
        
        print(f"\n🔍 Search Analytics:")
        print(f"   - Total Searches: {len(searches)}")
        if len(searches) > 0:
            print(f"   - Unique Keywords: {df_searches['keyword'].nunique()}")
            print(f"   - Top 5 Search Terms:")
            top_keywords = df_searches['keyword'].value_counts().head(5)
            for keyword, count in top_keywords.items():
                print(f"     - '{keyword}': {count} times")
        
        print("\n✅ Data export complete!")

if __name__ == '__main__':
    # Create export directory
    os.makedirs('data_export', exist_ok=True)
    export_data()
