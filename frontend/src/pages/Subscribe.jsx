import { useState } from 'react';
import { Mail, Key, Landmark, Clock, Bell, Zap, ShieldCheck, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import './Subscribe.css';

export default function Subscribe() {
  const [formData, setFormData] = useState({
    email: '',
    specific_bills: '',
    keywords: '',
    ministries: '',
    email_frequency: 'instant'
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  // Check URL for bill_id parameter to pre-fill the form
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const billId = params.get('bill_id');
    if (billId) {
      setFormData(prev => ({
        ...prev,
        specific_bills: billId
      }));
    }
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage({ type: '', text: '' });

    try {
      // Parse comma-separated lists
      const specificBillsArray = formData.specific_bills
        .split(',')
        .map(b => b.trim())
        .filter(b => b.length > 0);
        
      const keywordsArray = formData.keywords
        .split(',')
        .map(k => k.trim())
        .filter(k => k.length > 0);
      
      const ministriesArray = formData.ministries
        .split(',')
        .map(m => m.trim())
        .filter(m => m.length > 0);

      const response = await fetch('http://localhost:5000/api/subscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: formData.email,
          specific_bills: specificBillsArray,
          keywords: keywordsArray,
          ministries: ministriesArray,
          email_frequency: formData.email_frequency
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // Trigger n8n confirmation workflow
        try {
          await fetch('http://localhost:5678/webhook/subscription-confirmation', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              email: data.subscription.email,
              specific_bills: data.subscription.specific_bills,
              keywords: data.subscription.keywords,
              ministries: data.subscription.ministries,
              email_frequency: data.subscription.email_frequency,
              subscription_id: data.subscription.id,
              welcome_alerts: data.welcome_alerts
            })
          });
        } catch (webhookError) {
          console.error('Webhook error:', webhookError);
        }

        setMessage({
          type: 'success',
          text: data.message + ' Check your email for confirmation.'
        });
        // Reset form
        setFormData({
          email: '',
          specific_bills: '',
          keywords: '',
          ministries: '',
          email_frequency: 'instant'
        });
      } else {
        setMessage({
          type: 'error',
          text: data.error || 'Failed to subscribe. Please try again.'
        });
      }
    } catch (error) {
      console.error('Subscription error:', error);
      setMessage({
        type: 'error',
        text: 'Network error. Please check your connection and try again.'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  return (
    <div className="alerts-page">
      <div className="alerts-layout">
        {/* Left Side: Value Proposition */}
        <div className="alerts-sidebar">
          <div className="sidebar-content">
            <h1 className="alerts-title">Intelligent Legislative Alerts</h1>
            <p className="alerts-subtitle">
              Stay ahead of regulatory changes. Configure custom parameters and receive AI-summarized insights the moment relevant bills are published.
            </p>

            <div className="feature-list">
              <div className="feature-item">
                <div className="feature-icon-wrapper">
                  <Zap className="feature-icon" size={20} />
                </div>
                <div className="feature-text">
                  <h3>Real-time Tracking</h3>
                  <p>Get notified instantly when a bill is introduced or updated in parliament.</p>
                </div>
              </div>

              <div className="feature-item">
                <div className="feature-icon-wrapper">
                  <CheckCircle2 className="feature-icon" size={20} />
                </div>
                <div className="feature-text">
                  <h3>AI Summarization</h3>
                  <p>Receive concise, accurate summaries of complex legal text powered by fine-tuned models.</p>
                </div>
              </div>

              <div className="feature-item">
                <div className="feature-icon-wrapper">
                  <ShieldCheck className="feature-icon" size={20} />
                </div>
                <div className="feature-text">
                  <h3>Zero Noise</h3>
                  <p>Strict keyword matching ensures you only see legislation that impacts your domain.</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Subscription Form */}
        <div className="alerts-main">
          <div className="form-card">
            <div className="form-header">
              <h2>Configure Your Alert</h2>
              <p>Set up your notification preferences</p>
            </div>

            <form className="alerts-form" onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="email">
                  <Mail size={16} />
                  Email Address
                </label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="name@company.com"
                  required
                  className="modern-input"
                />
              </div>

              <div className="form-group">
                <label htmlFor="specific_bills">
                  <ShieldCheck size={16} />
                  Track Specific Bills
                </label>
                <input
                  type="text"
                  id="specific_bills"
                  name="specific_bills"
                  value={formData.specific_bills}
                  onChange={handleChange}
                  placeholder="e.g. 7, BILL-123"
                  className="modern-input"
                />
                <span className="input-help">Get an immediate summary for these specific Bill IDs.</span>
              </div>

              <div className="form-group">
                <label htmlFor="keywords">
                  <Key size={16} />
                  Tracked Keywords
                </label>
                <input
                  type="text"
                  id="keywords"
                  name="keywords"
                  value={formData.keywords}
                  onChange={handleChange}
                  placeholder="finance, technology, tax, environment"
                  className="modern-input"
                />
                <span className="input-help">Separate multiple keywords with commas.</span>
              </div>

              <div className="form-group">
                <label htmlFor="ministries">
                  <Landmark size={16} />
                  Target Ministries
                </label>
                <input
                  type="text"
                  id="ministries"
                  name="ministries"
                  value={formData.ministries}
                  onChange={handleChange}
                  placeholder="Ministry of Finance"
                  className="modern-input"
                />
                <span className="input-help">Leave blank to monitor all ministries.</span>
              </div>

              <div className="form-group">
                <label htmlFor="email_frequency">
                  <Clock size={16} />
                  Notification Frequency
                </label>
                <div className="select-wrapper">
                  <select
                    id="email_frequency"
                    name="email_frequency"
                    value={formData.email_frequency}
                    onChange={handleChange}
                    className="modern-select"
                  >
                    <option value="instant">Instant (Recommended)</option>
                    <option value="daily">Daily Digest</option>
                    <option value="weekly">Weekly Summary</option>
                  </select>
                </div>
              </div>

              {message.text && (
                <div className={`status-message ${message.type}`}>
                  {message.type === 'success' ? (
                    <CheckCircle2 size={18} />
                  ) : (
                    <AlertCircle size={18} />
                  )}
                  <span>{message.text}</span>
                </div>
              )}

              <button type="submit" className="modern-submit-btn" disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="spin-icon" size={18} />
                    Processing...
                  </>
                ) : (
                  <>
                    <Bell size={18} />
                    Create Alert Subscription
                  </>
                )}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
