import { useState } from 'react';

export default function BillCard({ bill, onViewDetails, onAddFavorite }) {
  const [isFavorite, setIsFavorite] = useState(false);

  const handleFavoriteClick = async () => {
    setIsFavorite(!isFavorite);
    if (onAddFavorite) {
      await onAddFavorite(bill.id);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric' 
    });
  };

  return (
    <div className="bill-card" onClick={() => onViewDetails && onViewDetails(bill)}>
      <h3 className="bill-title">{bill.title || 'Untitled Bill'}</h3>
      
      <div className="bill-meta">
        {bill.ministry && (
          <span className="bill-tag ministry">
            🏛️ {bill.ministry}
          </span>
        )}
        {bill.status && (
          <span className="bill-tag status">
            📋 {bill.status}
          </span>
        )}
        {bill.bill_type && (
          <span className="bill-tag">
            📄 {bill.bill_type}
          </span>
        )}
      </div>

      {bill.introduction_date && (
        <p className="bill-description">
          <strong>Introduced:</strong> {formatDate(bill.introduction_date)}
        </p>
      )}

      <div className="bill-footer">
        <span className="bill-date">
          {bill.session || 'Session info not available'}
        </span>
        <div className="bill-actions" onClick={(e) => e.stopPropagation()}>
          <button 
            className={`btn ${isFavorite ? 'btn-primary' : 'btn-secondary'}`}
            onClick={handleFavoriteClick}
            title={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
          >
            {isFavorite ? '⭐' : '☆'}
          </button>
        </div>
      </div>
    </div>
  );
}
