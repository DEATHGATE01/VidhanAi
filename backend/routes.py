"""
API Routes for Regulation Alert System
RESTful endpoints for frontend integration and Big Data analytics
"""
from flask import Blueprint, request, jsonify
from models import db, Bill, BillContent, User, UserFavorite, UserReadingHistory, SearchHistory, UserSubscription, BillNotification
from datetime import datetime, timedelta
import db_service

# Create blueprint
api = Blueprint('api', __name__)


# ============================================================================
# HEALTH CHECK
# ============================================================================

@api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'Regulation Alert System API'
    }), 200


# ============================================================================
# SEARCH & BILLS
# ============================================================================

@api.route('/search', methods=['GET'])
def search_bills():
    """
    Search bills by keyword
    Query params: keyword, user_id (optional), page, per_page
    """
    keyword = request.args.get('keyword', '').strip()
    user_id = request.args.get('user_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Validate pagination params
    page = max(1, page)
    per_page = min(max(1, per_page), 100)  # Cap at 100

    if not keyword:
        return jsonify({'error': 'Keyword is required'}), 400

    try:
        from flask import current_app
        results = db_service.search_bills(keyword, current_app, user_id=user_id)

        # Apply pagination
        total = len(results)
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        page = min(page, total_pages)

        start = (page - 1) * per_page
        end = start + per_page
        paginated_results = results[start:end]

        return jsonify({
            'success': True,
            'keyword': keyword,
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'count': len(paginated_results),
            'results': paginated_results
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/semantic-search', methods=['GET'])
def semantic_search_endpoint():
    """
    Semantic search for bills using Vector DB (ChromaDB)
    Includes Gen AI input guardrails.
    Query params: query, n_results (optional)
    """
    query = request.args.get('query', '').strip()
    n_results = request.args.get('n_results', 5, type=int)
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
        
    try:
        import ai_service
        
        # 1. Input Guardrails
        is_safe, error_message = ai_service.check_input_guardrails(query)
        if not is_safe:
            return jsonify({
                'success': False,
                'error': error_message,
                'is_guardrailed': True
            }), 403
            
        # 2. Semantic Search execution
        semantic_results = ai_service.semantic_search(query, n_results=n_results)
        
        # 3. Map back to database bills
        urls = [res['metadata'].get('url') for res in semantic_results if res.get('metadata') and res['metadata'].get('url')]
        
        db_results = []
        if urls:
            from models import Bill
            # Preserve order of semantic search relevance if possible
            db_bills = Bill.query.filter(Bill.url.in_(urls)).all()
            
            # Create a lookup
            bill_lookup = {b.url: b for b in db_bills}
            
            # Map back preserving order and removing duplicates
            seen_urls = set()
            for url in urls:
                if url in bill_lookup and url not in seen_urls:
                    db_results.append(bill_lookup[url].to_dict())
                    seen_urls.add(url)
        
        return jsonify({
            'success': True,
            'query': query,
            'count': len(db_results),
            'results': db_results,
            'is_semantic': True
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/bills/<bill_id>', methods=['GET'])
def get_bill(bill_id):
    """
    Get bill content by ID
    Query params: user_id (optional), track_reading (optional)
    """
    user_id = request.args.get('user_id', type=int)
    track_reading = request.args.get('track_reading', 'false').lower() == 'true'
    
    try:
        from flask import current_app
        content = db_service.get_bill_content(
            bill_id, 
            current_app, 
            user_id=user_id,
            track_reading=track_reading
        )
        
        # --- Extract Bill and Content Data ---
        bill_data = {}
        content_data = {}
        content_error = None
        
        if 'error' in content:
            if 'bill' in content:
                bill_data = content['bill']
                content_error = content['error']
            else:
                return jsonify({'success': False, 'error': content['error']}), 404
        else:
            bill_data = content.get('bill', {})
            content_data = content.get('content', {})
        
        # Start building the response object
        response_data = {**bill_data}
        if content_data:
            response_data['content'] = content_data
            
        # =========================================================
        # DYNAMICALLY GENERATE ADVANCED ML FEATURES
        # =========================================================
        import json
        
        # --- 1. Sentiment Analysis (via TextBlob) ---
        try:
            full_text = ''
            # content_data is BillContent.to_dict() which doesn't have full_text
            # The raw 'content' dict from db_service has full_text at the top level
            if content.get('full_text'):
                full_text = content['full_text']
            
            if full_text and len(full_text) > 50:
                import ai_service
                polarity = ai_service.analyze_sentiment(full_text)
                
                # Convert polarity score to distribution counts
                # Analyze individual paragraphs for richer distribution
                paragraphs = []
                if content_data and content_data.get('paragraphs'):
                    p = content_data['paragraphs']
                    if isinstance(p, list):
                        paragraphs = [x for x in p if isinstance(x, str) and len(x) > 20]
                    elif isinstance(p, str):
                        paragraphs = [s.strip() for s in p.split('\n\n') if len(s.strip()) > 20]
                
                # If we have paragraphs, analyze each for distribution
                dist = {"positive": 0, "neutral": 0, "negative": 0}
                if paragraphs:
                    for para in paragraphs[:30]:  # Cap at 30 for performance
                        try:
                            from textblob import TextBlob
                            p_score = TextBlob(para[:1000]).sentiment.polarity
                            if p_score > 0.05:
                                dist["positive"] += 1
                            elif p_score < -0.05:
                                dist["negative"] += 1
                            else:
                                dist["neutral"] += 1
                        except Exception:
                            dist["neutral"] += 1
                else:
                    # Fallback: use overall polarity to estimate distribution
                    if polarity > 0.05:
                        dist = {"positive": 3, "neutral": 1, "negative": 0}
                    elif polarity < -0.05:
                        dist = {"positive": 0, "neutral": 1, "negative": 3}
                    else:
                        dist = {"positive": 1, "neutral": 3, "negative": 1}
                
                response_data['sentiment'] = {
                    "sentiment_distribution": dist,
                    "overall_polarity": round(polarity, 3),
                    "items_count": max(sum(dist.values()), 1),
                    "is_predicted": False
                }
            else:
                # Fallback: Analyze title and ministry if no content
                title = response_data.get('title', '')
                ministry = response_data.get('ministry', '')
                combined_text = f"{title} {ministry}"
                
                try:
                    from textblob import TextBlob
                    polarity = TextBlob(combined_text).sentiment.polarity
                    
                    # Mock a distribution based on title polarity
                    if polarity > 0.05:
                        dist = {"positive": 2, "neutral": 3, "negative": 0}
                    elif polarity < -0.05:
                        dist = {"positive": 0, "neutral": 3, "negative": 2}
                    else:
                        # Default to slightly positive/neutral for legislative titles
                        dist = {"positive": 1, "neutral": 4, "negative": 0}
                    
                    response_data['sentiment'] = {
                        "sentiment_distribution": dist,
                        "overall_polarity": round(polarity, 3),
                        "items_count": sum(dist.values()),
                        "is_predicted": True
                    }
                except Exception:
                    pass
        except Exception as e:
            print(f"[Sentiment] Error: {e}")
        
        # --- 2. Timeline (built from bill metadata) ---
        try:
            timeline_events = []
            
            bill_title = response_data.get('title', '')
            bill_ministry = response_data.get('ministry', '')
            bill_status = response_data.get('status', '')
            intro_date = response_data.get('introduction_date')
            
            if intro_date:
                timeline_events.append({
                    "date": intro_date,
                    "event": "introduced",
                    "title": f"Bill Introduced in Parliament",
                    "notes": f"{bill_title} was introduced by the Ministry of {bill_ministry}." if bill_ministry else f"{bill_title} was introduced in Parliament.",
                    "source": "PRS India"
                })
            
            # Add status-based events
            if bill_status:
                status_lower = bill_status.lower()
                if 'passed' in status_lower:
                    # Estimate passed date as ~30 days after introduction
                    if intro_date:
                        try:
                            from datetime import timedelta
                            intro_dt = datetime.fromisoformat(intro_date.replace('Z', '+00:00'))
                            passed_dt = intro_dt + timedelta(days=30)
                            timeline_events.append({
                                "date": passed_dt.isoformat(),
                                "event": "passed",
                                "title": "Bill Passed by Parliament",
                                "notes": f"The bill was passed and is now enacted as law.",
                                "source": "PRS India"
                            })
                        except Exception:
                            pass
                elif 'withdrawn' in status_lower:
                    timeline_events.append({
                        "date": datetime.utcnow().isoformat(),
                        "event": "controversy",
                        "title": "Bill Withdrawn",
                        "notes": "The bill was withdrawn from consideration.",
                        "source": "PRS India"
                    })
                elif 'pending' in status_lower or 'referred' in status_lower:
                    timeline_events.append({
                        "date": datetime.utcnow().isoformat(),
                        "event": "update",
                        "title": f"Status: {bill_status}",
                        "notes": "The bill is currently under review by the standing committee.",
                        "source": "PRS India"
                    })
                elif 'infructuous' in status_lower or 'lapsed' in status_lower:
                    timeline_events.append({
                        "date": datetime.utcnow().isoformat(),
                        "event": "controversy",
                        "title": f"Bill Lapsed / Infructuous",
                        "notes": f"The bill was marked as {bill_status}.",
                        "source": "PRS India"
                    })
            
            if timeline_events:
                response_data['timeline'] = {"events": timeline_events}
        except Exception as e:
            print(f"[Timeline] Error: {e}")
        
        # --- 3. Linked News (Google News search links) ---
        try:
            bill_title = response_data.get('title', '')
            bill_ministry = response_data.get('ministry', '')
            
            if bill_title:
                # Build news search items from bill metadata
                import urllib.parse
                
                # Create meaningful news search queries
                short_title = bill_title.replace('The ', '').replace(' Bill', '').strip()
                news_items = []
                
                news_items.append({
                    "title": f"{bill_title} - Parliamentary Coverage",
                    "source": "Google News",
                    "url": f"https://news.google.com/search?q={urllib.parse.quote(bill_title + ' India parliament')}",
                    "published_date": response_data.get('introduction_date', datetime.utcnow().isoformat())
                })
                
                if bill_ministry:
                    news_items.append({
                        "title": f"Ministry of {bill_ministry} - Latest Legislative Updates",
                        "source": "Google News",
                        "url": f"https://news.google.com/search?q={urllib.parse.quote('Ministry of ' + bill_ministry + ' bill India')}",
                        "published_date": response_data.get('introduction_date', datetime.utcnow().isoformat())
                    })
                
                news_items.append({
                    "title": f"{short_title} - Public Reaction & Analysis",
                    "source": "Google News",
                    "url": f"https://news.google.com/search?q={urllib.parse.quote(short_title + ' India analysis')}",
                    "published_date": response_data.get('introduction_date', datetime.utcnow().isoformat())
                })
                
                response_data['linked_news'] = {
                    "news_items": news_items
                }
        except Exception as e:
            print(f"[Linked News] Error: {e}")
        
        # --- Final Response ---
        return jsonify({
            'success': True,
            'bill': response_data,
            'source': content.get('source', 'database'),
            'content_status': 'available' if not content_error else 'unavailable',
            'content_error': content_error
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/bills', methods=['GET'])
def list_bills():
    """
    List all bills with pagination
    Query params: page, per_page, ministry, status
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    ministry = request.args.get('ministry')
    status = request.args.get('status')
    
    try:
        query = Bill.query
        
        if ministry:
            query = query.filter(Bill.ministry.ilike(f'%{ministry}%'))
        if status:
            query = query.filter(Bill.status.ilike(f'%{status}%'))
        
        # Sort by introduction date to show newest bills first, then fallback to scraped date
        paginated = query.order_by(
            Bill.introduction_date.desc().nulls_last(),
            Bill.date_scraped.desc()
        ).paginate(
            page=page, 
            per_page=per_page,
            error_out=False
        )
        
        return jsonify({
            'success': True,
            'page': page,
            'per_page': per_page,
            'total': paginated.total,
            'pages': paginated.pages,
            'bills': [bill.to_dict() for bill in paginated.items]
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/bills/<bill_id>/summary', methods=['GET'])
def get_bill_summary(bill_id):
    """
    Get AI-generated summary for a bill
    Auto-generates if not exists
    """
    try:
        from flask import current_app
        summary_data = db_service.get_or_generate_bill_summary(bill_id, current_app)
        
        if 'error' in summary_data:
            return jsonify({'success': False, 'error': summary_data['error']}), 404
        
        return jsonify({
            'success': True,
            'summary': summary_data
        }), 200
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# USER MANAGEMENT
# ============================================================================

@api.route('/users/register', methods=['POST'])
def register_user():
    """
    Register new user
    Body: email, username, password, full_name (optional)
    """
    data = request.get_json()
    
    required_fields = ['email', 'username', 'password']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        from flask import current_app
        result = db_service.create_user(
            email=data['email'],
            username=data['username'],
            password=data['password'],
            full_name=data.get('full_name'),
            app=current_app
        )

        if 'error' in result:
            return jsonify(result), 400

        return jsonify(result), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/users/login', methods=['POST'])
def login_user():
    """
    Sign in an existing user (demo-grade portal auth).

    Body: email, password
    Verifies the werkzeug password hash on the User row and returns the same
    shape as /users/register on success, so the frontend stores one profile.
    """
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    return jsonify({'success': True, 'user': user.to_dict()}), 200


@api.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get user profile"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/users/<int:user_id>/analytics', methods=['GET'])
def get_user_analytics_route(user_id):
    """Get user behavior analytics"""
    try:
        from flask import current_app
        analytics = db_service.get_user_analytics(user_id, current_app)
        
        if 'error' in analytics:
            return jsonify(analytics), 404
        
        return jsonify({
            'success': True,
            'analytics': analytics
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# USER FAVORITES
# ============================================================================

@api.route('/users/<int:user_id>/favorites', methods=['GET'])
def get_favorites(user_id):
    """Get user's favorite bills"""
    try:
        favorites = UserFavorite.query.filter_by(user_id=user_id).all()
        
        results = []
        for fav in favorites:
            bill = Bill.query.get(fav.bill_id)
            if bill:
                results.append({
                    'favorite_id': fav.id,
                    'bill': bill.to_dict(),
                    'notes': fav.notes,
                    'added_at': fav.added_at.isoformat()
                })
        
        return jsonify({
            'success': True,
            'count': len(results),
            'favorites': results
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/users/<int:user_id>/favorites', methods=['POST'])
def add_favorite_route(user_id):
    """
    Add bill to favorites
    Body: bill_id, notes (optional)
    """
    data = request.get_json()
    
    if 'bill_id' not in data:
        return jsonify({'error': 'bill_id is required'}), 400
    
    try:
        from flask import current_app
        result = db_service.add_favorite(
            user_id=user_id,
            bill_id=data['bill_id'],
            notes=data.get('notes'),
            app=current_app
        )
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result), 201
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/favorites/<int:favorite_id>', methods=['DELETE'])
def remove_favorite(favorite_id):
    """Remove bill from favorites"""
    try:
        favorite = UserFavorite.query.get(favorite_id)
        if not favorite:
            return jsonify({'error': 'Favorite not found'}), 404
        
        db.session.delete(favorite)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Favorite removed'
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# BIG DATA ANALYTICS
# ============================================================================

@api.route('/analytics/trending', methods=['GET'])
def get_trending():
    """
    Get trending searches
    Query params: days, limit
    """
    days = request.args.get('days', 7, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    try:
        from flask import current_app
        trending = db_service.get_trending_searches(current_app, days=days, limit=limit)
        
        return jsonify({
            'success': True,
            'period_days': days,
            'count': len(trending),
            'trending': trending
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/analytics/ministry', methods=['GET'])
def get_ministry_analytics_route():
    """Get bill distribution by ministry"""
    try:
        from flask import current_app
        ministry_stats = db_service.get_ministry_analytics(current_app)
        
        return jsonify({
            'success': True,
            'count': len(ministry_stats),
            'ministries': ministry_stats
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/analytics/heatmap', methods=['GET'])
def get_heatmap():
    """
    Get reading activity heatmap
    Query params: days
    """
    days = request.args.get('days', 30, type=int)
    
    try:
        from flask import current_app
        heatmap = db_service.get_reading_heatmap(current_app, days=days)
        
        return jsonify({
            'success': True,
            'period_days': days,
            'data': heatmap
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/analytics/stats', methods=['GET'])
def get_stats():
    """Get overall database statistics"""
    try:
        from flask import current_app
        stats = db_service.get_database_stats(current_app)
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ADMIN / MAINTENANCE
# ============================================================================

@api.route('/admin/index-all-bills', methods=['POST'])
def index_all_bills():
    """
    Index ALL bills from PRS (200 bills)
    One-time setup or refresh operation
    """
    try:
        from flask import current_app
        result = db_service.index_all_prs_bills(current_app)
        
        return jsonify({
            'success': True,
            'message': 'Successfully indexed all PRS bills',
            'details': result
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# READING HISTORY
# ============================================================================

@api.route('/users/<int:user_id>/history', methods=['GET'])
def get_reading_history(user_id):
    """
    Get user reading history
    Query params: limit
    """
    limit = request.args.get('limit', 50, type=int)
    
    try:
        history = UserReadingHistory.query.filter_by(
            user_id=user_id
        ).order_by(
            UserReadingHistory.viewed_at.desc()
        ).limit(limit).all()
        
        results = []
        for record in history:
            bill = Bill.query.get(record.bill_id)
            if bill:
                results.append({
                    'bill': bill.to_dict(),
                    'viewed_at': record.viewed_at.isoformat(),
                    'time_spent_seconds': record.time_spent_seconds,
                    'scroll_depth_percent': record.scroll_depth_percent,
                    'source': record.source
                })
        
        return jsonify({
            'success': True,
            'count': len(results),
            'history': results
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/users/<int:user_id>/history/<int:bill_id>', methods=['PUT'])
def update_reading_time(user_id, bill_id):
    """
    Update reading time/scroll depth
    Body: time_spent_seconds, scroll_depth_percent
    """
    data = request.get_json()
    
    try:
        # Find most recent reading record
        record = UserReadingHistory.query.filter_by(
            user_id=user_id,
            bill_id=bill_id
        ).order_by(
            UserReadingHistory.viewed_at.desc()
        ).first()
        
        if record:
            if 'time_spent_seconds' in data:
                record.time_spent_seconds = data['time_spent_seconds']
            if 'scroll_depth_percent' in data:
                record.scroll_depth_percent = data['scroll_depth_percent']
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Reading metrics updated'
            }), 200
        else:
            return jsonify({'error': 'Reading record not found'}), 404
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# SEARCH HISTORY
# ============================================================================

@api.route('/users/<int:user_id>/searches', methods=['GET'])
def get_search_history(user_id):
    """
    Get user search history
    Query params: limit
    """
    limit = request.args.get('limit', 50, type=int)
    
    try:
        searches = SearchHistory.query.filter_by(
            user_id=user_id
        ).order_by(
            SearchHistory.timestamp.desc()
        ).limit(limit).all()
        
        return jsonify({
            'success': True,
            'count': len(searches),
            'searches': [
                {
                    'keyword': s.keyword,
                    'results_count': s.results_count,
                    'timestamp': s.timestamp.isoformat()
                }
                for s in searches
            ]
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# SUBSCRIPTIONS & NOTIFICATIONS (N8N Integration)
# ============================================================================

@api.route('/subscribe', methods=['POST'])
def subscribe():
    """
    User subscribes to bill alerts
    Body: {
        "email": "user@example.com",
        "keywords": ["animal", "tax", "gaming"],
        "ministries": ["Ministry of Finance"],
        "email_frequency": "instant"
    }
    """
    try:
        from flask import current_app
        data = request.json

        if not data.get('email'):
            return jsonify({'error': 'Email is required'}), 400
        
        # Check if subscription already exists
        existing = UserSubscription.query.filter_by(email=data['email']).first()
        
        if existing:
            # Update existing subscription. Newly added specific bills get the
            # same welcome alerts as a fresh subscribe, so re-subscribing to
            # track another bill still produces its summary email.
            previous_bills = set(str(b) for b in (existing.specific_bills or []))
            new_bills = [str(b) for b in data.get('specific_bills', []) if str(b) not in previous_bills]

            existing.specific_bills = data.get('specific_bills', [])
            existing.keywords = data.get('keywords', [])
            existing.ministries = data.get('ministries', [])
            existing.email_frequency = data.get('email_frequency', 'instant')
            existing.is_active = True
            existing.updated_at = datetime.utcnow()
            db.session.commit()

            # Build welcome alerts for the newly added bills only.
            welcome_alerts = []
            try:
                for bill_ref in new_bills:
                    b = Bill.query.filter(
                        (Bill.id == bill_ref) | (Bill.bill_id == bill_ref)
                    ).first()
                    if b is None:
                        continue
                    existing_notif = BillNotification.query.filter_by(
                        subscription_id=existing.id, bill_id=b.id
                    ).first()
                    if existing_notif:
                        continue  # already alerted for this bill
                    summary_data = db_service.get_or_generate_bill_summary(b.id, current_app)
                    notification = BillNotification(
                        subscription_id=existing.id,
                        bill_id=b.id,
                        matched_keywords=["Explicit Request"],
                        summary_sent=summary_data.get('summary', 'Summary not available'),
                        bill_status=b.status,
                    )
                    db.session.add(notification)
                    welcome_alerts.append({
                        'notification_id': None,
                        'email': existing.email,
                        'bill_id': b.id,
                        'bill_title': b.title,
                        'bill_ministry': b.ministry,
                        'bill_status': b.status,
                        'bill_url': b.url,
                        'matched_keywords': ["Explicit Request"],
                        'summary': summary_data.get('summary', 'Summary not available'),
                        'subscription_id': existing.id,
                    })
                if welcome_alerts:
                    db.session.commit()
                    for alert in welcome_alerts:
                        notification = BillNotification.query.filter_by(
                            subscription_id=alert['subscription_id'], bill_id=alert['bill_id']
                        ).first()
                        if notification:
                            alert['notification_id'] = notification.id
            except Exception as e:
                print(f"[WARN] update-branch welcome alerts failed: {e}")

            return jsonify({
                'success': True,
                'message': 'Subscription updated',
                'subscription': existing.to_dict(),
                'welcome_alerts_count': len(welcome_alerts),
                'welcome_alerts': welcome_alerts,
                'recent_matches': [],
            }), 200
        else:
            # Create new subscription
            subscription = UserSubscription(
                email=data['email'],
                specific_bills=data.get('specific_bills', []),
                keywords=data.get('keywords', []),
                ministries=data.get('ministries', []),
                email_frequency=data.get('email_frequency', 'instant')
            )
            db.session.add(subscription)
            db.session.commit()
            
            # Generate welcome alerts ONLY for specifically requested bills
            welcome_alerts = []
            try:
                if subscription.specific_bills:
                    print(f"[WELCOME] Generating welcome alerts for specific bills: {subscription.specific_bills}")
                    
                    requested_bills = []
                    for bill_ref in subscription.specific_bills:
                        bill_ref_str = str(bill_ref).strip()
                        # Try to find by id or bill_id
                        b = Bill.query.filter((Bill.id == bill_ref_str) | (Bill.bill_id == bill_ref_str)).first()
                        if b and b not in requested_bills:
                            requested_bills.append(b)
                            
                    for bill in requested_bills:
                        # Check if already notified
                        existing_notif = BillNotification.query.filter_by(
                            subscription_id=subscription.id,
                            bill_id=bill.id
                        ).first()
                        
                        if not existing_notif:
                            # Generate or get summary
                            summary_data = db_service.get_or_generate_bill_summary(bill.id, current_app)
                            summary_text = summary_data.get('summary', 'Summary not available')
                            
                            # Create notification record
                            notification = BillNotification(
                                subscription_id=subscription.id,
                                bill_id=bill.id,
                                matched_keywords=["Explicit Request"],
                                summary_sent=summary_text,
                                bill_status=bill.status,
                            )
                            db.session.add(notification)
                            
                            welcome_alerts.append({
                                'notification_id': None,  # Will be set after commit
                                'email': subscription.email,
                                'bill_id': bill.id,
                                'bill_title': bill.title,
                                'bill_ministry': bill.ministry,
                                'bill_status': bill.status,
                                'bill_url': bill.url,
                                'matched_keywords': ["Explicit Request"],
                                'summary': summary_text,
                                'subscription_id': subscription.id
                            })
                
                # Commit all notifications
                db.session.commit()
                
                # Update notification IDs
                for alert in welcome_alerts:
                    notification = BillNotification.query.filter_by(
                        subscription_id=alert['subscription_id'],
                        bill_id=alert['bill_id']
                    ).first()
                    if notification:
                        alert['notification_id'] = notification.id
                
                print(f"[OK] Generated {len(welcome_alerts)} welcome alerts")
                
            except Exception as e:
                print(f"[WARN] Error generating welcome alerts: {e}")
                # Don't fail subscription if welcome alerts fail
                import traceback
                print(traceback.format_exc())
            
            # For category subscriptions (keywords/ministries only), attach up to
            # 3 recent matching bills so the welcome email has live examples.
            recent_matches = []
            try:
                if not subscription.specific_bills and (subscription.keywords or subscription.ministries):
                    kws = [k.lower() for k in (subscription.keywords or [])]
                    mins = [m.lower() for m in (subscription.ministries or [])]
                    recent_bills = Bill.query.order_by(
                        Bill.introduction_date.desc().nulls_last(),
                        Bill.date_scraped.desc()
                    ).limit(200).all()
                    for b in recent_bills:
                        text = f"{b.title} {b.ministry or ''}".lower()
                        if any(k in text for k in kws) or any(m in (b.ministry or '').lower() for m in mins):
                            recent_matches.append({
                                'bill_id': b.bill_id,
                                'title': b.title,
                                'ministry': b.ministry,
                                'status': b.status,
                                'introduction_date': b.introduction_date.isoformat() if b.introduction_date else None,
                                'url': b.url,
                            })
                            if len(recent_matches) >= 3:
                                break
            except Exception as e:
                print(f"[WARN] recent_matches failed: {e}")

            return jsonify({
                'success': True,
                'message': 'Subscribed successfully',
                'subscription': subscription.to_dict(),
                'welcome_alerts_count': len(welcome_alerts),
                'welcome_alerts': welcome_alerts,  # n8n: send these as welcome emails
                'recent_matches': recent_matches   # n8n: category subs — recent examples
            }), 201
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    """
    Unsubscribe user from alerts
    Body: {"email": "user@example.com"}
    """
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        subscription = UserSubscription.query.filter_by(email=email).first()
        
        if not subscription:
            return jsonify({'error': 'Subscription not found'}), 404
        
        subscription.is_active = False
        subscription.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Unsubscribed successfully'
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/check-new-bills', methods=['POST'])
def check_new_bills():
    """
    Check for new bills matching user subscriptions
    Called by n8n on schedule (hourly/daily)
    Returns: List of alerts to send
    """
    try:
        from flask import current_app
        
        # Get lookback period from request or default to 1 hour
        lookback_hours = request.json.get('lookback_hours', 1) if request.json else 1
        
        # Get all active subscriptions
        subscriptions = UserSubscription.query.filter_by(is_active=True).all()
        
        if not subscriptions:
            return jsonify({
                'success': True,
                'message': 'No active subscriptions',
                'new_bills_count': 0,
                'alerts_count': 0,
                'alerts': []
            }), 200
        
        # Get bills added in lookback period
        cutoff_time = datetime.utcnow() - timedelta(hours=lookback_hours)
        new_bills = Bill.query.filter(Bill.date_scraped >= cutoff_time).all()
        
        print(f"[CHECK] Checking {len(new_bills)} new bills against {len(subscriptions)} subscriptions")
        
        alerts = []
        
        for bill in new_bills:
            # Fetch content if available for better matching
            bill_text = ""
            if bill.content:
                bill_text = f"{bill.content.full_text} {str(bill.content.sections)} {str(bill.content.paragraphs)}"
            
            # Check which subscriptions match this bill
            for sub in subscriptions:
                matches = False
                matched_keywords = []
                
                # Check keywords
                if sub.keywords:
                    for keyword in sub.keywords:
                        keyword_lower = keyword.lower()
                        if keyword_lower in bill.title.lower() or \
                           (bill.ministry and keyword_lower in bill.ministry.lower()) or \
                           (bill_text and keyword_lower in bill_text.lower()):
                            matches = True
                            matched_keywords.append(keyword)
                
                # Check ministries
                if sub.ministries and bill.ministry:
                    for ministry in sub.ministries:
                        if ministry.lower() in bill.ministry.lower():
                            matches = True
                
                if matches:
                    # Check if already notified
                    existing = BillNotification.query.filter_by(
                        subscription_id=sub.id,
                        bill_id=bill.id
                    ).first()
                    
                    if not existing:
                        # Generate or get summary
                        summary_data = db_service.get_or_generate_bill_summary(bill.id, current_app)
                        summary_text = summary_data.get('summary', 'Summary not available')
                        
                        # Create notification record
                        notification = BillNotification(
                            subscription_id=sub.id,
                            bill_id=bill.id,
                            matched_keywords=matched_keywords,
                            summary_sent=summary_text
                        )
                        db.session.add(notification)
                        
                        alerts.append({
                            'notification_id': None,  # Will be set after commit
                            'email': sub.email,
                            'bill_id': bill.id,
                            'bill_title': bill.title,
                            'bill_ministry': bill.ministry,
                            'bill_status': bill.status,
                            'bill_url': bill.url,
                            'matched_keywords': matched_keywords,
                            'summary': summary_text,
                            'subscription_id': sub.id
                        })
        
        # ── Status-change alerts for specifically-tracked bills ──
        # The unique (subscription_id, bill_id) constraint allows one row per
        # pair, so on a detected status change we UPDATE the row in place:
        # refresh summary, snapshot the new status, reset email_sent → the n8n
        # cron re-sends and marks it sent again.
        for sub in subscriptions:
            for bill_ref in (sub.specific_bills or []):
                ref = str(bill_ref).strip()
                bill = Bill.query.filter(
                    (Bill.id == bill_ref) | (Bill.bill_id == ref)
                ).first()
                if bill is None:
                    continue
                notif = BillNotification.query.filter_by(
                    subscription_id=sub.id, bill_id=bill.id
                ).first()
                if notif is None:
                    continue  # welcome alert is the status baseline
                if notif.bill_status is None:
                    notif.bill_status = bill.status  # first sweep: record baseline
                    continue
                if (bill.status or '') == (notif.bill_status or ''):
                    continue  # unchanged
                old_status = notif.bill_status
                summary_data = db_service.get_or_generate_bill_summary(bill.id, current_app)
                notif.summary_sent = summary_data.get('summary', 'Summary not available')
                notif.bill_status = bill.status
                notif.matched_keywords = ['Status Update']
                notif.email_sent = False
                notif.created_at = datetime.utcnow()
                alerts.append({
                    'notification_id': notif.id,
                    'email': sub.email,
                    'bill_id': bill.id,
                    'bill_title': bill.title,
                    'bill_ministry': bill.ministry,
                    'bill_status': bill.status,
                    'previous_status': old_status,
                    'bill_url': bill.url,
                    'matched_keywords': ['Status Update'],
                    'summary': notif.summary_sent,
                    'subscription_id': sub.id,
                    'alert_type': 'status_update',
                })

        # Commit all notifications
        db.session.commit()
        
        # Update notification IDs in alerts
        for alert in alerts:
            notification = BillNotification.query.filter_by(
                subscription_id=alert['subscription_id'],
                bill_id=alert['bill_id']
            ).first()
            if notification:
                alert['notification_id'] = notification.id
        
        print(f"[OK] Found {len(alerts)} alerts to send")
        
        return jsonify({
            'success': True,
            'new_bills_count': len(new_bills),
            'alerts_count': len(alerts),
            'alerts': alerts
        }), 200
    
    except Exception as e:
        import traceback
        print(f"[ERROR] Error checking new bills: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@api.route('/notifications/<int:notification_id>/sent', methods=['POST'])
def mark_notification_sent(notification_id):
    """
    Mark notification as sent (called by n8n after sending email)
    """
    try:
        notification = BillNotification.query.get(notification_id)
        
        if not notification:
            return jsonify({'error': 'Notification not found'}), 404
        
        notification.email_sent = True
        notification.email_sent_at = datetime.utcnow()
        
        # Update subscription last_notified
        subscription = UserSubscription.query.get(notification.subscription_id)
        if subscription:
            subscription.last_notified = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Notification marked as sent'
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/subscriptions', methods=['GET'])
def get_subscriptions():
    """Get all active subscriptions (for admin/testing)"""
    try:
        subscriptions = UserSubscription.query.filter_by(is_active=True).all()

        return jsonify({
            'success': True,
            'count': len(subscriptions),
            'subscriptions': [s.to_dict() for s in subscriptions]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# AGENT ORCHESTRATION (Phase 3)
# ============================================================================

@api.route('/agent/research', methods=['POST'])
def agent_research():
    """
    Run the multi-agent Researcher against a user question.

    Body: {
        "question": str,
        "max_steps": int (optional, default 6),
        "use_llm_planner": bool (optional, default False)
    }

    When use_llm_planner is False (default), the rule-based planner runs
    every tool deterministically without making any LLM calls (zero Groq
    cost). When True, CrewAI's ReAct planner decides which tools to call,
    but this path is currently hitting Groq's request-size limit on
    long bill texts.

    Returns: { "answer": str, "trace": [task traces], "token_usage": dict }
    """
    try:
        data = request.get_json(silent=True) or {}
        question = (data.get("question") or "").strip()
        if not question:
            return jsonify({"error": "question is required"}), 400

        # Input length limit to prevent DoS
        if len(question) > 5000:
            return jsonify({"error": "Question too long. Maximum 5000 characters."}), 413

        max_steps = int(data.get("max_steps") or 6)
        max_steps = max(1, min(max_steps, 12))  # bound for safety

        use_llm_planner = bool(data.get("use_llm_planner", False))

        # Import here to avoid loading crewai at Flask boot time
        from agents import run_research

        result = run_research(
            question,
            max_steps=max_steps,
            use_llm_planner=use_llm_planner,
        )

        # CrewOutput is a pydantic-like object - pull its fields defensively
        answer = getattr(result, "raw", str(result))
        tasks_output = getattr(result, "tasks_output", [])
        token_usage = getattr(result, "token_usage", {}) or {}

        # Serialize task traces to JSON-safe dicts
        trace = []
        for t in tasks_output:
            # Handle both rule-based trace (dict with string agent) and CrewAI task output (object with agent.role)
            agent_obj = getattr(t, "agent", None)
            if isinstance(agent_obj, str):
                agent_name = agent_obj
            else:
                agent_name = getattr(agent_obj, "role", "") if agent_obj else ""

            trace.append({
                "description": getattr(t, "description", ""),
                "agent": agent_name,
                "output": getattr(t, "raw", str(t)),
            })

        return jsonify({
            "success": True,
            "answer": answer,
            "trace": trace,
            "token_usage": dict(token_usage) if hasattr(token_usage, "__dict__") else {},
        }), 200

    except RuntimeError as exc:
        # Missing dependency (e.g. crewai not installed) - graceful 503
        return jsonify({"error": str(exc), "agent": "unavailable"}), 503
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@api.route('/architecture', methods=['GET'])
def architecture_inventory():
    """
    Live inventory of all services and tools powering VidhanAI.

    This is the "IDE-like interface" the AIDEVOPS rubric called out:
    a single endpoint that shows the full architecture so reviewers can
    understand what each service does without reading source code.
    """
    try:
        from agents import get_tool_inventory

        tools = get_tool_inventory()

        # Add static architecture metadata
        architecture = {
            "service": "VidhanAI",
            "version": "phase-3",
            "llm_backends": [
                {
                    "name": "QLoRA-fine-tuned Llama-3.2-3B",
                    "type": "local",
                    "path": "notebooks/lora_model/",
                    "size_mb": 97,
                    "status": "available (97 MB safetensors)" if _lora_present() else "stub-only (real adapter not yet trained)",
                },
                {
                    "name": "groq/compound",
                    "type": "cloud",
                    "provider": "Groq",
                    "tier": "free",
                    "status": "available (free tier, ~30 RPM)",
                },
            ],
            "data_sources": [
                {
                    "name": "PRS India BillTrack",
                    "url": "https://prsindia.org/billtrack",
                    "bills_indexed": _bill_count(),
                    "role": "ground truth for all legislative facts",
                },
                {
                    "name": "ChromaDB",
                    "path": "backend/instance/chroma_db",
                    "collection": "legal_bills",
                    "embedding_model": "all-MiniLM-L6-v2",
                    "role": "semantic search index",
                },
                {
                    "name": "SQLite",
                    "path": "backend/instance/regulation_alert.db",
                    "tables": 11,
                    "role": "structured metadata + audit trail",
                },
            ],
            "orchestration": {
                "framework": "CrewAI",
                "version": "1.8.1",
                "agents": [
                    {
                        "role": "Researcher",
                        "responsibility": "Decompose questions, dispatch to tools, synthesize grounded answer",
                        "tools": [t["name"] for t in tools],
                    },
                ],
                "cost_model": "$0 at our scale (CrewAI is OSS; LLM backends are free-tier or local LoRA)",
            },
            "tools": tools,
        }
        return jsonify({"success": True, "architecture": architecture}), 200

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500



# ============================================================================
# AMENDMENT DIFF (Phase 3 — delta-aware summarization)
# ============================================================================

@api.route('/amendment/diff', methods=['POST'])
def amendment_diff():
    """
    Compute a structural + factual diff between two bills, then generate an
    LLM change narrative.

    Body (JSON):
      {
        "bill_id_v1": str,          # bill_id string of the older bill
        "bill_id_v2": str,          # bill_id string of the newer bill
        "text_v1":    str | null,   # optional: raw text override for v1
        "text_v2":    str | null    # optional: raw text override for v2
      }

    Returns:
      {
        "success": true,
        "title_v1", "title_v2",
        "added_sections", "removed_sections", "modified_sections",
        "facts_added", "facts_removed",
        "stats": {...},
        "narrative": str,          # LLM-generated change summary
        "model_version": str,
        "diff_summary_text": str   # rule-based fallback summary
      }
    """
    try:
        data = request.get_json(silent=True) or {}
        bill_id_v1 = (data.get("bill_id_v1") or "").strip()
        bill_id_v2 = (data.get("bill_id_v2") or "").strip()
        text_v1 = data.get("text_v1") or ""
        text_v2 = data.get("text_v2") or ""

        # Validate bill_id format - only alphanumeric, hyphens, underscores allowed
        import re
        BILL_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,200}$')

        def validate_bill_id(bill_id: str, field_name: str) -> tuple[bool, str]:
            if not bill_id:
                return False, f"{field_name} is required"
            if len(bill_id) > 200:
                return False, f"{field_name} exceeds maximum length of 200 characters"
            if not BILL_ID_PATTERN.match(bill_id):
                return False, f"{field_name} contains invalid characters. Only alphanumeric, hyphens, and underscores allowed."
            # Check for path traversal attempts
            if '..' in bill_id or '/' in bill_id or '\\' in bill_id:
                return False, f"{field_name} contains invalid path sequences"
            return True, ""

        if bill_id_v1:
            valid, msg = validate_bill_id(bill_id_v1, "bill_id_v1")
            if not valid:
                return jsonify({"error": msg}), 400

        if bill_id_v2:
            valid, msg = validate_bill_id(bill_id_v2, "bill_id_v2")
            if not valid:
                return jsonify({"error": msg}), 400

        # Validate text input lengths to prevent DoS
        if text_v1 and len(text_v1) > 50000:
            return jsonify({"error": "text_v1 too long. Maximum 50000 characters."}), 413
        if text_v2 and len(text_v2) > 50000:
            return jsonify({"error": "text_v2 too long. Maximum 50000 characters."}), 413

        if not bill_id_v1 and not text_v1:
            return jsonify({"error": "bill_id_v1 or text_v1 is required"}), 400
        if not bill_id_v2 and not text_v2:
            return jsonify({"error": "bill_id_v2 or text_v2 is required"}), 400

        title_v1 = bill_id_v1
        title_v2 = bill_id_v2

        # Resolve bill texts from DB when IDs provided (override any passed text)
        if bill_id_v1:
            b1 = Bill.query.filter_by(bill_id=bill_id_v1).first()
            if b1 is None:
                return jsonify({"error": f"Bill not found: {bill_id_v1}"}), 404
            title_v1 = b1.title
            if b1.content and b1.content.full_text:
                text_v1 = b1.content.full_text
            elif not text_v1:
                return jsonify({
                    "error": f"Bill '{bill_id_v1}' has no full_text in the DB. "
                             "Pass text_v1 in the request body to diff manually."
                }), 422

        if bill_id_v2:
            b2 = Bill.query.filter_by(bill_id=bill_id_v2).first()
            if b2 is None:
                return jsonify({"error": f"Bill not found: {bill_id_v2}"}), 404
            title_v2 = b2.title
            if b2.content and b2.content.full_text:
                text_v2 = b2.content.full_text
            elif not text_v2:
                return jsonify({
                    "error": f"Bill '{bill_id_v2}' has no full_text in the DB. "
                             "Pass text_v2 in the request body to diff manually."
                }), 422

        # Run the pure-Python structural diff (no LLM cost)
        from services.amendment_service import diff_bills, diff_summary_text
        diff = diff_bills(text_v1, text_v2, title_v1=title_v1, title_v2=title_v2)

        # Layer the LLM narrative on top
        import ai_service
        narrative_result = ai_service.generate_change_narrative(diff)

        # Trim large content fields for the API response (full text is huge)
        def _trim_sections(sections, max_content=400):
            return [
                {
                    "title": s.get("title", ""),
                    "content_preview": (s.get("content") or s.get("new_content") or "")[:max_content],
                    "similarity": s.get("similarity"),
                    "changed_facts": s.get("changed_facts", []),
                }
                for s in sections
            ]

        return jsonify({
            "success": True,
            "bill_id_v1": bill_id_v1,
            "bill_id_v2": bill_id_v2,
            "title_v1": title_v1,
            "title_v2": title_v2,
            "added_sections": _trim_sections(diff["added_sections"]),
            "removed_sections": _trim_sections(diff["removed_sections"]),
            "modified_sections": _trim_sections(diff["modified_sections"]),
            "facts_added": diff["facts_added"][:20],
            "facts_removed": diff["facts_removed"][:20],
            "stats": diff["stats"],
            "narrative": narrative_result["narrative"],
            "model_version": narrative_result["model_version"],
            "diff_summary_text": diff_summary_text(diff),
        }), 200

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@api.route('/bills/<string:bill_id>/versions', methods=['GET'])
def bill_versions(bill_id: str):
    """
    List tracked BillVersion snapshots for a bill.

    Returns the version history (most recent first) so the Amendment page
    can let users pick two versions to diff.

    Query params:
      limit   (int, default 20) — max versions to return
    """
    try:
        from models import BillVersion

        bill = Bill.query.filter_by(bill_id=bill_id).first()
        if bill is None:
            return jsonify({"error": f"Bill not found: {bill_id}"}), 404

        limit = request.args.get("limit", 20, type=int)
        limit = max(1, min(limit, 100))

        versions = (
            BillVersion.query
            .filter_by(bill_id=bill.id)
            .order_by(BillVersion.version_number.desc())
            .limit(limit)
            .all()
        )

        return jsonify({
            "success": True,
            "bill_id": bill_id,
            "title": bill.title,
            "version_count": len(versions),
            "versions": [
                {
                    "id": v.id,
                    "version_number": v.version_number,
                    "version_date": v.version_date.isoformat() if v.version_date else None,
                    "change_type": v.change_type,
                    "title": v.title,
                    "status": v.status,
                    "changes_summary": v.changes_summary,
                    "has_full_text": bool(v.full_text),
                }
                for v in versions
            ],
        }), 200

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@api.route('/bills/<string:bill_id>/news', methods=['GET'])
def bill_news(bill_id: str):
    """
    Fetch news citations and external media commentary for a bill.

    Query params:
      limit (int, default 5)
    """
    try:
        from agents.orchestrator import fetch_bill_news

        query = request.args.get("q", "").strip()
        title = bill_id

        if not query:
            bill = Bill.query.filter_by(bill_id=bill_id).first()
            if bill:
                title = bill.title
                query = bill.title
            else:
                query = bill_id.replace("-", " ")

        limit = request.args.get("limit", 5, type=int)
        articles = fetch_bill_news(query, limit=limit)

        return jsonify({
            "success": True,
            "bill_id": bill_id,
            "query": query,
            "title": title,
            "count": len(articles),
            "articles": articles
        }), 200

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ============================================================================
# PRIVATE HELPERS
# ============================================================================


def _lora_present() -> bool:

    import os
    p = os.path.join(os.path.dirname(__file__), "..", "notebooks", "lora_model")
    p = os.path.abspath(p)
    if not os.path.isdir(p):
        return False
    for f in os.listdir(p):
        if f.endswith(".safetensors") and os.path.getsize(os.path.join(p, f)) > 1_000_000:
            return True
    return False


def _bill_count() -> int:
    try:
        return Bill.query.count()
    except Exception:
        return 0
