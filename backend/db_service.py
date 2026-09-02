"""
Database Service - On-Demand Population
Integrates PRS scraper with database
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from models import db, Bill, BillContent, SearchHistory, User, UserFavorite, UserReadingHistory, BillVersion, BillSummary
from datetime import datetime
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
# Import API-based AI service (Groq with custom prompt)
from ai_service import generate_bill_summary, generate_quick_summary
# Import the original working scraper
from src.scraping.prs_billtrack_scraper import PRSBillTrackScraper


def search_bills(keyword, app, user_id=None):
    """
    Search bills - check DB first, scrape if not found
    Enhanced with full-text content search and better relevance
    
    Workflow:
    1. Search in database (title, ministry, status, AND content) with word boundaries
    2. If few results (< 3), scrape ALL bills from PRS (200 bills)
    3. Save new bills to DB
    4. Return combined results sorted by relevance
    
    Args:
        keyword: Search keyword
        app: Flask app context
        user_id: User ID for tracking (optional, for analytics)
    """
    with app.app_context():
        # Normalize keyword for better matching
        keyword_normalized = keyword.strip().lower()
        
        # 1. Search in database with improved relevance
        # Priority 1: Exact word match in title (highest relevance)
        exact_title_results = Bill.query.filter(
            or_(
                Bill.title.ilike(f'%{keyword}%'),  # Contains keyword
                Bill.title.ilike(f'{keyword}%'),   # Starts with keyword
                Bill.title.ilike(f'% {keyword} %') # Word boundary match
            )
        ).all()
        
        # Priority 2: Keyword in ministry or status
        metadata_results = Bill.query.filter(
            or_(
                Bill.ministry.ilike(f'%{keyword}%'),
                Bill.status.ilike(f'%{keyword}%')
            )
        ).all()
        
        # Priority 3: Search content (full-text search in bill content)
        content_results = Bill.query.join(BillContent, Bill.id == BillContent.bill_id, isouter=True).filter(
            or_(
                BillContent.full_text.ilike(f'%{keyword}%'),
                BillContent.sections.cast(db.String).ilike(f'%{keyword}%'),
                BillContent.paragraphs.cast(db.String).ilike(f'%{keyword}%')
            )
        ).all()
        
        # Combine with priority: exact title > metadata > content
        seen_ids = set()
        db_results = []
        
        # Add exact title matches first
        for bill in exact_title_results:
            if bill.id not in seen_ids:
                db_results.append(bill)
                seen_ids.add(bill.id)
        
        # Add metadata matches
        for bill in metadata_results:
            if bill.id not in seen_ids:
                db_results.append(bill)
                seen_ids.add(bill.id)
        
        # Add content matches
        for bill in content_results:
            if bill.id not in seen_ids:
                db_results.append(bill)
                seen_ids.add(bill.id)
        
        print(f"Found {len(db_results)} bills in database ({len(exact_title_results)} by title, {len(metadata_results)} by metadata, {len(content_results)} by content)")
        
        # 2. If few results, scrape ALL bills from PRS
        if len(db_results) < 3:
            print(f"Scraping ALL bills from PRS for '{keyword}'...")
            
            # Fetch ALL bills from PRS (938+ bills)
            scraper = PRSBillTrackScraper()
            prs_bills = scraper.fetch_bill_list(max_items=None)  # Fetch all bills
            
            # Filter by keyword with better matching
            new_bills = []
            for bill_data in prs_bills:
                title = bill_data.get('title', '').lower()
                ministry = bill_data.get('ministry', '').lower()
                status = bill_data.get('status', '').lower()
                
                # Check if matches keyword (word-level or substring)
                matches = (
                    keyword_normalized in title or
                    keyword_normalized in ministry or
                    keyword_normalized in status or
                    # Check for word boundaries
                    f' {keyword_normalized} ' in f' {title} ' or
                    f' {keyword_normalized} ' in f' {ministry} ' or
                    f' {keyword_normalized} ' in f' {status} '
                )
                
                if matches:
                    # Generate bill_id from URL (last part of path)
                    url = bill_data.get('url', '')
                    bill_id = url.rstrip('/').split('/')[-1] if url else bill_data.get('title', '')[:50]
                    
                    # Check if already in DB
                    exists = Bill.query.filter_by(bill_id=bill_id).first()
                    if not exists:
                        # Add to database
                        new_bill = Bill(
                            bill_id=bill_id,
                            title=bill_data['title'],
                            ministry=bill_data.get('ministry'),
                            status=bill_data.get('status'),
                            url=bill_data['url']
                        )
                        db.session.add(new_bill)
                        new_bills.append(new_bill)
            
            if new_bills:
                db.session.commit()
                print(f"Added {len(new_bills)} new bills to database")
            
            # Re-query with full-text search, preserving priority order
            exact_title_results = Bill.query.filter(
                or_(
                    Bill.title.ilike(f'{keyword}%'),   # Starts with keyword
                    Bill.title.ilike(f'% {keyword} %'), # Word boundary match
                    Bill.title.ilike(f'%{keyword}%')    # Contains keyword
                )
            ).all()

            metadata_results = Bill.query.filter(
                or_(
                    Bill.ministry.ilike(f'%{keyword}%'),
                    Bill.status.ilike(f'%{keyword}%')
                )
            ).all()

            content_results = Bill.query.join(BillContent).filter(
                or_(
                    BillContent.full_text.ilike(f'%{keyword}%'),
                    BillContent.sections.cast(db.String).ilike(f'%{keyword}%'),
                    BillContent.paragraphs.cast(db.String).ilike(f'%{keyword}%')
                )
            ).all()

            # Combine with priority: exact title > metadata > content
            seen_ids = set()
            db_results = []

            for bill in exact_title_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in metadata_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in content_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)
            # Re-query with full-text search, preserving priority order
            exact_title_results = Bill.query.filter(
                or_(
                    Bill.title.ilike(f'{keyword}%'),   # Starts with keyword
                    Bill.title.ilike(f'% {keyword} %'), # Word boundary match
                    Bill.title.ilike(f'%{keyword}%')    # Contains keyword
                )
            ).all()

            metadata_results = Bill.query.filter(
                or_(
                    Bill.ministry.ilike(f'%{keyword}%'),
                    Bill.status.ilike(f'%{keyword}%')
                )
            ).all()

            content_results = Bill.query.join(BillContent).filter(
                or_(
                    BillContent.full_text.ilike(f'%{keyword}%'),
                    BillContent.sections.cast(db.String).ilike(f'%{keyword}%'),
                    BillContent.paragraphs.cast(db.String).ilike(f'%{keyword}%')
                )
            ).all()

            # Combine with priority: exact title > metadata > content
            seen_ids = set()
            db_results = []

            for bill in exact_title_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in metadata_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in content_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)
            # Re-query with full-text search, preserving priority order
            exact_title_results = Bill.query.filter(
                or_(
                    Bill.title.ilike(f'{keyword}%'),   # Starts with keyword
                    Bill.title.ilike(f'% {keyword} %'), # Word boundary match
                    Bill.title.ilike(f'%{keyword}%')    # Contains keyword
                )
            ).all()

            metadata_results = Bill.query.filter(
                or_(
                    Bill.ministry.ilike(f'%{keyword}%'),
                    Bill.status.ilike(f'%{keyword}%')
                )
            ).all()

            content_results = Bill.query.join(BillContent).filter(
                or_(
                    BillContent.full_text.ilike(f'%{keyword}%'),
                    BillContent.sections.cast(db.String).ilike(f'%{keyword}%'),
                    BillContent.paragraphs.cast(db.String).ilike(f'%{keyword}%')
                )
            ).all()

            # Combine with priority: exact title > metadata > content
            seen_ids = set()
            db_results = []

            for bill in exact_title_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in metadata_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in content_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)
            # Re-query with full-text search, preserving priority order
            exact_title_results = Bill.query.filter(
                or_(
                    Bill.title.ilike(f'{keyword}%'),   # Starts with keyword
                    Bill.title.ilike(f'% {keyword} %'), # Word boundary match
                    Bill.title.ilike(f'%{keyword}%')    # Contains keyword
                )
            ).all()

            metadata_results = Bill.query.filter(
                or_(
                    Bill.ministry.ilike(f'%{keyword}%'),
                    Bill.status.ilike(f'%{keyword}%')
                )
            ).all()

            content_results = Bill.query.join(BillContent).filter(
                or_(
                    BillContent.full_text.ilike(f'%{keyword}%'),
                    BillContent.sections.cast(db.String).ilike(f'%{keyword}%'),
                    BillContent.paragraphs.cast(db.String).ilike(f'%{keyword}%')
                )
            ).all()

            # Combine with priority: exact title > metadata > content
            seen_ids = set()
            db_results = []

            for bill in exact_title_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in metadata_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in content_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)
            # Re-query with full-text search, preserving priority order
            exact_title_results = Bill.query.filter(
                or_(
                    Bill.title.ilike(f'{keyword}%'),   # Starts with keyword
                    Bill.title.ilike(f'% {keyword} %'), # Word boundary match
                    Bill.title.ilike(f'%{keyword}%')    # Contains keyword
                )
            ).all()

            metadata_results = Bill.query.filter(
                or_(
                    Bill.ministry.ilike(f'%{keyword}%'),
                    Bill.status.ilike(f'%{keyword}%')
                )
            ).all()

            content_results = Bill.query.join(BillContent).filter(
                or_(
                    BillContent.full_text.ilike(f'%{keyword}%'),
                    BillContent.sections.cast(db.String).ilike(f'%{keyword}%'),
                    BillContent.paragraphs.cast(db.String).ilike(f'%{keyword}%')
                )
            ).all()

            # Combine with priority: exact title > metadata > content
            seen_ids = set()
            db_results = []

            for bill in exact_title_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in metadata_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in content_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)
            # Re-query with full-text search, preserving priority order
            exact_title_results = Bill.query.filter(
                or_(
                    Bill.title.ilike(f'{keyword}%'),   # Starts with keyword
                    Bill.title.ilike(f'% {keyword} %'), # Word boundary match
                    Bill.title.ilike(f'%{keyword}%')    # Contains keyword
                )
            ).all()

            metadata_results = Bill.query.filter(
                or_(
                    Bill.ministry.ilike(f'%{keyword}%'),
                    Bill.status.ilike(f'%{keyword}%')
                )
            ).all()

            content_results = Bill.query.join(BillContent).filter(
                or_(
                    BillContent.full_text.ilike(f'%{keyword}%'),
                    BillContent.sections.cast(db.String).ilike(f'%{keyword}%'),
                    BillContent.paragraphs.cast(db.String).ilike(f'%{keyword}%')
                )
            ).all()

            # Combine with priority: exact title > metadata > content
            seen_ids = set()
            db_results = []

            for bill in exact_title_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in metadata_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in content_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)
            # Re-query with full-text search, preserving priority order
            exact_title_results = Bill.query.filter(
                or_(
                    Bill.title.ilike(f'{keyword}%'),   # Starts with keyword
                    Bill.title.ilike(f'% {keyword} %'), # Word boundary match
                    Bill.title.ilike(f'%{keyword}%')    # Contains keyword
                )
            ).all()

            metadata_results = Bill.query.filter(
                or_(
                    Bill.ministry.ilike(f'%{keyword}%'),
                    Bill.status.ilike(f'%{keyword}%')
                )
            ).all()

            content_results = Bill.query.join(BillContent).filter(
                or_(
                    BillContent.full_text.ilike(f'%{keyword}%'),
                    BillContent.sections.cast(db.String).ilike(f'%{keyword}%'),
                    BillContent.paragraphs.cast(db.String).ilike(f'%{keyword}%')
                )
            ).all()

            # Combine with priority: exact title > metadata > content
            seen_ids = set()
            db_results = []

            for bill in exact_title_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in metadata_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in content_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)
            # Re-query with full-text search, preserving priority order
            exact_title_results = Bill.query.filter(
                or_(
                    Bill.title.ilike(f'{keyword}%'),   # Starts with keyword
                    Bill.title.ilike(f'% {keyword} %'), # Word boundary match
                    Bill.title.ilike(f'%{keyword}%')    # Contains keyword
                )
            ).all()

            metadata_results = Bill.query.filter(
                or_(
                    Bill.ministry.ilike(f'%{keyword}%'),
                    Bill.status.ilike(f'%{keyword}%')
                )
            ).all()

            content_results = Bill.query.join(BillContent).filter(
                or_(
                    BillContent.full_text.ilike(f'%{keyword}%'),
                    BillContent.sections.cast(db.String).ilike(f'%{keyword}%'),
                    BillContent.paragraphs.cast(db.String).ilike(f'%{keyword}%')
                )
            ).all()

            # Combine with priority: exact title > metadata > content
            seen_ids = set()
            db_results = []

            for bill in exact_title_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in metadata_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in content_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)
            # Re-query with full-text search, preserving priority order
            exact_title_results = Bill.query.filter(
                or_(
                    Bill.title.ilike(f'{keyword}%'),   # Starts with keyword
                    Bill.title.ilike(f'% {keyword} %'), # Word boundary match
                    Bill.title.ilike(f'%{keyword}%')    # Contains keyword
                )
            ).all()

            metadata_results = Bill.query.filter(
                or_(
                    Bill.ministry.ilike(f'%{keyword}%'),
                    Bill.status.ilike(f'%{keyword}%')
                )
            ).all()

            content_results = Bill.query.join(BillContent).filter(
                or_(
                    BillContent.full_text.ilike(f'%{keyword}%'),
                    BillContent.sections.cast(db.String).ilike(f'%{keyword}%'),
                    BillContent.paragraphs.cast(db.String).ilike(f'%{keyword}%')
                )
            ).all()

            # Combine with priority: exact title > metadata > content
            seen_ids = set()
            db_results = []

            for bill in exact_title_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in metadata_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in content_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)
            # Re-query with full-text search, preserving priority order
            exact_title_results = Bill.query.filter(
                or_(
                    Bill.title.ilike(f'{keyword}%'),   # Starts with keyword
                    Bill.title.ilike(f'% {keyword} %'), # Word boundary match
                    Bill.title.ilike(f'%{keyword}%')    # Contains keyword
                )
            ).all()

            metadata_results = Bill.query.filter(
                or_(
                    Bill.ministry.ilike(f'%{keyword}%'),
                    Bill.status.ilike(f'%{keyword}%')
                )
            ).all()

            content_results = Bill.query.join(BillContent).filter(
                or_(
                    BillContent.full_text.ilike(f'%{keyword}%'),
                    BillContent.sections.cast(db.String).ilike(f'%{keyword}%'),
                    BillContent.paragraphs.cast(db.String).ilike(f'%{keyword}%')
                )
            ).all()

            # Combine with priority: exact title > metadata > content
            seen_ids = set()
            db_results = []

            for bill in exact_title_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in metadata_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in content_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)
            # Re-query with full-text search, preserving priority order
            exact_title_results = Bill.query.filter(
                or_(
                    Bill.title.ilike(f'{keyword}%'),   # Starts with keyword
                    Bill.title.ilike(f'% {keyword} %'), # Word boundary match
                    Bill.title.ilike(f'%{keyword}%')    # Contains keyword
                )
            ).all()

            metadata_results = Bill.query.filter(
                or_(
                    Bill.ministry.ilike(f'%{keyword}%'),
                    Bill.status.ilike(f'%{keyword}%')
                )
            ).all()

            content_results = Bill.query.join(BillContent).filter(
                or_(
                    BillContent.full_text.ilike(f'%{keyword}%'),
                    BillContent.sections.cast(db.String).ilike(f'%{keyword}%'),
                    BillContent.paragraphs.cast(db.String).ilike(f'%{keyword}%')
                )
            ).all()

            # Combine with priority: exact title > metadata > content
            seen_ids = set()
            db_results = []

            for bill in exact_title_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in metadata_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in content_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)
            # Re-query with full-text search, preserving priority order
            exact_title_results = Bill.query.filter(
                or_(
                    Bill.title.ilike(f'{keyword}%'),   # Starts with keyword
                    Bill.title.ilike(f'% {keyword} %'), # Word boundary match
                    Bill.title.ilike(f'%{keyword}%')    # Contains keyword
                )
            ).all()

            metadata_results = Bill.query.filter(
                or_(
                    Bill.ministry.ilike(f'%{keyword}%'),
                    Bill.status.ilike(f'%{keyword}%')
                )
            ).all()

            content_results = Bill.query.join(BillContent).filter(
                or_(
                    BillContent.full_text.ilike(f'%{keyword}%'),
                    BillContent.sections.cast(db.String).ilike(f'%{keyword}%'),
                    BillContent.paragraphs.cast(db.String).ilike(f'%{keyword}%')
                )
            ).all()

            # Combine with priority: exact title > metadata > content
            seen_ids = set()
            db_results = []

            for bill in exact_title_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in metadata_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in content_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)
            # Re-query with full-text search, preserving priority order
            exact_title_results = Bill.query.filter(
                or_(
                    Bill.title.ilike(f'{keyword}%'),   # Starts with keyword
                    Bill.title.ilike(f'% {keyword} %'), # Word boundary match
                    Bill.title.ilike(f'%{keyword}%')    # Contains keyword
                )
            ).all()

            metadata_results = Bill.query.filter(
                or_(
                    Bill.ministry.ilike(f'%{keyword}%'),
                    Bill.status.ilike(f'%{keyword}%')
                )
            ).all()

            content_results = Bill.query.join(BillContent).filter(
                or_(
                    BillContent.full_text.ilike(f'%{keyword}%'),
                    BillContent.sections.cast(db.String).ilike(f'%{keyword}%'),
                    BillContent.paragraphs.cast(db.String).ilike(f'%{keyword}%')
                )
            ).all()

            # Combine with priority: exact title > metadata > content
            seen_ids = set()
            db_results = []

            for bill in exact_title_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in metadata_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in content_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)
            # Re-query with full-text search, preserving priority order
            exact_title_results = Bill.query.filter(
                or_(
                    Bill.title.ilike(f'{keyword}%'),   # Starts with keyword
                    Bill.title.ilike(f'% {keyword} %'), # Word boundary match
                    Bill.title.ilike(f'%{keyword}%')    # Contains keyword
                )
            ).all()

            metadata_results = Bill.query.filter(
                or_(
                    Bill.ministry.ilike(f'%{keyword}%'),
                    Bill.status.ilike(f'%{keyword}%')
                )
            ).all()

            content_results = Bill.query.join(BillContent).filter(
                or_(
                    BillContent.full_text.ilike(f'%{keyword}%'),
                    BillContent.sections.cast(db.String).ilike(f'%{keyword}%'),
                    BillContent.paragraphs.cast(db.String).ilike(f'%{keyword}%')
                )
            ).all()

            # Combine with priority: exact title > metadata > content
            seen_ids = set()
            db_results = []

            for bill in exact_title_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in metadata_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in content_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)
            # Re-query with full-text search, preserving priority order
            exact_title_results = Bill.query.filter(
                or_(
                    Bill.title.ilike(f'{keyword}%'),   # Starts with keyword
                    Bill.title.ilike(f'% {keyword} %'), # Word boundary match
                    Bill.title.ilike(f'%{keyword}%')    # Contains keyword
                )
            ).all()

            metadata_results = Bill.query.filter(
                or_(
                    Bill.ministry.ilike(f'%{keyword}%'),
                    Bill.status.ilike(f'%{keyword}%')
                )
            ).all()

            content_results = Bill.query.join(BillContent).filter(
                or_(
                    BillContent.full_text.ilike(f'%{keyword}%'),
                    BillContent.sections.cast(db.String).ilike(f'%{keyword}%'),
                    BillContent.paragraphs.cast(db.String).ilike(f'%{keyword}%')
                )
            ).all()

            # Combine with priority: exact title > metadata > content
            seen_ids = set()
            db_results = []

            for bill in exact_title_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in metadata_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in content_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)
            # Re-query with full-text search, preserving priority order
            exact_title_results = Bill.query.filter(
                or_(
                    Bill.title.ilike(f'{keyword}%'),   # Starts with keyword
                    Bill.title.ilike(f'% {keyword} %'), # Word boundary match
                    Bill.title.ilike(f'%{keyword}%')    # Contains keyword
                )
            ).all()

            metadata_results = Bill.query.filter(
                or_(
                    Bill.ministry.ilike(f'%{keyword}%'),
                    Bill.status.ilike(f'%{keyword}%')
                )
            ).all()

            content_results = Bill.query.join(BillContent).filter(
                or_(
                    BillContent.full_text.ilike(f'%{keyword}%'),
                    BillContent.sections.cast(db.String).ilike(f'%{keyword}%'),
                    BillContent.paragraphs.cast(db.String).ilike(f'%{keyword}%')
                )
            ).all()

            # Combine with priority: exact title > metadata > content
            seen_ids = set()
            db_results = []

            for bill in exact_title_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in metadata_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in content_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)
            # Re-query with full-text search, preserving priority order
            exact_title_results = Bill.query.filter(
                or_(
                    Bill.title.ilike(f'{keyword}%'),   # Starts with keyword
                    Bill.title.ilike(f'% {keyword} %'), # Word boundary match
                    Bill.title.ilike(f'%{keyword}%')    # Contains keyword
                )
            ).all()

            metadata_results = Bill.query.filter(
                or_(
                    Bill.ministry.ilike(f'%{keyword}%'),
                    Bill.status.ilike(f'%{keyword}%')
                )
            ).all()

            content_results = Bill.query.join(BillContent).filter(
                or_(
                    BillContent.full_text.ilike(f'%{keyword}%'),
                    BillContent.sections.cast(db.String).ilike(f'%{keyword}%'),
                    BillContent.paragraphs.cast(db.String).ilike(f'%{keyword}%')
                )
            ).all()

            # Combine with priority: exact title > metadata > content
            seen_ids = set()
            db_results = []

            for bill in exact_title_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in metadata_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in content_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)
            # Re-query with full-text search, preserving priority order
            exact_title_results = Bill.query.filter(
                or_(
                    Bill.title.ilike(f'{keyword}%'),   # Starts with keyword
                    Bill.title.ilike(f'% {keyword} %'), # Word boundary match
                    Bill.title.ilike(f'%{keyword}%')    # Contains keyword
                )
            ).all()

            metadata_results = Bill.query.filter(
                or_(
                    Bill.ministry.ilike(f'%{keyword}%'),
                    Bill.status.ilike(f'%{keyword}%')
                )
            ).all()

            content_results = Bill.query.join(BillContent).filter(
                or_(
                    BillContent.full_text.ilike(f'%{keyword}%'),
                    BillContent.sections.cast(db.String).ilike(f'%{keyword}%'),
                    BillContent.paragraphs.cast(db.String).ilike(f'%{keyword}%')
                )
            ).all()

            # Combine with priority: exact title > metadata > content
            seen_ids = set()
            db_results = []

            for bill in exact_title_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in metadata_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

            for bill in content_results:
                if bill.id not in seen_ids:
                    db_results.append(bill)
                    seen_ids.add(bill.id)

        # Apply relevance scoring to final results (initial + scraped)
        import re
        query_lower = keyword.strip().lower()
        query_words = set(re.findall(r'\w+', query_lower))

        def relevance_score(bill):
            score = 0
            title = (bill.title or '').lower()
            bill_id = (bill.bill_id or '').lower()
            status = (bill.status or '').lower()

            # Exact phrase match in title (highest) - require word boundaries, handle singular/plural
            # Check if all query words appear in order with word boundaries (allowing plural variations)
            query_words_list = re.findall(r'\w+', query_lower)
            if len(query_words_list) >= 1:
                matched_in_order = True
                title_words_list = re.findall(r'\w+', title)
                q_idx = 0
                for tw in title_words_list:
                    if q_idx < len(query_words_list):
                        qw = query_words_list[q_idx]
                        if qw == tw or (qw.endswith('s') and tw == qw[:-1]) or (tw.endswith('s') and qw == tw[:-1]):
                            q_idx += 1
                if q_idx == len(query_words_list):
                    score += 200  # Exact phrase match bonus (with word boundaries and plural handling)

            # Word-level matches in title
            title_words = set(re.findall(r'\w+', title))
            word_overlap = len(query_words & title_words)
            score += word_overlap * 15

            # Fuzzy match for plurals
            for qw in query_words:
                for tw in title_words:
                    if qw != tw and (qw.startswith(tw) or tw.startswith(qw)) and len(qw) > 4 and len(tw) > 4:
                        score += 8

            # Year match in title/bill_id
            year_match = re.search(r'\b(20\d{2})\b', query_lower)
            if year_match:
                year = year_match.group(1)
                if year in title or year in bill_id:
                    score += 100

            # Status preference: Passed > Lapsed > In Committee > Draft > Rules > Withdrawn
            status_rank = {'passed': 50, 'lapsed': 30, 'in committee': 20, 'draft': 10, 'rules': 5, 'withdrawn': 1}
            score += status_rank.get(status, 0)

            # Boost "The [Name] Bill, YYYY" format
            if re.match(r'^the\s+\w+.*bill.*\d{4}$', title):
                score += 15

            return score

        db_results.sort(key=relevance_score, reverse=True)

        # 3. Log search (with user tracking for Big Data analytics)
        search_log = SearchHistory(
            keyword=keyword,
            results_count=len(db_results),
            user_id=user_id  # Track user if logged in
        )
        db.session.add(search_log)
        db.session.commit()

        return [bill.to_dict() for bill in db_results]


def get_bill_content(bill_id, app, user_id=None, track_reading=True):
    """
    Get bill content - fetch from DB or scrape if needed
    
    Workflow:
    1. Check if content exists in DB
    2. If not, scrape from PRS
    3. Save to DB
    4. Track reading history (Big Data analytics)
    5. Return formatted content
    
    Args:
        bill_id: Bill identifier (can be numeric id or string bill_id)
        app: Flask app context
        user_id: User ID for tracking (optional)
        track_reading: Whether to track in reading history
    """
    with app.app_context():
        # 1. Find bill - try numeric ID first, then string bill_id
        bill = None
        try:
            # Try as numeric ID
            numeric_id = int(bill_id)
            bill = Bill.query.get(numeric_id)
        except (ValueError, TypeError):
            pass
        
        # If not found, try as string bill_id
        if not bill:
            bill = Bill.query.filter_by(bill_id=str(bill_id)).first()
        
        if not bill:
            return {'error': 'Bill not found in database'}
        
        # 2. Check if content exists
        if bill.content:
            print(f"Content found in database (fetched {bill.content.fetched_at})")
            content_data = {
                'bill': bill.to_dict(),
                'content': bill.content.to_dict(),
                'full_text': bill.content.full_text,
                'source': 'database'
            }
        else:
            # 3. Scrape content from PRS
            print(f"Attempting to fetch content from PRS for bill: {bill.title}")
            
            # Check if bill has a valid URL
            if not bill.url:
                print(f"Bill has no URL - cannot scrape content")
                return {
                    'error': 'Bill URL not available',
                    'bill': bill.to_dict(),
                    'content': None,
                    'source': 'unavailable'
                }
            
            # Try to scrape content
            scraper = PRSBillTrackScraper()
            print(f"Scraping from URL: {bill.url}")
            scraped_data = scraper.fetch_bill_content(bill.url)
            
            if not scraped_data or not scraped_data.get('full_text'):
                print(f"Failed to scrape content - saving placeholder to avoid infinite retries")
                scraped_data = {
                    'full_text': 'Content not available in HTML format on PRS India. Please refer to the PDF.',
                    'sections': [],
                    'paragraphs': ['Content not available in HTML format on PRS India. Please refer to the PDF.']
                }
            
            # 4. Save to database
            print(f"Saving scraped content to database...")
            bill_content = BillContent(
                bill_id=bill.id,
                full_text=scraped_data.get('full_text'),
                sections=scraped_data.get('sections', []),
                paragraphs=scraped_data.get('paragraphs', []),
                summary_link=scraped_data.get('summary_link'),
                pdf_link=scraped_data.get('pdf_link')
            )
            db.session.add(bill_content)
            
            # Update bill metadata if scraped from detail page
            if scraped_data.get('ministry') and scraped_data['ministry'] != 'Unknown':
                bill.ministry = scraped_data['ministry']
                print(f"Updated bill ministry: {bill.ministry}")
            if scraped_data.get('introduction_date'):
                bill.introduction_date = scraped_data['introduction_date']
                print(f"Updated bill introduction date: {bill.introduction_date}")
            
            db.session.commit()
            db.session.refresh(bill)  # Refresh to get the latest data
            
            print(f"Content saved to database successfully")
            
            content_data = {
                'bill': bill.to_dict(),
                'content': bill_content.to_dict(),
                'full_text': scraped_data.get('full_text'),
                'source': 'scraped'
            }
        
        # 5. Track reading history (Big Data analytics)
        if track_reading:
            reading_record = UserReadingHistory(
                user_id=user_id,  # Can be None for anonymous
                bill_id=bill.id,
                source='search'  # Can be 'search', 'favorite', 'recommendation'
            )
            db.session.add(reading_record)
            db.session.commit()
            print(f"Reading history tracked")
        
        return content_data


def get_database_stats(app):
    """Get database statistics"""
    with app.app_context():
        bills_count = Bill.query.count()
        content_count = BillContent.query.count()
        searches_count = SearchHistory.query.count()
        users_count = User.query.count()
        
        # Count unique search keywords
        unique_keywords = db.session.query(SearchHistory.keyword).distinct().count()
        
        recent_searches = SearchHistory.query.order_by(
            SearchHistory.timestamp.desc()
        ).limit(5).all()
        
        return {
            'total_bills': bills_count,
            'bills_with_content': content_count,
            'total_searches': searches_count,
            'total_users': users_count,
            'unique_keywords': unique_keywords,
            'recent_searches': [
                {
                    'keyword': s.keyword,
                    'results': s.results_count,
                    'timestamp': s.timestamp.isoformat()
                }
                for s in recent_searches
            ]
        }


# ============================================================================
# BIG DATA ANALYTICS FUNCTIONS
# ============================================================================

def create_user(email, username, password, full_name=None, app=None):
    """Create new user account"""
    with app.app_context():
        # Check if user exists
        if User.query.filter_by(email=email).first():
            return {'error': 'Email already registered'}
        if User.query.filter_by(username=username).first():
            return {'error': 'Username already taken'}
        
        user = User(
            email=email,
            username=username,
            full_name=full_name
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        return {'success': True, 'user': user.to_dict()}


def add_favorite(user_id, bill_id, notes=None, app=None):
    """Add bill to user favorites"""
    with app.app_context():
        # Check if already favorited
        existing = UserFavorite.query.filter_by(
            user_id=user_id, 
            bill_id=bill_id
        ).first()
        
        if existing:
            return {'error': 'Already in favorites'}
        
        favorite = UserFavorite(
            user_id=user_id,
            bill_id=bill_id,
            notes=notes
        )
        db.session.add(favorite)
        db.session.commit()
        
        return {'success': True, 'favorite_id': favorite.id}


def track_bill_version(bill_id, change_type, changes_summary=None, app=None):
    """Track bill version changes (for trend analysis)"""
    with app.app_context():
        bill = Bill.query.get(bill_id)
        if not bill:
            return {'error': 'Bill not found'}
        
        # Get latest version number
        latest_version = BillVersion.query.filter_by(bill_id=bill_id).order_by(
            BillVersion.version_number.desc()
        ).first()
        
        version_number = (latest_version.version_number + 1) if latest_version else 1
        
        # Create new version
        version = BillVersion(
            bill_id=bill_id,
            version_number=version_number,
            change_type=change_type,
            title=bill.title,
            status=bill.status,
            full_text=bill.content.full_text if bill.content else None,
            sections=bill.content.sections if bill.content else None,
            changes_summary=changes_summary
        )
        db.session.add(version)
        db.session.commit()
        
        return {'success': True, 'version_number': version_number}


def get_trending_searches(app, days=7, limit=10):
    """Get trending search keywords (Big Data analytics)"""
    with app.app_context():
        from datetime import timedelta
        from sqlalchemy import func
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Aggregate searches by keyword
        trending = db.session.query(
            SearchHistory.keyword,
            func.count(SearchHistory.id).label('search_count'),
            func.count(func.distinct(SearchHistory.user_id)).label('unique_users')
        ).filter(
            SearchHistory.timestamp >= cutoff_date
        ).group_by(
            SearchHistory.keyword
        ).order_by(
            func.count(SearchHistory.id).desc()
        ).limit(limit).all()
        
        return [
            {
                'keyword': row.keyword,
                'search_count': row.search_count,
                'unique_users': row.unique_users
            }
            for row in trending
        ]


def get_user_analytics(user_id, app):
    """Get user behavior analytics"""
    with app.app_context():
        user = User.query.get(user_id)
        if not user:
            return {'error': 'User not found'}
        
        # Reading statistics
        total_reads = UserReadingHistory.query.filter_by(user_id=user_id).count()
        favorites_count = UserFavorite.query.filter_by(user_id=user_id).count()
        searches_count = SearchHistory.query.filter_by(user_id=user_id).count()
        
        # Recent activity
        recent_reads = UserReadingHistory.query.filter_by(
            user_id=user_id
        ).order_by(
            UserReadingHistory.viewed_at.desc()
        ).limit(5).all()
        
        return {
            'user': user.to_dict(),
            'stats': {
                'total_reads': total_reads,
                'favorites': favorites_count,
                'searches': searches_count
            },
            'recent_activity': [
                {
                    'bill_id': r.bill_id,
                    'viewed_at': r.viewed_at.isoformat(),
                    'time_spent': r.time_spent_seconds
                }
                for r in recent_reads
            ]
        }


def get_ministry_analytics(app):
    """Get bill distribution by ministry (Big Data analytics)"""
    with app.app_context():
        from sqlalchemy import func
        
        ministry_stats = db.session.query(
            Bill.ministry,
            func.count(Bill.id).label('bill_count')
        ).filter(
            Bill.ministry.isnot(None),
            Bill.ministry != ''
        ).group_by(
            Bill.ministry
        ).order_by(
            func.count(Bill.id).desc()
        ).all()
        
        return [
            {
                'ministry': row.ministry,
                'bill_count': row.bill_count
            }
            for row in ministry_stats
        ]


def get_reading_heatmap(app, days=30):
    """Get reading activity heatmap (hour of day x day of week)"""
    with app.app_context():
        from datetime import timedelta
        from sqlalchemy import func
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        heatmap_data = db.session.query(
            func.strftime('%w', UserReadingHistory.viewed_at).label('day_of_week'),
            func.strftime('%H', UserReadingHistory.viewed_at).label('hour'),
            func.count(UserReadingHistory.id).label('views')
        ).filter(
            UserReadingHistory.viewed_at >= cutoff_date
        ).group_by(
            'day_of_week', 'hour'
        ).all()
        
        return [
            {
                'day_of_week': int(row.day_of_week),  # 0=Sunday, 6=Saturday
                'hour': int(row.hour),  # 0-23
                'views': row.views
            }
            for row in heatmap_data
        ]


def get_or_generate_bill_summary(bill_id, app):
    """
    Get AI-generated summary for a bill
    If summary exists, return it; otherwise generate and save
    
    Args:
        bill_id: Bill identifier (numeric id or string bill_id)
        app: Flask app context
    
    Returns:
        dict with summary data or error
    """
    with app.app_context():
        # 1. Find bill
        bill = None
        try:
            numeric_id = int(bill_id)
            bill = Bill.query.get(numeric_id)
        except (ValueError, TypeError):
            pass
        
        if not bill:
            bill = Bill.query.filter_by(bill_id=str(bill_id)).first()
        
        if not bill:
            return {'error': 'Bill not found'}
        
        # 2. Check if summary exists
        if bill.summary:
            print(f"[OK] Summary found in database (generated {bill.summary.generated_at}, model={bill.summary.model_version})")
            return {
                'summary': bill.summary.summary,
                'summary_type': bill.summary.summary_type,
                'model_version': bill.summary.model_version,
                'guardrail_applied': bill.summary.guardrail_applied,
                'generated_at': bill.summary.generated_at.isoformat(),
                'confidence': bill.summary.confidence,
                'source': 'database'
            }
        
        # 3. Check if content exists - DON'T generate summary without content
        if not bill.content:
            return {'error': 'Bill content not available yet. Please wait for content to be scraped.'}
        
        # 4. Generate new summary (only when content exists)
        print(f"[AI] Generating AI summary for bill...")
        
        # Full summary with content analysis using API
        bill_data = bill.to_dict()
        content_data = {
            'full_text': bill.content.full_text,
            'sections': bill.content.sections,
            'paragraphs': bill.content.paragraphs
        }
        
        summary_result = generate_bill_summary(bill_data, content_data)
        
        # 5. Save to database
        bill_summary = BillSummary(
            bill_id=bill.id,
            summary=summary_result['summary'],
            summary_type=summary_result['summary_type'],
            confidence=summary_result.get('confidence', 0.5),
            model_version=summary_result.get('model_version'),
            guardrail_applied=summary_result.get('guardrail_applied', True),
            guardrail_version='v1.0',
        )
        db.session.add(bill_summary)
        # Two requests can race to generate the same bill (e.g. the regenerate
        # script and the live server, or a double-click): both see no cached
        # row, both generate (slow on CPU), and the loser's INSERT violates the
        # UNIQUE(bill_id) constraint. On conflict, keep the winner's row.
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            existing = BillSummary.query.filter_by(bill_id=bill.id).first()
            if existing is not None:
                print("[race] another request generated this summary first; using its row "
                      f"(model_version={existing.model_version})")
                return {
                    'summary': existing.summary,
                    'summary_type': existing.summary_type,
                    'model_version': existing.model_version,
                    'guardrail_applied': existing.guardrail_applied,
                    'generated_at': existing.generated_at.isoformat() if existing.generated_at else None,
                    'confidence': existing.confidence,
                    'source': 'database',
                }
            raise  # pragma: no cover - genuine error, not a race

        print(f"Summary saved to database (model_version={bill_summary.model_version})")

        return {
            'summary': summary_result['summary'],
            'summary_type': summary_result['summary_type'],
            'model_version': summary_result.get('model_version'),
            'guardrail_applied': summary_result.get('guardrail_applied', True),
            'generated_at': bill_summary.generated_at.isoformat(),
            'confidence': summary_result.get('confidence', 0.5),
            'sentiment_score': summary_result.get('sentiment_score'),
            'source': 'generated'
        }


def index_all_prs_bills(app):
    """
    Index ALL bills from PRS into database (one-time setup)
    This populates the database with all 938+ bills from PRS
    """
    with app.app_context():
        print("[START] Starting full PRS indexing...")
        
        scraper = PRSBillTrackScraper()
        prs_bills = scraper.fetch_bill_list(max_items=None)  # Fetch all bills
        
        print(f"[INFO] Found {len(prs_bills)} bills on PRS")
        
        new_count = 0
        updated_count = 0
        
        for bill_data in prs_bills:
            # Generate bill_id from URL
            url = bill_data.get('url', '')
            bill_id = url.rstrip('/').split('/')[-1] if url else bill_data.get('title', '')[:50]
            
            # Check if already in DB
            existing_bill = Bill.query.filter_by(bill_id=bill_id).first()
            
            if existing_bill:
                # Update metadata if changed
                if existing_bill.title != bill_data['title'] or \
                   existing_bill.ministry != bill_data.get('ministry') or \
                   existing_bill.status != bill_data.get('status'):
                    existing_bill.title = bill_data['title']
                    existing_bill.ministry = bill_data.get('ministry')
                    existing_bill.status = bill_data.get('status')
                    existing_bill.last_updated = datetime.utcnow()
                    updated_count += 1
            else:
                # Add new bill
                new_bill = Bill(
                    bill_id=bill_id,
                    title=bill_data['title'],
                    ministry=bill_data.get('ministry'),
                    status=bill_data.get('status'),
                    url=bill_data['url']
                )
                db.session.add(new_bill)
                new_count += 1
        
        db.session.commit()
        
        print(f"[DONE] Indexing complete!")
        print(f"   New bills added: {new_count}")
        print(f"   Bills updated: {updated_count}")
        print(f"   Total bills in DB: {Bill.query.count()}")
        
        return {
            'success': True,
            'new_bills': new_count,
            'updated_bills': updated_count,
            'total_bills': Bill.query.count()
        }

