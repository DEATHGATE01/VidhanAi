import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { getUserFavorites } from '../services/api';
import BillCard from '../components/BillCard';
import BillDetailsModal from '../components/BillDetailsModal';

export default function Favorites() {
  const { user } = useAuth();
  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedBillId, setSelectedBillId] = useState(null);

  useEffect(() => {
    if (user) {
      fetchFavorites();
    } else {
      setLoading(false);
    }
  }, [user]);

  const fetchFavorites = async () => {
    try {
      setLoading(true);
      const response = await getUserFavorites(user.id);
      if (response.success) {
        setFavorites(response.favorites || []);
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

  if (!user) {
    return (
      <div className="container">
        <div className="search-section">
          <h1 className="search-title">⭐ My Favorites</h1>
          <p className="search-subtitle">
            Please login to view your favorite bills
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="search-section">
        <h1 className="search-title">⭐ My Favorites</h1>
        <p className="search-subtitle">
          Bills you've bookmarked for quick access
        </p>
      </div>

      {loading && (
        <div className="loading">
          <div className="spinner"></div>
          <p>Loading favorites...</p>
        </div>
      )}

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {!loading && !error && favorites.length > 0 && (
        <div className="results-section">
          <h2 className="results-header">
            {favorites.length} Favorite Bill{favorites.length !== 1 ? 's' : ''}
          </h2>
          <div className="bills-grid">
            {favorites.map((fav) => (
              <BillCard
                key={fav.bill.id}
                bill={fav.bill}
                onViewDetails={handleViewDetails}
              />
            ))}
          </div>
        </div>
      )}

      {!loading && !error && favorites.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">⭐</div>
          <p className="empty-state-text">
            No favorites yet. Start adding bills to your favorites from search results!
          </p>
        </div>
      )}

      {selectedBillId && (
        <BillDetailsModal 
          billId={selectedBillId} 
          onClose={handleCloseModal}
        />
      )}
    </div>
  );
}
