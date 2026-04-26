import { useState, useEffect } from 'react';
import { getBillById, getBillSummary } from '../services/api';
import './BillDetailsModal.css';

export default function BillDetailsModal({ billId, onClose, onBillUpdate }) {
  const [billDetails, setBillDetails] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('content');

  useEffect(() => {
    const fetchBillDetails = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await getBillById(billId, 1, true); // user_id=1, track_reading=true
        
        if (response.success) {
          console.log('Bill details loaded:', response.bill);
          console.log('Has content:', !!response.bill.content);
          console.log('Content keys:', response.bill.content ? Object.keys(response.bill.content) : 'no content');
          setBillDetails(response.bill);
          // Notify parent component of updated bill data
          if (onBillUpdate && response.bill) {
            onBillUpdate(response.bill);
          }
        } else {
          setError('Failed to load bill details');
        }
      } catch (err) {
        setError(err.message || 'An error occurred');
        console.error('Error fetching bill details:', err);
      } finally {
        setLoading(false);
      }
    };

    if (billId) {
      fetchBillDetails();
    }
  }, [billId]); // onBillUpdate removed from deps to prevent infinite loop

  // Fetch summary when Summary or Split tab is clicked
  useEffect(() => {
    const fetchSummary = async () => {
      if ((activeTab === 'summary' || activeTab === 'split') && billId && !summary) {
        try {
          setSummaryLoading(true);
          const response = await getBillSummary(billId);
          
          if (response.success) {
            setSummary(response.summary);
          } else {
            // Backend returned error (e.g., content not available)
            console.log('Summary not available:', response.error);
            setSummary(null); // Show empty state message
          }
        } catch (err) {
          console.error('Error fetching summary:', err);
          setSummary(null); // Show empty state message
        } finally {
          setSummaryLoading(false);
        }
      }
    };

    fetchSummary();
  }, [activeTab, billId, summary]);

  const handleBackdropClick = (e) => {
    if (e.target.className === 'modal-backdrop') {
      onClose();
    }
  };

  if (!billId) return null;

  return (
    <div className="modal-backdrop" onClick={handleBackdropClick}>
      <div className="modal-content">
        <div className="modal-header">
          <h2 className="modal-title">Bill Details</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {loading && (
          <div className="modal-body">
            <div className="loading">
              <div className="spinner"></div>
              <p>Loading bill details...</p>
            </div>
          </div>
        )}

        {error && (
          <div className="modal-body">
            <div className="error-message">{error}</div>
          </div>
        )}

        {!loading && !error && billDetails && (
          <>
            <div className="bill-info">
              <h3 className="bill-detail-title">{billDetails.title}</h3>
              <div className="bill-detail-meta">
                {billDetails.ministry && (
                  <span className="bill-tag ministry">🏛️ {billDetails.ministry}</span>
                )}
                {billDetails.status && (
                  <span className="bill-tag status">📋 {billDetails.status}</span>
                )}
                {billDetails.bill_type && (
                  <span className="bill-tag">📄 {billDetails.bill_type}</span>
                )}
              </div>
              {billDetails.introduction_date && (
                <p className="bill-date-info">
                  <strong>Introduced:</strong> {new Date(billDetails.introduction_date).toLocaleDateString('en-IN', { 
                    year: 'numeric', 
                    month: 'long', 
                    day: 'numeric' 
                  })}
                </p>
              )}
            </div>

            <div className="modal-tabs">
              <button 
                className={`tab-button ${activeTab === 'content' ? 'active' : ''}`}
                onClick={() => setActiveTab('content')}
              >
                📄 Original Text
              </button>
              <button 
                className={`tab-button ${activeTab === 'summary' ? 'active' : ''}`}
                onClick={() => setActiveTab('summary')}
              >
                🤖 AI Summary
              </button>
              <button 
                className={`tab-button ${activeTab === 'split' ? 'active' : ''}`}
                onClick={() => setActiveTab('split')}
              >
                🌓 Split View
              </button>
              {billDetails.sentiment && (
                <button 
                  className={`tab-button ${activeTab === 'news' ? 'active' : ''}`}
                  onClick={() => setActiveTab('news')}
                >
                  📈 News & Sentiment
                </button>
              )}
              {billDetails.timeline && (
                <button 
                  className={`tab-button ${activeTab === 'timeline' ? 'active' : ''}`}
                  onClick={() => setActiveTab('timeline')}
                >
                  ⏱️ Timeline
                </button>
              )}
            </div>

            <div className={`modal-body ${activeTab === 'split' ? 'split-view-body' : ''}`}>
              {(activeTab === 'content' || activeTab === 'split') && (
                <div className={`bill-content-section ${activeTab === 'split' ? 'split-pane pane-left' : ''}`}>
                  {activeTab === 'split' && <h3 className="pane-title">📄 Original Legal Text</h3>}
                  {/* Debug info - remove after fixing */}
                  {console.log('Rendering content tab, billDetails:', billDetails)}
                  {console.log('Has content check:', billDetails.content && (
                    (billDetails.content.sections && billDetails.content.sections.length > 0) || 
                    billDetails.content.paragraphs
                  ))}
                  
                  {billDetails.content && (
                    (billDetails.content.sections && billDetails.content.sections.length > 0) || 
                    billDetails.content.paragraphs
                  ) ? (
                    <div className="content-display">
                      {billDetails.content.sections && billDetails.content.sections.length > 0 ? (
                        <div className="sections-list">
                          {billDetails.content.sections.map((section, index) => (
                            <div key={index} className="section-item">
                              <h4 className="section-title">{section.title}</h4>
                              <div className="section-content">
                                {section.paragraphs && section.paragraphs.length > 0 ? (
                                  section.paragraphs.map((para, pIndex) => (
                                    <p key={pIndex} className="section-paragraph">{para}</p>
                                  ))
                                ) : (
                                  <p className="section-paragraph">{section.content || 'No content available'}</p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : billDetails.content.paragraphs ? (
                        <div className="paragraphs-content">
                          <div className="content-text">
                            {(() => {
                              const paras = billDetails.content.paragraphs;
                              // Handle both string and already-parsed formats
                              if (typeof paras === 'string') {
                                // Display as formatted text blocks
                                return paras.split(/\n{2,}/).filter(p => p.trim()).map((para, index) => (
                                  <p key={index} className="content-paragraph">{para.trim()}</p>
                                ));
                              } else if (Array.isArray(paras)) {
                                // Display array of paragraphs
                                return paras.filter(p => p && p.trim()).map((para, index) => (
                                  <p key={index} className="content-paragraph">{para}</p>
                                ));
                              } else {
                                return <p className="content-paragraph">{String(paras)}</p>;
                              }
                            })()}
                          </div>
                          
                          {/* Also show full_text if paragraphs seem incomplete */}
                          {billDetails.content.full_text && (
                            <div className="full-text-section">
                              <h4 style={{marginTop: '20px', color: '#666'}}>Complete Bill Text:</h4>
                              <div style={{whiteSpace: 'pre-wrap', lineHeight: '1.6'}}>
                                {billDetails.content.full_text}
                              </div>
                            </div>
                          )}
                          
                          {billDetails.content.pdf_link && (
                            <div className="pdf-link-container">
                              <a 
                                href={billDetails.content.pdf_link} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="pdf-link"
                              >
                                📄 Download Full Bill PDF
                              </a>
                            </div>
                          )}
                        </div>
                      ) : null}
                    </div>
                  ) : (
                    <div className="empty-state">
                      <p>⏳ <strong>Bill content is being fetched...</strong></p>
                      <p>
                        We're attempting to scrape the full text of this bill from the PRS India website. 
                        {billDetails.content_error && (
                          <span> <strong>Status:</strong> {billDetails.content_error}</span>
                        )}
                      </p>
                      <p>If content fails to load, you can view it directly on the official website:</p>
                      {billDetails.url && (
                        <p>
                          <a 
                            href={billDetails.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="external-link"
                          >
                            📄 View Full Bill on PRS India →
                          </a>
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}

              {(activeTab === 'summary' || activeTab === 'split') && (
                <div className={`bill-summary-section ${activeTab === 'split' ? 'split-pane pane-right' : ''}`}>
                  {activeTab === 'split' && <h3 className="pane-title">🤖 AI Simplified Summary</h3>}
                  {summaryLoading ? (
                    <div className="loading">
                      <div className="spinner"></div>
                      <p>🤖 Generating AI summary...</p>
                    </div>
                  ) : summary ? (
                    <div className="summary-content">
                      <div className="summary-header">
                        <span className="summary-badge">
                          {summary.summary_type === 'api_llm' ? '🤖 AI Generated' : '📝 Extractive AI'}
                        </span>
                        {summary.sentiment_score !== undefined && (
                          <span className={`summary-badge sentiment ${summary.sentiment_score > 0 ? 'positive' : summary.sentiment_score < 0 ? 'negative' : 'neutral'}`}>
                            {summary.sentiment_score > 0 ? '📈 Positive' : summary.sentiment_score < 0 ? '📉 Negative' : '⚖️ Neutral'} ({(summary.sentiment_score * 100).toFixed(0)}%)
                          </span>
                        )}
                        {summary.source === 'generated' && (
                          <span className="summary-new">✨ Just generated</span>
                        )}
                        {summary.generated_at && (
                          <span className="summary-timestamp">
                            Generated: {new Date(summary.generated_at).toLocaleString('en-IN', {
                              dateStyle: 'medium',
                              timeStyle: 'short'
                            })}
                          </span>
                        )}
                      </div>
                      <div className="summary-text" dangerouslySetInnerHTML={{ 
                        __html: summary.summary.replace(/\n/g, '<br/>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/###\s*(.*?)(<br\/>|$)/g, '<h3>$1</h3>').replace(/##\s*(.*?)(<br\/>|$)/g, '<h2>$1</h2>')
                      }} />
                    </div>
                  ) : (
                    <div className="empty-state">
                      <p>⏳ <strong>AI summary cannot be generated yet.</strong></p>
                      <p>The bill content needs to be scraped first before we can generate an AI-powered summary. Please check the "Bill Content" tab or visit PRS India for full details.</p>
                      <p className="summary-placeholder">
                        <strong>Basic Info:</strong><br/>
                        📋 Ministry: {billDetails?.ministry || 'N/A'}<br/>
                        📅 Introduced: {billDetails?.introduction_date ? 
                          new Date(billDetails.introduction_date).toLocaleDateString('en-IN') : 
                          'N/A'
                        }<br/>
                        📊 Status: {billDetails?.status || 'Unknown'}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* NEWS AND SENTIMENT TAB */}
              {activeTab === 'news' && billDetails.sentiment && (
                <div className="bill-news-section" style={{ padding: '1rem' }}>
                  <h3 className="pane-title" style={{ marginBottom: '1.5rem', color: '#f8fafc' }}>📈 News & Public Sentiment</h3>
                  
                  <div className="stats-grid" style={{ marginBottom: '2rem' }}>
                    <div className="stat-card" style={{ background: 'rgba(16, 185, 129, 0.1)', borderColor: 'rgba(16, 185, 129, 0.3)' }}>
                      <div className="stat-value" style={{ color: '#34d399' }}>{billDetails.sentiment.sentiment_distribution?.positive || 0}</div>
                      <div className="stat-label">Positive</div>
                    </div>
                    <div className="stat-card" style={{ background: 'rgba(148, 163, 184, 0.1)', borderColor: 'rgba(148, 163, 184, 0.3)' }}>
                      <div className="stat-value" style={{ color: '#94a3b8' }}>{billDetails.sentiment.sentiment_distribution?.neutral || 0}</div>
                      <div className="stat-label">Neutral</div>
                    </div>
                    <div className="stat-card" style={{ background: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.3)' }}>
                      <div className="stat-value" style={{ color: '#f87171' }}>{billDetails.sentiment.sentiment_distribution?.negative || 0}</div>
                      <div className="stat-label">Negative</div>
                    </div>
                  </div>

                  {billDetails.linked_news && billDetails.linked_news.news_items && billDetails.linked_news.news_items.length > 0 && (
                    <div>
                      <h4 style={{ color: '#cbd5e1', marginBottom: '1rem', fontSize: '1.1rem' }}>Related News Articles</h4>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        {billDetails.linked_news.news_items.map((news, idx) => (
                          <a key={idx} href={news.url || `https://www.google.com/search?q=${encodeURIComponent(news.title + " " + (news.source || ''))}`} target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'none' }}>
                            <div className="premium-card" style={{ padding: '1.2rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', cursor: 'pointer', transition: 'all 0.2s', ':hover': { transform: 'translateY(-2px)' } }}>
                              <h5 style={{ color: '#fff', fontSize: '1.05rem', margin: 0 }}>{news.title}</h5>
                              <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontSize: '0.85rem' }}>
                                <span>{news.source || 'News Source'}</span>
                                <span>{news.published_date ? new Date(news.published_date).toLocaleDateString() : ''}</span>
                              </div>
                            </div>
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* TIMELINE TAB */}
              {activeTab === 'timeline' && billDetails.timeline && (
                <div className="bill-timeline-section" style={{ padding: '1rem' }}>
                  <h3 className="pane-title" style={{ marginBottom: '2rem', color: '#f8fafc' }}>⏱️ Legislative Journey</h3>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', position: 'relative' }}>
                    {/* Vertical line */}
                    <div style={{ position: 'absolute', left: '15px', top: '10px', bottom: '10px', width: '2px', background: 'rgba(139, 92, 246, 0.3)' }}></div>
                    
                    {billDetails.timeline.events && billDetails.timeline.events.length > 0 ? (
                      billDetails.timeline.events.map((evt, idx) => {
                        // Format date safely — the pipeline uses mixed formats
                        let displayDate = evt.date || 'Unknown Date';
                        try {
                          const parsed = new Date(evt.date);
                          if (!isNaN(parsed.getTime())) {
                            displayDate = parsed.toLocaleDateString('en-IN', { year: 'numeric', month: 'long', day: 'numeric' });
                          }
                        } catch(e) { /* keep raw string */ }

                        // Event type badge color
                        const typeColors = { introduced: '#8b5cf6', passed: '#10b981', news_reaction: '#3b82f6', assent: '#f59e0b', controversy: '#ef4444' };
                        const eventType = evt.event || evt.event_type || 'update';
                        const dotColor = typeColors[eventType] || '#8b5cf6';

                        return (
                          <div key={idx} style={{ display: 'flex', gap: '1.5rem', position: 'relative', zIndex: 1 }}>
                            <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: dotColor, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, border: '4px solid #0f111a' }}>
                              <span style={{ color: 'white', fontSize: '0.8rem' }}>•</span>
                            </div>
                            <div className="premium-card" style={{ padding: '1rem', flex: 1 }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                                <span style={{ color: '#a78bfa', fontSize: '0.85rem', fontWeight: 'bold' }}>{displayDate}</span>
                                <span style={{ background: `${dotColor}22`, color: dotColor, padding: '0.15rem 0.6rem', borderRadius: '50px', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', border: `1px solid ${dotColor}44` }}>
                                  {eventType.replace('_', ' ')}
                                </span>
                              </div>
                              <h4 style={{ color: 'white', marginBottom: '0.5rem', fontSize: '1.05rem' }}>{evt.title || 'Update'}</h4>
                              {evt.source && <span style={{ color: '#64748b', fontSize: '0.8rem' }}>Source: {evt.source}</span>}
                              {evt.notes && <p style={{ color: '#94a3b8', fontSize: '0.9rem', margin: '0.5rem 0 0 0', lineHeight: 1.5 }}>{evt.notes}</p>}
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <div className="empty-state">No timeline events found.</div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </>
        )}

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
          {billDetails && billDetails.prs_url && (
            <a 
              href={billDetails.prs_url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="btn btn-primary"
            >
              View on PRS India ↗
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
