import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { Search, X, ExternalLink, FileText, Scale, ChevronLeft, ChevronRight } from 'lucide-react'
import { getActs, getLifecycleStats } from '../services/api'

export default function ActsPage() {
  const [acts, setActs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [yearFilter, setYearFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [lifecycleStats, setLifecycleStats] = useState(null)
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 12
  const debounceRef = useRef(null)

  // Fetch acts once on mount
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getActs({ page: 1, per_page: 100 })
      .then((response) => {
        if (!cancelled && response.success) {
          setActs(response.acts || [])
        } else if (!cancelled) {
          setError('Failed to load acts')
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err?.message || 'Failed to load acts')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  // Lifecycle stats for the strip below (CTO backlog #7). Optional enhancement:
  // if the endpoint fails the strip simply doesn't render, like the
  // per-bill lifecycle fetch on ActDetailPage.
  useEffect(() => {
    let cancelled = false
    getLifecycleStats()
      .then((data) => { if (!cancelled) setLifecycleStats(data) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [])

  // Debounced search input
  const handleSearchInput = (value) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setSearchKeyword(value)
      setCurrentPage(1)
    }, 300)
  }

  const handleYearChange = (value) => {
    setYearFilter(value)
    setCurrentPage(1)
  }

  const handleStatusChange = (value) => {
    setStatusFilter(value)
    setCurrentPage(1)
  }

  const clearFilters = () => {
    setSearchKeyword('')
    setYearFilter('')
    setStatusFilter('')
    setCurrentPage(1)
  }

  // Derive distinct years and statuses from data. Acts with status 'unknown'
  // are excluded from the filter: PRS does not publish a status for these
  // rows, so an "All Statuses / unknown" dropdown would offer exactly one
  // meaningless value (CTO handoff defect 2). The filter renders only when
  // more than one real status exists.
  const years = [...new Set(acts.map((a) => a.year).filter(Boolean))].sort((a, b) => b - a)
  const statuses = [...new Set(acts.map((a) => a.status).filter((s) => s && s !== 'unknown'))].sort()

  // Human labels and colors for the machine codes the API stores
  // ('in_force' -> 'In force'). Same mapping as ActDetailPage: a badge that
  // reads "in_force" in a neutral grey teaches a reviewer to distrust the
  // table, and the Act detail page already renders these as words.
  const STATUS_LABELS = { in_force: 'In force', repealed: 'Repealed', spent: 'Spent', unknown: 'Unknown' }
  const statusLabel = (s) => STATUS_LABELS[(s || '').toLowerCase()] || s
  const statusBadgeClass = (s) => {
    const v = (s || '').toLowerCase()
    if (v === 'active' || v === 'in_force') return 'badge-emerald'
    if (v === 'repealed' || v === 'withdrawn' || v === 'lapsed') return 'badge-rose'
    return 'badge-slate'
  }

  // Client-side filtering
  const kw = searchKeyword.trim().toLowerCase()
  const filtered = acts
    .filter((a) => !kw || a.title?.toLowerCase().includes(kw) || a.act_id?.toLowerCase().includes(kw))
    .filter((a) => !yearFilter || String(a.year) === String(yearFilter))
    .filter((a) => !statusFilter || a.status === statusFilter)

  // Pagination
  const totalPages = Math.ceil(filtered.length / itemsPerPage) || 1
  const page = Math.min(currentPage, totalPages)
  const paginated = filtered.slice((page - 1) * itemsPerPage, page * itemsPerPage)

  return (
    <div className="container animate-fade-in" style={{ padding: '2rem 1rem' }}>
      {/* Header */}
      <header style={{ marginBottom: '1.5rem' }}>
        <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
          <Scale size={28} style={{ color: 'var(--accent)' }} />
          Acts
        </h1>
        <p className="page-sub">
          The law itself — tracked as first-class objects and linked to the Bills they came from. Source: PRS Legislative Research.
        </p>
      </header>

      {/* Lifecycle stats strip (CTO backlog #7). Numbers in the project's mono
          font; monospace numbers are a standing project convention for data. */}
      {lifecycleStats && lifecycleStats.success && (
        <section
          className="glass-panel"
          style={{ borderRadius: 16, padding: '1rem 1.25rem', marginBottom: '1.25rem', border: '1px solid var(--border)' }}
          aria-label="Bill to Act lifecycle statistics"
        >
          <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-3)', marginBottom: '0.2rem' }}>Bill→Act links</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.15rem', fontWeight: 600, color: 'var(--text-1)' }}>
                {lifecycleStats.total_links ?? 0}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-3)', marginBottom: '0.2rem' }}>Verified</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.15rem', fontWeight: 600, color: 'var(--ok)' }}>
                {lifecycleStats.total_verified ?? 0}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-3)', marginBottom: '0.2rem' }}>Unverified (labelled on the Act page)</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.15rem', fontWeight: 600, color: 'var(--text-2)' }}>
                {(lifecycleStats.total_links ?? 0) - (lifecycleStats.total_verified ?? 0)}
              </div>
            </div>
            <div style={{ flex: 1, minWidth: 260 }}>
              <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-3)', marginBottom: '0.3rem' }}>Verified links by year</div>
              <div style={{ display: 'flex', gap: '0.9rem', flexWrap: 'wrap' }}>
                {(lifecycleStats.by_year || []).map((y) => (
                  <span key={y.year} style={{ fontSize: '0.82rem', color: 'var(--text-2)' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-1)' }}>{y.year}</span>
                    {' '}<span style={{ fontFamily: 'var(--font-mono)', color: 'var(--ok)' }}>{y.verified_links}</span>
                    <span style={{ color: 'var(--text-3)' }}>/{y.links}</span>
                  </span>
                ))}
              </div>
            </div>
          </div>
          <p style={{ margin: '0.6rem 0 0', fontSize: '0.75rem', color: 'var(--text-3)' }}>
            How many bills have been confirmed as enacted into each Act (verified) vs. candidate matches awaiting confirmation. Source: this system's own verified/candidate links.
          </p>
        </section>
      )}

      {/* Filter bar */}
      <section className="glass-panel" style={{ borderRadius: 16, padding: '1.25rem', marginBottom: '1.25rem' }} aria-label="Search and filter acts">
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          {/* Search */}
          <div style={{ flex: 1, minWidth: 220 }}>
            <label htmlFor="acts-search" style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0,0,0,0)' }}>Search acts</label>
            <div style={{ position: 'relative' }}>
              <Search style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', size: 18, color: 'var(--text-3)' }} />
              <input
                id="acts-search"
                type="text"
                value={searchKeyword}
                onChange={(e) => handleSearchInput(e.target.value)}
                placeholder="Search acts… e.g. 'data protection', 'companies 2013'"
                className="premium-input"
                style={{ paddingLeft: '2.5rem', padding: '0.7rem 1rem 0.7rem 2.5rem', fontSize: '0.9rem' }}
                aria-label="Search acts by keyword"
              />
            </div>
          </div>

          {/* Year filter */}
          <div style={{ minWidth: 160 }}>
            <label htmlFor="acts-year" style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0,0,0,0)' }}>Filter by year</label>
            <select
              id="acts-year"
              value={yearFilter}
              onChange={(e) => handleYearChange(e.target.value)}
              className="premium-input"
              style={{ padding: '0.6rem 2.2rem 0.6rem 0.9rem', fontSize: '0.85rem', cursor: 'pointer', backgroundImage: 'none' }}
            >
              <option value="">All Years</option>
              {years.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>

          {/* Status filter — only when more than one real status exists */}
          {statuses.length > 1 && (
            <div style={{ minWidth: 160 }}>
              <label htmlFor="acts-status" style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0,0,0,0)' }}>Filter by status</label>
              <select
                id="acts-status"
                value={statusFilter}
                onChange={(e) => handleStatusChange(e.target.value)}
                className="premium-input"
                style={{ padding: '0.6rem 2.2rem 0.6rem 0.9rem', fontSize: '0.85rem', cursor: 'pointer', backgroundImage: 'none' }}
              >
                <option value="">All Statuses</option>
                {statuses.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          )}

          {/* Clear filters */}
          {(searchKeyword || yearFilter || statusFilter) && (
            <button
              type="button"
              onClick={clearFilters}
              className="btn btn-secondary"
              style={{ padding: '0.5rem 1rem', fontSize: '0.82rem', whiteSpace: 'nowrap', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
            >
              <X size={14} /> Clear
            </button>
          )}
        </div>
      </section>

      {/* Results count */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <span style={{ color: 'var(--text-2)', fontSize: '0.85rem' }}>
          <strong>{filtered.length}</strong> act{filtered.length === 1 ? '' : 's'}{searchKeyword || yearFilter || statusFilter ? ` (filtered from ${acts.length})` : ''}
        </span>
      </div>

      {/* States */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '4rem' }}>
          <span className="spinner-ring" style={{ width: 32, height: 32, borderWidth: 3 }} />
          <p className="empty-state-text" style={{ marginTop: '1rem' }}>Loading acts…</p>
        </div>
      )}

      {!loading && error && (
        <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center', borderRadius: 16 }}>
          <p style={{ color: 'var(--danger)', margin: 0 }}>⚠️ {error}</p>
          <p className="empty-state-text" style={{ marginTop: '0.5rem' }}>Is the backend running on :5000?</p>
        </div>
      )}

      {!loading && !error && filtered.length === 0 && (
        <div className="empty-state" style={{ padding: '4rem 1rem' }}>
          <FileText size={64} style={{ margin: '0 auto 1rem', color: 'var(--text-3)' }} />
          <p className="empty-state-text">No acts match your criteria.</p>
          <button type="button" onClick={clearFilters} className="btn btn-secondary" style={{ marginTop: '0.85rem' }}>
            Clear All Filters
          </button>
        </div>
      )}

      {/* Results table */}
      {!loading && !error && filtered.length > 0 && (
        <>
          <div className="card card-hover" style={{ overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-strong)' }}>
                  <th style={{ textAlign: 'left', padding: '0.85rem 1rem', fontWeight: 600, color: 'var(--text-2)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Title</th>
                  <th style={{ textAlign: 'center', padding: '0.85rem 1rem', fontWeight: 600, color: 'var(--text-2)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', width: '100px' }}>Year</th>
                  <th style={{ textAlign: 'center', padding: '0.85rem 1rem', fontWeight: 600, color: 'var(--text-2)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', width: '130px' }}>Act No.</th>
                  <th style={{ textAlign: 'center', padding: '0.85rem 1rem', fontWeight: 600, color: 'var(--text-2)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', width: '120px' }}>Status</th>
                  <th style={{ textAlign: 'center', padding: '0.85rem 1rem', fontWeight: 600, color: 'var(--text-2)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', width: '80px' }}>Bills</th>
                  <th style={{ textAlign: 'center', padding: '0.85rem 1rem', fontWeight: 600, color: 'var(--text-2)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', width: '60px' }}>PDF</th>
                </tr>
              </thead>
              <tbody>
                {paginated.map((act) => (
                  <tr key={act.act_id} style={{ borderBottom: '1px solid var(--border)', transition: 'background 0.15s' }}>
                    <td style={{ padding: '0.85rem 1rem', verticalAlign: 'middle' }}>
                      <Link
                        to={`/acts/${act.act_id}`}
                        style={{
                          fontWeight: 500,
                          color: 'var(--text-1)',
                          textDecoration: 'none',
                          display: 'block',
                        }}
                        onMouseOver={(e) => (e.target.style.color = 'var(--accent)')}
                        onMouseOut={(e) => (e.target.style.color = 'var(--text-1)')}
                      >
                        {act.title || act.short_title || act.act_id}
                      </Link>
                      {act.short_title && act.short_title !== act.title && (
                        <div style={{ fontSize: '0.78rem', color: 'var(--text-3)', marginTop: '0.15rem' }}>
                          {act.short_title}
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '0.85rem 1rem', textAlign: 'center', verticalAlign: 'middle', fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: 'var(--text-2)' }}>
                      {act.year || '—'}
                    </td>
                    <td style={{ padding: '0.85rem 1rem', textAlign: 'center', verticalAlign: 'middle', fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: 'var(--text-2)' }}>
                      {act.act_number || '—'}
                    </td>
                    <td style={{ padding: '0.85rem 1rem', textAlign: 'center', verticalAlign: 'middle' }}>
                      {act.status && act.status !== 'unknown' ? (
                        <span className={`badge ${statusBadgeClass(act.status)}`}>
                          {statusLabel(act.status)}
                        </span>
                      ) : (
                        <span
                          style={{ color: 'var(--text-3)', fontStyle: 'italic', fontSize: '0.8rem' }}
                          title="No source reachable so far publishes an in-force status for this Act — see the Act's detail page for the search trail"
                        >
                          Not published
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '0.85rem 1rem', textAlign: 'center', verticalAlign: 'middle' }}>
                      <span className="badge badge-vidhan" style={{ fontSize: '0.7rem' }}>
                        {act.linked_bill_count || 0} bill{ (act.linked_bill_count || 0) === 1 ? '' : 's' }
                      </span>
                    </td>
                    <td style={{ padding: '0.85rem 1rem', textAlign: 'center', verticalAlign: 'middle' }}>
                      {act.pdf_url && (
                        <a
                          href={act.pdf_url}
                          target="_blank"
                          rel="noreferrer"
                          style={{ color: 'var(--accent)', fontSize: '1.1rem', transition: 'color 0.15s' }}
                          onMouseOver={(e) => (e.target.style.color = 'var(--accent-hover)')}
                          onMouseOut={(e) => (e.target.style.color = 'var(--accent)')}
                          title="Open Act PDF"
                        >
                          <ExternalLink size={18} />
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <nav style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem', marginTop: '1.75rem' }} aria-label="Pagination">
              <button
                type="button"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn btn-secondary"
                aria-label="Previous page"
                style={{ padding: '0.4rem 0.7rem' }}
              >
                <ChevronLeft size={16} />
              </button>
              <span style={{ color: 'var(--text-2)', fontSize: '0.85rem', padding: '0 0.5rem' }}>Page {page} of {totalPages}</span>
              <button
                type="button"
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="btn btn-secondary"
                aria-label="Next page"
                style={{ padding: '0.4rem 0.7rem' }}
              >
                <ChevronRight size={16} />
              </button>
            </nav>
          )}
        </>
      )}
    </div>
  )
}