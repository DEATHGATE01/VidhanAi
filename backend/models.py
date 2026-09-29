"""
Database Models for Regulation Alert System - Enhanced for Big Data Analysis
- Bill: Stores bill metadata
- BillContent: Stores full bill text and structured data
- User: User accounts and authentication
- UserFavorite: User bookmarked bills
- UserReadingHistory: Track reading behavior (Big Data analytics)
- BillVersion: Historical bill versions (trend analysis)
- BillSummary: AI-generated summaries
- SearchHistory: Search analytics (aggregated after 90 days)
- SearchAnalytics: Long-term aggregated search data
- Act: First-class Act records (an Act is the law; a Bill is not)
- BillActLink: Bill -> Act relationship (enacted_as / replaced_by_act / ...)
- LifecycleEvent: Sourced lifecycle events for bills and acts
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Bill(db.Model):
    """Bill metadata - lightweight for fast search"""
    __tablename__ = 'bills'
    
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.String(200), unique=True, nullable=False, index=True)
    title = db.Column(db.String(500), nullable=False, index=True)
    ministry = db.Column(db.String(200), index=True)
    status = db.Column(db.String(100))
    url = db.Column(db.String(500), nullable=False)
    introduction_date = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    date_scraped = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to content
    content = db.relationship('BillContent', backref='bill', uselist=False, cascade='all, delete-orphan')
    
    # Relationship to summary
    summary = db.relationship('BillSummary', backref='bill', uselist=False, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Bill {self.bill_id}: {self.title[:50]}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'bill_id': self.bill_id,
            'title': self.title,
            'ministry': self.ministry,
            'status': self.status,
            'url': self.url,
            'introduction_date': self.introduction_date.isoformat() if self.introduction_date else None,
            'date_scraped': self.date_scraped.isoformat() if self.date_scraped else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }


class BillContent(db.Model):
    """Bill full content - fetched on-demand"""
    __tablename__ = 'bill_contents'
    
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'), nullable=False, unique=True)
    
    # Full text content
    full_text = db.Column(db.Text)
    
    # Structured data (stored as JSON)
    sections = db.Column(db.JSON)  # List of {section: str, content: str}
    paragraphs = db.Column(db.JSON)  # List of paragraph strings
    
    # Links
    summary_link = db.Column(db.String(500))
    pdf_link = db.Column(db.String(500))
    
    # Timestamp
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<BillContent for Bill ID {self.bill_id}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'bill_id': self.bill_id,
            'sections': self.sections,
            'paragraphs': self.paragraphs,
            'summary_link': self.summary_link,
            'pdf_link': self.pdf_link,
            'fetched_at': self.fetched_at.isoformat() if self.fetched_at else None
        }


class SearchHistory(db.Model):
    """Track user searches for analytics (90-day retention)"""
    __tablename__ = 'search_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # nullable for anonymous
    keyword = db.Column(db.String(200), index=True)
    results_count = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<Search "{self.keyword}" at {self.timestamp}>'


class User(db.Model):
    """User accounts"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Profile
    full_name = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    favorites = db.relationship('UserFavorite', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    reading_history = db.relationship('UserReadingHistory', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    searches = db.relationship('SearchHistory', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'full_name': self.full_name,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class UserFavorite(db.Model):
    """User bookmarked/favorite bills"""
    __tablename__ = 'user_favorites'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'), nullable=False, index=True)
    
    # Metadata
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)  # User's personal notes
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'bill_id', name='unique_user_favorite'),)
    
    def __repr__(self):
        return f'<UserFavorite user={self.user_id} bill={self.bill_id}>'


class UserReadingHistory(db.Model):
    """Track what users read (Big Data analytics)"""
    __tablename__ = 'user_reading_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)  # nullable for anonymous
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'), nullable=False, index=True)
    
    # Analytics data
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    time_spent_seconds = db.Column(db.Integer)  # How long user read
    scroll_depth_percent = db.Column(db.Integer)  # How far user scrolled (0-100)
    source = db.Column(db.String(50))  # 'search', 'favorite', 'recommendation'
    
    def __repr__(self):
        return f'<ReadingHistory user={self.user_id} bill={self.bill_id}>'


class BillVersion(db.Model):
    """Historical versions of bills (track changes over time)"""
    __tablename__ = 'bill_versions'
    
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'), nullable=False, index=True)
    
    # Version info
    version_number = db.Column(db.Integer, nullable=False)
    version_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    change_type = db.Column(db.String(50))  # 'introduced', 'amended', 'passed', 'rejected'
    
    # Content snapshot
    title = db.Column(db.String(500))
    status = db.Column(db.String(100))
    full_text = db.Column(db.Text)
    sections = db.Column(db.JSON)
    
    # Change summary
    changes_summary = db.Column(db.Text)  # What changed from previous version
    
    def __repr__(self):
        return f'<BillVersion bill={self.bill_id} v{self.version_number}>'


class BillSummary(db.Model):
    """AI-generated summaries of bills"""
    __tablename__ = 'bill_summaries'
    
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'), nullable=False, unique=True)
    
    # Main summary
    summary = db.Column(db.Text)  # Full AI-generated summary
    summary_type = db.Column(db.String(50))  # 'extractive', 'quick', 'full'
    confidence = db.Column(db.Float, default=0.5)  # Confidence score 0-1
    
    # Legacy fields (for future enhancements)
    short_summary = db.Column(db.Text)  # 2-3 sentences
    detailed_summary = db.Column(db.Text)  # 1-2 paragraphs
    key_points = db.Column(db.JSON)  # List of bullet points
    
    # NLP analytics (future)
    sentiment_score = db.Column(db.Float)  # -1 to 1
    complexity_score = db.Column(db.Float)  # 0 to 10
    keywords = db.Column(db.JSON)  # Top keywords with weights
    topics = db.Column(db.JSON)  # Topic modeling results
    
    # Metadata
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    model_version = db.Column(db.String(100))  # Which AI model generated it (e.g. 'groq_groq/compound', 'local_lora_...', 'rule_based_extractive_v1')
    guardrail_applied = db.Column(db.Boolean, default=True)  # Disclaimer appended
    guardrail_version = db.Column(db.String(50))  # Identifier for the disclaimer/guardrail set used
    
    def __repr__(self):
        return f'<BillSummary bill={self.bill_id}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'bill_id': self.bill_id,
            'summary': self.summary,
            'summary_type': self.summary_type,
            'confidence': self.confidence,
            'model_version': self.model_version,
            'guardrail_applied': self.guardrail_applied,
            'guardrail_version': self.guardrail_version,
            'sentiment_score': self.sentiment_score,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None
        }


class SearchAnalytics(db.Model):
    """Aggregated search analytics (long-term storage)"""
    __tablename__ = 'search_analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Aggregation period
    period_start = db.Column(db.Date, nullable=False, index=True)
    period_end = db.Column(db.Date, nullable=False)
    period_type = db.Column(db.String(20))  # 'daily', 'weekly', 'monthly'
    
    # Aggregated data
    keyword = db.Column(db.String(200), index=True)
    search_count = db.Column(db.Integer)
    unique_users = db.Column(db.Integer)
    avg_results = db.Column(db.Float)
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('period_start', 'period_type', 'keyword', name='unique_period_keyword'),)
    
    def __repr__(self):
        return f'<SearchAnalytics {self.keyword} {self.period_start}>'


class UserSubscription(db.Model):
    """User alert subscriptions for automated notifications"""
    __tablename__ = 'user_subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), nullable=False, index=True)
    
    # Subscription preferences
    specific_bills = db.Column(db.JSON)  # List of bill IDs the user specifically wants to track
    keywords = db.Column(db.JSON)  # List of keywords: ["animal welfare", "tax", "gaming"]
    ministries = db.Column(db.JSON)  # List of ministries to track
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Notification preferences
    email_frequency = db.Column(db.String(20), default='instant')  # 'instant', 'daily', 'weekly'
    last_notified = db.Column(db.DateTime)  
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    notifications = db.relationship('BillNotification', backref='subscription', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<UserSubscription {self.email} - {len(self.keywords or [])} keywords>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'specific_bills': self.specific_bills or [],
            'keywords': self.keywords or [],
            'ministries': self.ministries or [],
            'is_active': self.is_active,
            'email_frequency': self.email_frequency,
            'last_notified': self.last_notified.isoformat() if self.last_notified else None,
            'created_at': self.created_at.isoformat()
        }


class BillNotification(db.Model):
    """Track which bills were sent to which users"""
    __tablename__ = 'bill_notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('user_subscriptions.id'), nullable=False, index=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'), nullable=False, index=True)
    
    # Notification details
    matched_keywords = db.Column(db.JSON)  # Which keywords matched
    summary_sent = db.Column(db.Text)  # Cached summary sent in email
    # Status snapshot at alert time — lets /check-new-bills detect status
    # changes for specifically-tracked bills and re-alert by updating this row.
    bill_status = db.Column(db.String(100))
    
    # Email tracking
    email_sent = db.Column(db.Boolean, default=False, index=True)
    email_sent_at = db.Column(db.DateTime)
    email_opened = db.Column(db.Boolean, default=False)
    email_clicked = db.Column(db.Boolean, default=False)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Unique constraint - don't send same bill to same user twice
    __table_args__ = (db.UniqueConstraint('subscription_id', 'bill_id', name='unique_subscription_bill'),)
    
    def __repr__(self):
        return f'<BillNotification sub:{self.subscription_id} bill:{self.bill_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'subscription_id': self.subscription_id,
            'bill_id': self.bill_id,
            'matched_keywords': self.matched_keywords or [],
            'email_sent': self.email_sent,
            'email_sent_at': self.email_sent_at.isoformat() if self.email_sent_at else None,
            'created_at': self.created_at.isoformat()
        }


class Act(db.Model):
    """A central Act as a first-class object (the law itself, not the Bill).

    act_id is the slugified PRS PDF basename (stable, unique, re-scrapable).
    Every date field stays NULL unless it came from scraped content with a
    source_url -- never estimated, never invented.
    """
    __tablename__ = 'acts'

    id = db.Column(db.Integer, primary_key=True)
    act_id = db.Column(db.String(200), unique=True, nullable=False, index=True)
    title = db.Column(db.String(500), nullable=False, index=True)
    short_title = db.Column(db.String(300), index=True)  # normalized, no leading "The"/year
    year = db.Column(db.Integer, index=True)             # from the PRS PDF path segment
    act_number = db.Column(db.String(50))                # e.g. "No. 12 of 2026" -- only if sourced
    assent_date = db.Column(db.DateTime)                 # only if sourced
    commencement_date = db.Column(db.DateTime)           # only if sourced
    status = db.Column(db.String(50), default='unknown')  # in_force | repealed | spent | unknown
    source = db.Column(db.String(50))                    # 'prs_acts' | 'indiacode'
    source_url = db.Column(db.String(500))
    pdf_url = db.Column(db.String(500))
    full_text = db.Column(db.Text)
    date_scraped = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    links = db.relationship('BillActLink', backref='act', lazy='dynamic', cascade='all, delete-orphan')
    lifecycle_events = db.relationship('LifecycleEvent', backref='act', lazy='dynamic')

    def __repr__(self):
        return f'<Act {self.act_id}: {self.title[:50]}>'

    def to_dict(self):
        return {
            'id': self.id,
            'act_id': self.act_id,
            'title': self.title,
            'short_title': self.short_title,
            'year': self.year,
            'act_number': self.act_number,
            'assent_date': self.assent_date.isoformat() if self.assent_date else None,
            'commencement_date': self.commencement_date.isoformat() if self.commencement_date else None,
            'status': self.status,
            'source': self.source,
            'source_url': self.source_url,
            'pdf_url': self.pdf_url,
            'date_scraped': self.date_scraped.isoformat() if self.date_scraped else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }


class BillActLink(db.Model):
    """Bill -> Act relationship with explainable, sourced matching.

    match_method: 'prs_status' | 'title_match' | 'body_mention' | 'manual'.
    evidence always quotes the exact scraped text/URL that justifies the link;
    verified=True is only ever set for an exact normalized title match or a
    direct PRS status derivation.
    """
    __tablename__ = 'bill_act_links'

    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'), nullable=False, index=True)
    act_id = db.Column(db.Integer, db.ForeignKey('acts.id'), nullable=False, index=True)
    link_type = db.Column(db.String(50))   # enacted_as | replaced_by_act | amended_by_act | repealed_by
    match_method = db.Column(db.String(50))
    match_confidence = db.Column(db.Float)  # 0..1
    evidence = db.Column(db.Text)
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('bill_id', 'act_id', 'link_type', name='unique_bill_act_link'),)

    def __repr__(self):
        return f'<BillActLink bill={self.bill_id} act={self.act_id} {self.link_type}>'

    def to_dict(self):
        return {
            'id': self.id,
            'bill_id': self.bill_id,
            'act_id': self.act_id,
            'link_type': self.link_type,
            'match_method': self.match_method,
            'match_confidence': self.match_confidence,
            'evidence': self.evidence,
            'verified': self.verified,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class LifecycleEvent(db.Model):
    """A sourced lifecycle event for a bill and/or act.

    event_type: introduced | referred_to_committee | committee_report |
    passed_lok_sabha | passed_rajya_sabha | passed_both_houses |
    president_assent | act_notified | commencement | amendment | repeal | other.

    event_date is NULL when the source does not state one. is_estimated must be
    False for everything this work creates: False implies source and source_url
    are set (enforced by verify_acts.py).
    """
    __tablename__ = 'lifecycle_events'

    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'), index=True)
    act_id = db.Column(db.Integer, db.ForeignKey('acts.id'), index=True)
    event_type = db.Column(db.String(50), nullable=False)
    event_date = db.Column(db.DateTime)   # NULL when the source does not state one
    house = db.Column(db.String(50))
    source = db.Column(db.String(50))     # prs_billtrack | prs_acts | indiacode | manual
    source_url = db.Column(db.String(500))
    notes = db.Column(db.Text)
    is_estimated = db.Column(db.Boolean, default=False)
    extracted_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('bill_id', 'act_id', 'event_type', 'event_date',
                                          name='unique_lifecycle_event'),)

    # Relationships
    bill = db.relationship('Bill', backref='lifecycle_events')

    def __repr__(self):
        return f'<LifecycleEvent bill={self.bill_id} act={self.act_id} {self.event_type} {self.event_date}>'

    def to_dict(self):
        return {
            'id': self.id,
            'bill_id': self.bill_id,
            'act_id': self.act_id,
            'event_type': self.event_type,
            'event_date': self.event_date.isoformat() if self.event_date else None,
            'house': self.house,
            'source': self.source,
            'source_url': self.source_url,
            'notes': self.notes,
            'is_estimated': self.is_estimated,
            'extracted_at': self.extracted_at.isoformat() if self.extracted_at else None
        }
