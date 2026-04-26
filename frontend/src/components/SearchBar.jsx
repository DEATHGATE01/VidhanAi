import { useState } from 'react';

export default function SearchBar({ onSearch, loading }) {
  const [keyword, setKeyword] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (keyword.trim()) {
      onSearch(keyword.trim());
    }
  };

  return (
    <div className="search-section">
      <h1 className="search-title">🔍 Smart Legal Research Platform</h1>
      <p className="search-subtitle">
        Search Indian Parliamentary Bills • Real-time Data from PRS India
      </p>
      
      <form onSubmit={handleSubmit} className="search-box">
        <input
          type="text"
          className="search-input"
          placeholder="Search for bills (e.g., 'agriculture', 'education', 'finance')..."
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          disabled={loading}
        />
        <button 
          type="submit" 
          className="search-button"
          disabled={loading || !keyword.trim()}
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>
    </div>
  );
}
