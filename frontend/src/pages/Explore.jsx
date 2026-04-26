import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import SearchBar from '../components/SearchBar';
import BillCard from '../components/BillCard';
import BillDetailsModal from '../components/BillDetailsModal';
import AdvancedFilters from '../components/AdvancedFilters';
import { searchBills, addFavorite } from '../services/api';

export default function Explore() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get('q') || '';
  
  const [bills, setBills] = useState([]);
  const [filteredBills, setFilteredBills] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchKeyword, setSearchKeyword] = useState(initialQuery);
  const [selectedBillId, setSelectedBillId] = useState(null);
  const [activeFilters, setActiveFilters] = useState({});

  useEffect(() => {
    if (initialQuery) {
      handleSearch(initialQuery);
    } else {
      // Load all by default
      fetchAllBills();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchAllBills = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/bills?per_page=20');
      const data = await response.json();
      if (data.success) {
        setBills(data.bills);
        setFilteredBills(data.bills);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (keyword) => {
    setLoading(true);
    setError(null);
    setSearchKeyword(keyword);
    setSearchParams({ q: keyword });
    
    if (!keyword.trim()) {
      fetchAllBills();
      return;
    }

    try {
      const response = await searchBills(keyword, user?.id);
      if (response.success) {
        const results = response.results || [];
        setBills(results);
        applyFilters(results, activeFilters);
      } else {
        setError('Failed to fetch bills');
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'An error occurred while searching');
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = (billsToFilter, filters) => {
    let filtered = [...billsToFilter];
    if (filters.ministry) {
      filtered = filtered.filter(bill => bill.ministry && bill.ministry.toLowerCase().includes(filters.ministry.toLowerCase()));
    }
    if (filters.status) {
      filtered = filtered.filter(bill => bill.status && bill.status.toLowerCase().includes(filters.status.toLowerCase()));
    }
    setFilteredBills(filtered);
  };

  const handleFilterChange = (filters) => {
    setActiveFilters(filters);
    applyFilters(bills, filters);
  };

  return (
    <div className="container">
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ color: 'white', marginBottom: '1.5rem', fontSize: '2.5rem' }}>Explore Legislation</h1>
        <SearchBar onSearch={handleSearch} loading={loading} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 3fr', gap: '2rem' }}>
        {/* Left Sidebar - Filters */}
        <div>
          <AdvancedFilters onFilterChange={handleFilterChange} loading={loading} />
        </div>

        {/* Right Content - Results */}
        <div>
          {loading && (
            <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
              <div className="spinner"></div>
              <p>Searching databases...</p>
            </div>
          )}

          {error && (
            <div className="error-message">
              <strong>Error:</strong> {error}
            </div>
          )}

          {!loading && !error && (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', color: '#cbd5e1' }}>
                <span style={{ fontSize: '1.1rem' }}>
                  {filteredBills.length} results found {searchKeyword && `for "${searchKeyword}"`}
                </span>
              </div>
              
              <div className="showcase-bills-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
                {filteredBills.map((bill) => (
                  <BillCard
                    key={bill.id}
                    bill={bill}
                    onViewDetails={() => setSelectedBillId(bill.id)}
                    onAddFavorite={() => {}}
                  />
                ))}
              </div>
              
              {filteredBills.length === 0 && (
                <div className="premium-card" style={{ textAlign: 'center', padding: '4rem' }}>
                  <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.5 }}>🔍</div>
                  <h3 style={{ color: 'white', marginBottom: '0.5rem' }}>No bills found</h3>
                  <p style={{ color: '#94a3b8' }}>Try adjusting your search terms or filters.</p>
                </div>
              )}
            </>
          )}
        </div>
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
