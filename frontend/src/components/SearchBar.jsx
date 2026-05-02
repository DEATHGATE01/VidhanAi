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
      <h1 className="search-title">
        <span className="emoji-icon">🔍</span>
        <span className="text-gradient">Smart Legal Research</span>
      </h1>
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
          {loading ? (
            <>
              <svg className="animate-spin" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ animation: 'spin 1s linear infinite' }}>
                <circle cx="12" cy="12" r="10" strokeOpacity="0.25"></circle>
                <path d="M12 2a10 10 0 0 1 10 10"></path>
              </svg>
              <span>Searching...</span>
            </>
          ) : (
            <>
              <span>Search</span>
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="5" y1="12" x2="19" y2="12"></line>
                <polyline points="12 5 19 12 12 19"></polyline>
              </svg>
            </>
          )}
        </button>
      </form>
    </div>
  );
}
