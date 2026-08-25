"""
AI Summary Generator (On-Demand)
=================================
Generates AI summaries for bills ONLY when user searches for them.
This keeps the system fast and generates summaries only for relevant bills.

This module provides:
1. On-demand summary generation when user clicks/views a bill
2. Background summary generation for popular/recently searched bills
3. Caching to avoid regenerating summaries
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Bill, BillSummary, SearchHistory
from ai_service import generate_bill_summary

def generate_summary_for_bill(bill_id, force_regenerate=False):
    """
    Generate AI summary for a specific bill.
    
    Args:
        bill_id: ID of the bill
        force_regenerate: If True, regenerate even if summary exists
    
    Returns:
        BillSummary object or None
    """
    app = create_app()
    
    with app.app_context():
        bill = Bill.query.get(bill_id)
        if not bill:
            print(f"❌ Bill {bill_id} not found")
            return None
        
        # Check if summary already exists
        existing_summary = BillSummary.query.filter_by(bill_id=bill_id).first()
        if existing_summary and not force_regenerate:
            print(f"✅ Summary already exists for bill {bill_id}")
            return existing_summary
        
        # Check if bill has content
        if not bill.content:
            print(f"⚠️  Bill {bill_id} has no content - cannot generate summary")
            return None
        
        print(f"🤖 Generating AI summary for: {bill.title[:60]}...")
        
        try:
            # Generate summary using the AI service.
            # generate_bill_summary(bill_data, content_data) expects dicts and
            # returns a dict (summary, summary_type, confidence, ...). This
            # mirrors db_service.get_or_generate_bill_summary().
            bill_data = bill.to_dict()
            content_data = {
                'full_text': bill.content.full_text,
                'sections': bill.content.sections,
                'paragraphs': bill.content.paragraphs,
            }
            summary_result = generate_bill_summary(bill_data, content_data)
            summary_text = summary_result['summary']

            if existing_summary:
                # Update existing
                existing_summary.summary = summary_text
                existing_summary.summary_type = summary_result.get('summary_type')
                existing_summary.confidence = summary_result.get('confidence', 0.5)
                existing_summary.generated_at = datetime.utcnow()
                summary_obj = existing_summary
                print(f"   ✅ Summary updated")
            else:
                # Create new
                summary_obj = BillSummary(
                    bill_id=bill_id,
                    summary=summary_text,
                    summary_type=summary_result.get('summary_type'),
                    confidence=summary_result.get('confidence', 0.5),
                    generated_at=datetime.utcnow()
                )
                db.session.add(summary_obj)
                print(f"   ✅ Summary created")
            
            db.session.commit()
            return summary_obj
            
        except Exception as e:
            print(f"   ❌ Error generating summary: {str(e)}")
            db.session.rollback()
            return None

def generate_summaries_for_popular_bills(days=7, top_n=50):
    """
    Generate summaries for most frequently searched bills.
    
    Args:
        days: Look at search history from last N days
        top_n: Generate summaries for top N most searched bills
    """
    app = create_app()
    
    with app.app_context():
        # Get most searched bills
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        popular_searches = db.session.query(
            SearchHistory.keyword,
            db.func.count(SearchHistory.id).label('search_count')
        ).filter(
            SearchHistory.timestamp >= cutoff_date
        ).group_by(
            SearchHistory.keyword
        ).order_by(
            db.desc('search_count')
        ).limit(top_n).all()
        
        print(f"🔥 Found {len(popular_searches)} popular search terms from last {days} days")
        print("="*70)
        
        generated_count = 0
        skipped_count = 0
        
        for keyword, count in popular_searches:
            print(f"\n🔍 Keyword: '{keyword}' (searched {count} times)")
            
            # Find bills matching this keyword
            bills = Bill.query.filter(
                Bill.title.ilike(f'%{keyword}%')
            ).filter(
                Bill.content != None,
                Bill.content != ''
            ).all()
            
            print(f"   Found {len(bills)} bills with content")
            
            for bill in bills:
                # Check if summary exists
                has_summary = BillSummary.query.filter_by(bill_id=bill.id).first()
                
                if has_summary:
                    print(f"   ⏭️  Skipped: {bill.title[:50]}... (already has summary)")
                    skipped_count += 1
                else:
                    result = generate_summary_for_bill(bill.id)
                    if result:
                        generated_count += 1
        
        print("\n" + "="*70)
        print(f"✅ Summary generation complete!")
        print(f"   • Generated: {generated_count}")
        print(f"   • Skipped (already exists): {skipped_count}")
        print("="*70)

def generate_summaries_for_all_bills_with_content():
    """Generate summaries for ALL bills that have content but no summary."""
    app = create_app()
    
    with app.app_context():
        # Get bills with content but no summary
        bills_needing_summary = Bill.query.filter(
            Bill.content != None,
            Bill.content != ''
        ).filter(
            ~Bill.id.in_(
                db.session.query(BillSummary.bill_id)
            )
        ).all()
        
        print(f"📝 Found {len(bills_needing_summary)} bills with content but no summary")
        print("="*70)
        
        if not bills_needing_summary:
            print("✅ All bills with content already have summaries!")
            return
        
        generated = 0
        failed = 0
        
        for i, bill in enumerate(bills_needing_summary, 1):
            print(f"\n[{i}/{len(bills_needing_summary)}]")
            result = generate_summary_for_bill(bill.id)
            if result:
                generated += 1
            else:
                failed += 1
        
        print("\n" + "="*70)
        print(f"✅ Batch summary generation complete!")
        print(f"   • Successfully generated: {generated}")
        print(f"   • Failed: {failed}")
        print("="*70)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate AI summaries for bills')
    parser.add_argument('--bill-id', type=int, help='Generate summary for specific bill ID')
    parser.add_argument('--popular', action='store_true', help='Generate for popular searched bills')
    parser.add_argument('--all', action='store_true', help='Generate for all bills with content')
    parser.add_argument('--days', type=int, default=7, help='Days to look back for popular (default: 7)')
    parser.add_argument('--top-n', type=int, default=50, help='Top N popular keywords (default: 50)')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🤖 AI SUMMARY GENERATOR")
    print("="*70)
    
    if args.bill_id:
        generate_summary_for_bill(args.bill_id, force_regenerate=True)
    elif args.popular:
        generate_summaries_for_popular_bills(days=args.days, top_n=args.top_n)
    elif args.all:
        generate_summaries_for_all_bills_with_content()
    else:
        print("❌ Please specify --bill-id, --popular, or --all")
        parser.print_help()
