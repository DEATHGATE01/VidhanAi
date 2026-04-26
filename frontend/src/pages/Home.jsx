import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import SearchBar from '../components/SearchBar';
import BillCard from '../components/BillCard';
import BillDetailsModal from '../components/BillDetailsModal';
import { searchBills, addFavorite } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function Home() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [trendingBills, setTrendingBills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedBillId, setSelectedBillId] = useState(null);

  useEffect(() => {
    // Fetch some generic latest bills for trending
    const fetchTrending = async () => {
      try {
        const response = await fetch('/api/bills?per_page=6');
        const data = await response.json();
        if (data.success) {
          setTrendingBills(data.bills);
        }
      } catch (err) {
        console.error('Failed to fetch trending bills', err);
      } finally {
        setLoading(false);
      }
    };
    fetchTrending();
  }, []);

  const handleSearch = (keyword) => {
    // Redirect to Explore page with query parameter
    navigate(`/explore?q=${encodeURIComponent(keyword)}`);
  };

  const handleViewDetails = (bill) => {
    setSelectedBillId(bill.id);
  };

  return (
    <div>
      {/* Hero Section */}
      <div style={{ textAlign: 'center', padding: '6rem 20px', background: 'radial-gradient(circle at top, rgba(139, 92, 246, 0.15) 0%, transparent 70%)' }}>
        <div className="badge badge-purple" style={{ marginBottom: '1.5rem' }}>VIDHAN.AI INTELLIGENCE HUB</div>
        <h1 style={{ fontSize: '4rem', fontWeight: 800, marginBottom: '1.5rem', lineHeight: 1.1 }}>
          Track Indian Legislation<br/>
          <span className="text-gradient">Powered by Generative AI</span>
        </h1>
        <p style={{ color: '#94a3b8', fontSize: '1.25rem', maxWidth: '700px', margin: '0 auto 3rem auto', lineHeight: 1.6 }}>
          We translate dense parliamentary bills into plain English. 
          Search naturally, track ministries, and get instant sentiment analysis.
        </p>

        <div style={{ maxWidth: '800px', margin: '0 auto' }}>
          <SearchBar onSearch={handleSearch} loading={false} />
          
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', marginTop: '1.5rem', flexWrap: 'wrap' }}>
            <span style={{ color: '#64748b', fontSize: '0.9rem', display: 'flex', alignItems: 'center' }}>Popular:</span>
            {['Finance', 'Technology', 'Healthcare', 'Agriculture', 'Gaming'].map(topic => (
              <button 
                key={topic}
                onClick={() => handleSearch(topic)}
                style={{ 
                  background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', 
                  color: '#cbd5e1', padding: '0.3rem 0.8rem', borderRadius: '50px', 
                  fontSize: '0.85rem', cursor: 'pointer', transition: 'all 0.2s' 
                }}
                onMouseOver={(e) => { e.target.style.background = 'rgba(139, 92, 246, 0.2)'; e.target.style.borderColor = 'rgba(139, 92, 246, 0.4)'; }}
                onMouseOut={(e) => { e.target.style.background = 'rgba(255,255,255,0.05)'; e.target.style.borderColor = 'rgba(255,255,255,0.1)'; }}
              >
                {topic}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Trending Section */}
      <div className="container" style={{ paddingBottom: '6rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
          <h2 style={{ fontSize: '1.8rem', color: '#f8fafc' }}>Trending Legislation</h2>
          <button className="btn btn-secondary" onClick={() => navigate('/explore')}>View All →</button>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
            <div className="spinner"></div>
          </div>
        ) : (
          <div className="showcase-bills-grid">
            {trendingBills.map((bill) => (
              <BillCard
                key={bill.id}
                bill={bill}
                onViewDetails={handleViewDetails}
                onAddFavorite={() => {}}
              />
            ))}
          </div>
        )}
      </div>

      {selectedBillId && (
        <BillDetailsModal 
          billId={selectedBillId} 
          onClose={() => setSelectedBillId(null)}
          onBillUpdate={() => {}}
        />
      )}
    </div>
  );
}
