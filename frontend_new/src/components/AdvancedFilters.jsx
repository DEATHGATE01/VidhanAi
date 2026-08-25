// Advanced filter panel for ExplorePage. Controlled component — all state
// lives in the parent via activeFilters/onFilterChange.
const MINISTRIES = [
  'Ministry of Finance', 'Ministry of Home Affairs', 'Ministry of Law and Justice',
  'Ministry of Electronics and Information Technology', 'Ministry of Health and Family Welfare',
  'Ministry of Agriculture and Farmers Welfare', 'Ministry of Education', 'Ministry of Defence',
  'Ministry of Commerce and Industry', 'Ministry of Railways', 'Ministry of Road Transport and Highways',
  'Ministry of Civil Aviation', 'Ministry of Environment, Forest and Climate Change',
  'Ministry of Housing and Urban Affairs', 'Ministry of Rural Development',
]

const STATUSES = ['Passed', 'Draft', 'Lapsed', 'Withdrawn', 'In Committee', 'Pending', 'Referred']

const selectStyle = {
  width: '100%',
  padding: '0.6rem 0.85rem',
  background: 'rgba(8,10,18,0.7)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: 10,
  color: '#e2e8f0',
  fontFamily: 'inherit',
  fontSize: '0.85rem',
  outline: 'none',
  cursor: 'pointer',
}

const labelStyle = {
  display: 'block',
  fontSize: '0.75rem',
  fontWeight: 600,
  color: '#94a3b8',
  marginBottom: '0.35rem',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
}

export default function AdvancedFilters({ activeFilters, onFilterChange }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.85rem' }}>
      <div>
        <label htmlFor="af-ministry" style={labelStyle}>Ministry</label>
        <select
          id="af-ministry"
          value={activeFilters.ministry}
          onChange={(e) => onFilterChange('ministry', e.target.value)}
          style={selectStyle}
        >
          <option value="">All Ministries</option>
          {MINISTRIES.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="af-status" style={labelStyle}>Status</label>
        <select
          id="af-status"
          value={activeFilters.status}
          onChange={(e) => onFilterChange('status', e.target.value)}
          style={selectStyle}
        >
          <option value="">All Statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="af-from" style={labelStyle}>Introduced From</label>
        <input
          id="af-from"
          type="date"
          value={activeFilters.dateFrom}
          onChange={(e) => onFilterChange('dateFrom', e.target.value)}
          className="premium-input"
          style={{ width: '100%', padding: '0.55rem 0.7rem', fontSize: '0.82rem' }}
        />
      </div>

      <div>
        <label htmlFor="af-to" style={labelStyle}>Introduced To</label>
        <input
          id="af-to"
          type="date"
          value={activeFilters.dateTo}
          onChange={(e) => onFilterChange('dateTo', e.target.value)}
          className="premium-input"
          style={{ width: '100%', padding: '0.55rem 0.7rem', fontSize: '0.82rem' }}
        />
      </div>
    </div>
  )
}
