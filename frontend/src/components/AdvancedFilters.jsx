import { useState } from 'react';
import './AdvancedFilters.css';

export default function AdvancedFilters({ onFilterChange, loading }) {
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    ministry: '',
    status: '',
    billType: '',
    dateFrom: '',
    dateTo: ''
  });

  const ministries = [
    'Agriculture',
    'Commerce',
    'Defence',
    'Education',
    'Environment',
    'Finance',
    'Health',
    'Home Affairs',
    'Labour',
    'Law',
    'Rural Development',
    'Urban Development'
  ];

  const statuses = [
    'Introduced',
    'Pending',
    'Passed by Lok Sabha',
    'Passed by Rajya Sabha',
    'Enacted',
    'Withdrawn',
    'Lapsed'
  ];

  const billTypes = [
    'Government Bill',
    'Private Member Bill',
    'Money Bill',
    'Constitutional Amendment Bill',
    'Ordinance'
  ];

  const handleFilterChange = (key, value) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    onFilterChange(newFilters);
  };

  const handleReset = () => {
    const resetFilters = {
      ministry: '',
      status: '',
      billType: '',
      dateFrom: '',
      dateTo: ''
    };
    setFilters(resetFilters);
    onFilterChange(resetFilters);
  };

  const activeFilterCount = Object.values(filters).filter(v => v !== '').length;

  return (
    <div className="advanced-filters">
      <button 
        className="filters-toggle"
        onClick={() => setShowFilters(!showFilters)}
        disabled={loading}
      >
        🔧 Advanced Filters
        {activeFilterCount > 0 && (
          <span className="filter-badge">{activeFilterCount}</span>
        )}
      </button>

      {showFilters && (
        <div className="filters-panel">
          <div className="filters-grid">
            <div className="filter-group">
              <label>Ministry</label>
              <select 
                value={filters.ministry}
                onChange={(e) => handleFilterChange('ministry', e.target.value)}
              >
                <option value="">All Ministries</option>
                {ministries.map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>

            <div className="filter-group">
              <label>Status</label>
              <select 
                value={filters.status}
                onChange={(e) => handleFilterChange('status', e.target.value)}
              >
                <option value="">All Statuses</option>
                {statuses.map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            <div className="filter-group">
              <label>Bill Type</label>
              <select 
                value={filters.billType}
                onChange={(e) => handleFilterChange('billType', e.target.value)}
              >
                <option value="">All Types</option>
                {billTypes.map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            <div className="filter-group">
              <label>Date From</label>
              <input 
                type="date"
                value={filters.dateFrom}
                onChange={(e) => handleFilterChange('dateFrom', e.target.value)}
              />
            </div>

            <div className="filter-group">
              <label>Date To</label>
              <input 
                type="date"
                value={filters.dateTo}
                onChange={(e) => handleFilterChange('dateTo', e.target.value)}
              />
            </div>

            <div className="filter-actions">
              <button 
                className="btn btn-secondary"
                onClick={handleReset}
              >
                Reset Filters
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
