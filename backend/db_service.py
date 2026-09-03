"""
Database Service - On-Demand Population
Integrates PRS scraper with database
"""
import sys
import os
import re

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


_SEARCH_STOPWORDS = frozenset({
    "what", "which", "who", "whom", "when", "where", "why", "how",
    "is", "are", "was", "were", "be", "been", "being", "do", "does", "did",
    "has", "have", "had", "the", "a", "an", "of", "to", "for", "and", "or",
    "in", "on", "at", "by", "with", "without", "from", "than", "that", "this",
    "these", "those", "it", "its", "me", "my", "mine", "i", "you", "your",
    "about", "please", "tell", "explain", "summarize", "describe", "give",
    "know", "want", "need", "can", "could", "would", "should", "may", "might",
    "regarding", "main", "key", "provisions", "features", "purpose", "status",
    "current", "latest", "overview", "summary", "act", "passed", "draft",
})


def _extract_search_terms(keyword: str) -> list[str]:
    """Break a search query into meaningful, matchable terms.

    A natural-language question ("What is the Digital Personal Data Protection
    Bill 2023 about?") must not be passed whole to an ILIKE '%...%' filter --
    the full sentence matches zero titles.  Strip function words and split so
    the DB search can OR across ['digital', 'personal', 'data', 'protection',
    'bill', '2023'].  Falls back to the trimmed query when nothing meaningful
    remains.
    """
    words = re.findall(r"\w+", keyword.lower())
    terms = [w for w in words if w not in _SEARCH_STOPWORDS and len(w) > 1]
    # Dedupe (keeps order) so repeated words don't skew ranking.
    return list(dict.fromkeys(terms)) or [keyword.strip().lower()]


def search_bills(keyword, app, user_id=None):
    """Search bills - check the DB first, scrape PRS to backfill if needed.

    Keyword may be a short tag ('telecom') or a full natural-language
    question; either way it is tokenized into terms so matching is done on
    meaningful words instead of one long phrase.

    Workflow:
      1. OR-match the extracted terms against bill title / ministry / status,
         then the raw keyword against bill full-text (content).
      2. If very few results (< 3), scrape ALL bills from PRS, persist any
         that match, and re-run the DB search once.
      3. Rank by relevance, log a SearchHistory row, return bill dicts.
    """
    with app.app_context():
        keyword_norm = keyword.strip().lower()
        terms = _extract_search_terms(keyword)

        def _query_db():
            """OR-match terms across title/metadata; raw keyword over content."""
            # Priority 1: any search term present in the title
            title_rows = Bill.query.filter(
                or_(*[Bill.title.ilike(f"%{t}%") for t in terms])
            ).all()

            # Priority 2: any search term in ministry or status
            meta_rows = Bill.query.filter(
                or_(
                    or_(*[Bill.ministry.ilike(f"%{t}%") for t in terms]),
                    or_(*[Bill.status.ilike(f"%{t}%") for t in terms]),
                )
            ).all()

            # Priority 3: raw keyword in bill content (single-tag queries;
            # a full sentence contributes nothing here, as before)
            content_rows = (
                Bill.query.join(
                    BillContent, Bill.id == BillContent.bill_id, isouter=True
                )
                .filter(
                    or_(
                        BillContent.full_text.ilike(f"%{keyword_norm}%"),
                        BillContent.sections.cast(db.String).ilike(f"%{keyword_norm}%"),
                        BillContent.paragraphs.cast(db.String).ilike(f"%{keyword_norm}%"),
                    )
                )
                .all()
            )

            # Combine with priority: title > metadata > content (dedup by id)
            seen_ids = set()
            combined = []
            for bill in title_rows + meta_rows + content_rows:
                if bill.id not in seen_ids:
                    seen_ids.add(bill.id)
                    combined.append(bill)
            return combined

        db_results = _query_db()
        print(
            f"Found {len(db_results)} bills in database (terms={terms}) "
            f"for '{keyword}'"
        )

        # 2. If few results, scrape ALL bills from PRS to backfill the DB
        if len(db_results) < 3:
            print(f"Scraping ALL bills from PRS for '{keyword}'...")
            scraper = PRSBillTrackScraper()
            prs_bills = scraper.fetch_bill_list(max_items=None)

            new_bills = []
            for bill_data in prs_bills:
                haystack = " ".join(
                    str(bill_data.get(k, "")).lower()
                    for k in ("title", "ministry", "status")
                )
                # Any term present in title/ministry/status counts as a match
                if not any(t in haystack for t in terms):
                    continue

                url = bill_data.get("url", "")
                bill_id = (
                    url.rstrip("/").split("/")[-1]
                    if url
                    else bill_data.get("title", "")[:50]
                )
                if Bill.query.filter_by(bill_id=bill_id).first():
                    continue

                new_bill = Bill(
                    bill_id=bill_id,
                    title=bill_data["title"],
                    ministry=bill_data.get("ministry"),
                    status=bill_data.get("status"),
                    url=bill_data["url"],
                )
                db.session.add(new_bill)
                new_bills.append(new_bill)

            if new_bills:
                db.session.commit()
                print(f"Added {len(new_bills)} new bills to database")

            db_results = _query_db()

        # 3. Rank by relevance: phrase + word overlap + year + status
        term_str = " ".join(terms)
        query_words = set(re.findall(r"\w+", term_str))
        year_match = re.search(r"\b(20\d{2})\b", term_str)

        def relevance_score(bill):
            score = 0
            title = (bill.title or "").lower()
            bill_id = (bill.bill_id or "").lower()
            status = (bill.status or "").lower()

            # Phrase bonus: query terms appear in order in the title
            title_words = re.findall(r"\w+", title)
            q_idx = 0
            for tw in title_words:
                if q_idx < len(terms):
                    qw = terms[q_idx]
                    if qw == tw or (qw.endswith("s") and qw[:-1] == tw) or (tw.endswith("s") and tw[:-1] == qw):
                        q_idx += 1
            if q_idx == len(terms):
                score += 200

            # Word-level overlap in title
            title_set = set(title_words)
            score += len(query_words & title_set) * 15

            # Fuzzy plural/stem matches (telecommunication vs telecommunications)
            for qw in query_words:
                for tw in title_set:
                    if qw != tw and (qw.startswith(tw) or tw.startswith(qw)) and len(qw) > 4 and len(tw) > 4:
                        score += 8

            # Year match in title/bill_id
            if year_match and year_match.group(1) in (title, bill_id):
                score += 100

            # Status preference: Passed > Lapsed > In Committee > Draft > Rules > Withdrawn
            status_rank = {
                "passed": 50,
                "lapsed": 30,
                "in committee": 20,
                "draft": 10,
                "rules": 5,
                "withdrawn": 1,
            }
            score += status_rank.get(status, 0)

            # Boost canonical "The ... Bill, YYYY" titles over amendments
            if re.match(r"^the\s+\w+.*bill.*\d{4}$", title):
                score += 15

            return score

        db_results.sort(key=relevance_score, reverse=True)

        # 4. Log search (with user tracking for Big Data analytics)
        search_log = SearchHistory(
            keyword=keyword,
            results_count=len(db_results),
            user_id=user_id,
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

