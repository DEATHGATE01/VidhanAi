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
    Query params: keyword, user_id (optional)
    """
    keyword = request.args.get('keyword', '').strip()
    user_id = request.args.get('user_id', type=int)
    
    if not keyword:
        return jsonify({'error': 'Keyword is required'}), 400
    
    try:
        from flask import current_app
        results = db_service.search_bills(keyword, current_app, user_id=user_id)
        
        return jsonify({
            'success': True,
            'keyword': keyword,
            'count': len(results),
            'results': results
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
        
        # Check if we have an error but still have bill metadata
        if 'error' in content:
            # If we have bill data, return it with error message
            if 'bill' in content:
                bill_data = content['bill']
                return jsonify({
                    'success': True,
                    'bill': bill_data,
                    'source': content.get('source', 'unavailable'),
                    'content_error': content['error'],  # Frontend can show this
                    'content_status': 'unavailable'
                }), 200
            else:
                # Bill not found at all
                return jsonify({'success': False, 'error': content['error']}), 404
        
        # Merge bill and content data for frontend
        bill_data = content.get('bill', {})
        content_data = content.get('content', {})
        
        # Combine them
        response_data = {**bill_data}
        if content_data:
            response_data['content'] = content_data
            
        # =========================================================
        # INJECT ADVANCED ML FEATURES FROM VidhanAI(temp)
        # =========================================================
        import os
        import json
        
        v2_data_dir = os.path.join(current_app.root_path, '..', 'VidhanAI(temp)', 'data')
        
        # The URL parameter `bill_id` is an integer (primary key)
        # The JSON files use the string slug `bill_id`
        slug_id = response_data.get('bill_id', str(bill_id))
        
        # 1. Sentiment
        sentiment_path = os.path.join(v2_data_dir, 'sentiment', f"{slug_id}_sentiment.json")
        if os.path.exists(sentiment_path):
            try:
                with open(sentiment_path, 'r', encoding='utf-8') as f:
                    sentiment_data = json.load(f)
                    # Compute sentiment distribution
                    dist = {"positive": 0, "neutral": 0, "negative": 0}
                    items = sentiment_data.get("items", [])
                    for item in items:
                        if isinstance(item, dict):
                            labels = item.get("labels", {})
                            if isinstance(labels, dict):
                                sentiment_label = labels.get("sentiment", "neutral")
                                if sentiment_label in dist:
                                    dist[sentiment_label] += 1
                    
                    response_data['sentiment'] = {
                        "sentiment_distribution": dist,
                        "items_count": len(items)
                    }
            except Exception as e:
                print(f"Error loading sentiment: {e}")
                
        # 2. Timeline
        timeline_path = os.path.join(v2_data_dir, 'timeline', f"{slug_id}_timeline.json")
        if os.path.exists(timeline_path):
            try:
                with open(timeline_path, 'r', encoding='utf-8') as f:
                    response_data['timeline'] = json.load(f)
            except Exception as e:
                print(f"Error loading timeline: {e}")
                
        # 3. Linked News
        linked_path = os.path.join(v2_data_dir, 'linked', f"{slug_id}_linked_news.json")
        if os.path.exists(linked_path):
            try:
                with open(linked_path, 'r', encoding='utf-8') as f:
                    linked_data = json.load(f)
                    response_data['linked_news'] = {
                        "news_items": linked_data.get("linked_news", [])
                    }
            except Exception as e:
                print(f"Error loading linked news: {e}")
        
        return jsonify({
            'success': True,
            'bill': response_data,
            'source': content.get('source', 'database'),
            'content_status': 'available'
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
        data = request.json
        
        if not data.get('email'):
            return jsonify({'error': 'Email is required'}), 400
        
        # Check if subscription already exists
        existing = UserSubscription.query.filter_by(email=data['email']).first()
        
        if existing:
            # Update existing subscription
            existing.keywords = data.get('keywords', [])
            existing.ministries = data.get('ministries', [])
            existing.email_frequency = data.get('email_frequency', 'instant')
            existing.is_active = True
            existing.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Subscription updated',
                'subscription': existing.to_dict()
            }), 200
        else:
            # Create new subscription
            subscription = UserSubscription(
                email=data['email'],
                keywords=data.get('keywords', []),
                ministries=data.get('ministries', []),
                email_frequency=data.get('email_frequency', 'instant')
            )
            db.session.add(subscription)
            db.session.commit()
            
            # Generate welcome alerts for existing matching bills
            welcome_alerts = []
            try:
                # Get ALL bills in database
                all_bills = Bill.query.all()
                
                print(f"🎁 Generating welcome alerts for new subscriber: {subscription.email}")
                print(f"📚 Checking ALL {len(all_bills)} bills in database")
                
                for bill in all_bills:  # Process ALL bills, no limit
                    # Fetch content for better matching
                    bill_text = ""
                    if bill.content:
                        bill_text = f"{bill.content.full_text} {str(bill.content.sections)} {str(bill.content.paragraphs)}"
                    
                    matches = False
                    matched_keywords = []
                    
                    # Check keywords
                    if subscription.keywords:
                        for keyword in subscription.keywords:
                            keyword_lower = keyword.lower()
                            if keyword_lower in bill.title.lower() or \
                               (bill.ministry and keyword_lower in bill.ministry.lower()) or \
                               (bill_text and keyword_lower in bill_text.lower()):
                                matches = True
                                matched_keywords.append(keyword)
                    
                    # Check ministries
                    if subscription.ministries and bill.ministry:
                        for ministry in subscription.ministries:
                            if ministry.lower() in bill.ministry.lower():
                                matches = True
                    
                    if matches:
                        # Check if already notified (shouldn't happen for new subscription)
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
                                matched_keywords=matched_keywords,
                                summary_sent=summary_text
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
                                'matched_keywords': matched_keywords,
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
                
                print(f"✅ Generated {len(welcome_alerts)} welcome alerts")
                
            except Exception as e:
                print(f"⚠️ Error generating welcome alerts: {e}")
                # Don't fail subscription if welcome alerts fail
                import traceback
                print(traceback.format_exc())
            
            return jsonify({
                'success': True,
                'message': 'Subscribed successfully',
                'subscription': subscription.to_dict(),
                'welcome_alerts_count': len(welcome_alerts),
                'welcome_alerts': welcome_alerts  # Return alerts so n8n can send them
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
        
        print(f"🔍 Checking {len(new_bills)} new bills against {len(subscriptions)} subscriptions")
        
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
        
        print(f"✅ Found {len(alerts)} alerts to send")
        
        return jsonify({
            'success': True,
            'new_bills_count': len(new_bills),
            'alerts_count': len(alerts),
            'alerts': alerts
        }), 200
    
    except Exception as e:
        import traceback
        print(f"❌ Error checking new bills: {e}")
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
