import { useState, useEffect, useRef } from 'react'
import { ChevronLeft, ChevronRight, Download } from 'lucide-react'
import { getAllBills } from '../services/api'
import BillCard from '../components/BillCard'
import AdvancedFilters from '../components/AdvancedFilters'
import Vid from '../components/Vid'

// Explore all bills — GET /api/bills (page 1, 100 rows) with client-side
// filtering, sorting, grid/list views, bulk select + CSV export.
export default function ExplorePage() {
  const [bills, setBills] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [activeFilters, setActiveFilters] = useState({ ministry: '', status: '', dateFrom: '', dateTo: '' })
  const [sortBy, setSortBy] = useState('relevance')
  const [viewMode, setViewMode] = useState('grid')
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 12
  const [selectedBills, setSelectedBills] = useState(new Set())
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false)
  const debounceRef = useRef(null)

  useEffect(() => {
    let cancelled = false
    getAllBills(1, 100)
      .then((response) => {
        if (!cancelled && response.success) setBills(response.bills || [])
        else if (!cancelled) setError('Failed to load bills')
      })
      .catch((err) => { if (!cancelled) setError(err?.message || 'Failed to load bills') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  // Debounced keyword lives in state; filtering is derived on render.
  const handleSearchInput = (value) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setSearchKeyword(value)
      setCurrentPage(1)
    }, 300)
  }

  const handleFilterChange = (key, value) => {
    setActiveFilters((prev) => ({ ...prev, [key]: value }))
    setCurrentPage(1)
  }

  const clearFilters = () => {
    setSearchKeyword('')
    setActiveFilters({ ministry: '', status: '', dateFrom: '', dateTo: '' })
    setSortBy('relevance')
    setCurrentPage(1)
  }

  const toggleSelectBill = (billId) => {
    setSelectedBills((prev) => {
      const next = new Set(prev)
      if (next.has(billId)) next.delete(billId)
      else next.add(billId)
      return next
    })
  }

  const exportSelected = () => {
    const selected = bills.filter((b) => selectedBills.has(b.id))
    if (selected.length === 0) return
    const csv = [
      ['Title', 'Ministry', 'Status', 'Introduction Date', 'URL'],
      ...selected.map((b) => [b.title, b.ministry || '', b.status || '', b.introduction_date || '', b.url || '']),
    ]
      .map((row) => row.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(','))
      .join('\n')

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `vidhanai-bills-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  // Derived filter/sort/pagination — no duplicated state.
  const kw = searchKeyword.trim().toLowerCase()
  const filtered = bills
    .filter((b) =>
      !kw ||
      b.title?.toLowerCase().includes(kw) ||
      b.ministry?.toLowerCase().includes(kw) ||
      b.status?.toLowerCase().includes(kw))
    .filter((b) => !activeFilters.ministry || b.ministry === activeFilters.ministry)
    .filter((b) => !activeFilters.status || b.status === activeFilters.status)
    .filter((b) => !activeFilters.dateFrom || (b.introduction_date && new Date(b.introduction_date) >= new Date(activeFilters.dateFrom)))
    .filter((b) => !activeFilters.dateTo || (b.introduction_date && new Date(b.introduction_date) <= new Date(activeFilters.dateTo)))

  const sorted = [...filtered]
  if (sortBy === 'date_desc') sorted.sort((a, b) => new Date(b.introduction_date || 0) - new Date(a.introduction_date || 0))
  else if (sortBy === 'date_asc') sorted.sort((a, b) => new Date(a.introduction_date || 0) - new Date(b.introduction_date || 0))
  else if (sortBy === 'title_asc') sorted.sort((a, b) => (a.title || '').localeCompare(b.title || ''))
  else if (sortBy === 'title_desc') sorted.sort((a, b) => (b.title || '').localeCompare(a.title || ''))

  const totalPages = Math.ceil(sorted.length / itemsPerPage) || 1
  const page = Math.min(currentPage, totalPages)
  const paginated = sorted.slice((page - 1) * itemsPerPage, page * itemsPerPage)

  return (
    <div className="container animate-fade-in" style={{ padding: '2rem 1rem' }}>
      {/* Header */}
      <header style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: 800, letterSpacing: '-0.5px', margin: 0 }}>
          📂 Explore Legislation
        </h1>
        <p style={{ color: 'var(--text-2)', fontSize: '0.85rem', margin: 0 }}>
          Browse, search, and analyze Indian parliamentary bills from PRS Legislative Research
        </p>
      </header>

      {/* Search & filters */}
      <section className="glass-panel" style={{ borderRadius: 16, padding: '1.25rem', marginBottom: '1.25rem' }} aria-label="Search and filters">
        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: showAdvancedFilters ? '1rem' : 0, flexWrap: 'wrap' }}>
          <input
            value={searchKeyword}
            onChange={(e) => handleSearchInput(e.target.value)}
            placeholder="Search bills… e.g. 'data protection', 'telecom 2023'"
            className="premium-input"
            style={{ flex: 1, minWidth: 220, padding: '0.7rem 1rem', fontSize: '0.9rem' }}
            aria-label="Search bills by keyword"
          />
          <button
            type="button"
            onClick={() => setShowAdvancedFilters((s) => !s)}
            className={showAdvancedFilters ? 'btn btn-primary' : 'btn btn-secondary'}
            style={{ padding: '0.5rem 1rem', fontSize: '0.82rem', whiteSpace: 'nowrap' }}
            aria-expanded={showAdvancedFilters}
          >
            {showAdvancedFilters ? 'Hide Filters' : 'Advanced Filters'}
          </button>
        </div>

        {showAdvancedFilters && (
          <div className="animate-fade-in">
            <AdvancedFilters activeFilters={activeFilters} onFilterChange={handleFilterChange} />
            <div style={{ display: 'flex', gap: '0.6rem', marginTop: '0.85rem' }}>
              <button type="button" onClick={clearFilters} className="btn btn-secondary" style={{ padding: '0.45rem 1rem', fontSize: '0.82rem' }}>
                Clear All
              </button>
            </div>
          </div>
        )}
      </section>

      {/* Toolbar */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center', marginBottom: '1.25rem' }}>
        <span style={{ color: 'var(--text-1)', fontSize: '0.85rem' }}>
          <strong>{sorted.length}</strong> bill{sorted.length === 1 ? '' : 's'}
          {selectedBills.size > 0 && <span style={{ color: 'var(--ok)' }}> · {selectedBills.size} selected</span>}
        </span>

        <label htmlFor="explore-sort" style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0,0,0,0)' }}>Sort bills</label>
        <select
          id="explore-sort"
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="premium-input"
          style={{ marginLeft: 'auto', padding: '0.4rem 0.7rem', fontSize: '0.82rem', cursor: 'pointer' }}
        >
          <option value="relevance">Default order</option>
          <option value="date_desc">Newest first</option>
          <option value="date_asc">Oldest first</option>
          <option value="title_asc">Title A–Z</option>
          <option value="title_desc">Title Z–A</option>
        </select>

        {selectedBills.size > 0 && (
          <button type="button" onClick={exportSelected} className="btn btn-secondary" style={{ padding: '0.4rem 0.85rem', fontSize: '0.8rem' }}>
            <Download size={14} /> Export CSV
          </button>
        )}

        <div style={{ display: 'flex', gap: '0.3rem' }} role="group" aria-label="View mode">
          <button type="button" onClick={() => setViewMode('grid')} aria-pressed={viewMode === 'grid'} title="Grid view"
            className={viewMode === 'grid' ? 'btn btn-primary' : 'btn btn-ghost'}
            style={{ padding: '0.4rem 0.7rem', fontSize: '0.8rem' }}>▦</button>
          <button type="button" onClick={() => setViewMode('list')} aria-pressed={viewMode === 'list'} title="List view"
            className={viewMode === 'list' ? 'btn btn-primary' : 'btn btn-ghost'}
            style={{ padding: '0.4rem 0.7rem', fontSize: '0.8rem' }}>☰</button>
        </div>
      </div>

      {/* States */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '4rem' }}>
          <span className="spinner-ring" style={{ width: 32, height: 32, borderWidth: 3 }} />
          <p className="empty-state-text" style={{ marginTop: '1rem' }}>Loading bills…</p>
        </div>
      )}

      {!loading && error && (
        <div className="glass-panel rounded-xl" style={{ padding: '2rem', textAlign: 'center' }}>
          <p style={{ color: 'var(--danger)', margin: 0 }}>⚠️ {error}</p>
          <p className="empty-state-text" style={{ marginTop: '0.5rem' }}>Is the backend running on :5000?</p>
        </div>
      )}

      {!loading && !error && paginated.length === 0 && (
        <div className="empty-state" style={{ padding: '4rem 1rem' }}>
          <Vid size={64} expression="curious" lively style={{ margin: '0 auto 1rem' }} />
          <p className="empty-state-text">No bills match your criteria.</p>
          <button type="button" onClick={clearFilters} className="btn btn-secondary" style={{ marginTop: '0.85rem' }}>
            Clear All Filters
          </button>
        </div>
      )}

      {/* Results */}
      {!loading && !error && paginated.length > 0 && (
        <>
          <div
            style={
              viewMode === 'grid'
                ? { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1rem' }
                : { display: 'flex', flexDirection: 'column', gap: '0.75rem', maxWidth: 900, margin: '0 auto' }
            }
          >
            {paginated.map((bill) => (
              <BillCard
                key={bill.id}
                bill={bill}
                onViewDetails={() => { if (bill.url) window.open(bill.url, '_blank', 'noopener,noreferrer') }}
                onAddFavorite={() => {}}
                isSelected={selectedBills.has(bill.id)}
                onToggleSelect={() => toggleSelectBill(bill.id)}
              />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <nav style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem', marginTop: '1.75rem' }} aria-label="Pagination">
              <button type="button" onClick={() => setCurrentPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="btn btn-secondary" aria-label="Previous page" style={{ padding: '0.4rem 0.7rem' }}>
                <ChevronLeft size={16} />
              </button>
              <span style={{ color: 'var(--text-2)', fontSize: '0.85rem', padding: '0 0.5rem' }}>Page {page} of {totalPages}</span>
              <button type="button" onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="btn btn-secondary" aria-label="Next page" style={{ padding: '0.4rem 0.7rem' }}>
                <ChevronRight size={16} />
              </button>
            </nav>
          )}
        </>
      )}
    </div>
  )
}
