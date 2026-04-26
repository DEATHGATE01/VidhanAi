import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { getUserHistory } from '../services/api';
import BillCard from '../components/BillCard';
import BillDetailsModal from '../components/BillDetailsModal';

export default function History() {
  const { user } = useAuth();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedBillId, setSelectedBillId] = useState(null);

  useEffect(() => {
    if (user) {
      fetchHistory();
    } else {
      setLoading(false);
    }
  }, [user]);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const response = await getUserHistory(user.id);
      if (response.success) {
        setHistory(response.history || []);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetails = (bill) => {
    setSelectedBillId(bill.id);
  };

  const handleCloseModal = () => {
    setSelectedBillId(null);
  };

  const formatDateTime = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (!user) {
    return (
      <div className="container">
        <div className="search-section">
          <h1 className="search-title">📚 Reading History</h1>
          <p className="search-subtitle">
            Please login to view your reading history
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="search-section">
        <h1 className="search-title">📚 Reading History</h1>
        <p className="search-subtitle">
          Bills you've recently viewed
        </p>
      </div>

      {loading && (
        <div className="loading">
          <div className="spinner"></div>
          <p>Loading history...</p>
        </div>
      )}

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {!loading && !error && history.length > 0 && (
        <div className="results-section">
          <h2 className="results-header">
            {history.length} Bill{history.length !== 1 ? 's' : ''} in History
          </h2>
          <div className="history-list">
            {history.map((item) => (
              <div key={item.id} className="history-item">
                <div className="history-meta">
                  <span className="history-time">
                    📅 {formatDateTime(item.timestamp)}
                  </span>
                  <span className="history-source">
                    via {item.source}
                  </span>
                </div>
                <BillCard
                  bill={item.bill}
                  onViewDetails={handleViewDetails}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {!loading && !error && history.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">📚</div>
          <p className="empty-state-text">
            No reading history yet. Start exploring bills to build your history!
          </p>
        </div>
      )}

      {selectedBillId && (
        <BillDetailsModal 
          billId={selectedBillId} 
          onClose={handleCloseModal}
        />
      )}

      <style jsx>{`
        .history-list {
          display: flex;
          flex-direction: column;
          gap: 2rem;
        }

        .history-item {
          background: white;
          border-radius: 15px;
          padding: 1.5rem;
          box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
        }

        .history-meta {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
          padding-bottom: 1rem;
          border-bottom: 2px solid #f0f0f0;
        }

        .history-time {
          color: #666;
          font-size: 0.9rem;
        }

        .history-source {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 0.25rem 0.75rem;
          border-radius: 20px;
          font-size: 0.85rem;
        }
      `}</style>
    </div>
  );
}
