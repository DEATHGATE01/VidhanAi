# New Models to Add to backend/models.py

class UserSubscription(db.Model):
    """User alert subscriptions"""
    __tablename__ = 'user_subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), nullable=False, index=True)
    keywords = db.Column(db.JSON)  # List of keywords: ["animal welfare", "tax", "gaming"]
    ministries = db.Column(db.JSON)  # List of ministries to track
    is_active = db.Column(db.Boolean, default=True)
    
    # Notification preferences
    email_frequency = db.Column(db.String(20), default='instant')  # 'instant', 'daily', 'weekly'
    last_notified = db.Column(db.DateTime)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BillNotification(db.Model):
    """Track which bills were sent to which users"""
    __tablename__ = 'bill_notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('user_subscriptions.id'), nullable=False)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'), nullable=False)
    
    # Notification details
    matched_keywords = db.Column(db.JSON)  # Which keywords matched
    summary = db.Column(db.Text)  # Cached summary sent
    email_sent = db.Column(db.Boolean, default=False)
    email_sent_at = db.Column(db.DateTime)
    email_opened = db.Column(db.Boolean, default=False)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
