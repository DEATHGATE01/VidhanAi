import { useState, useEffect } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, ExternalLink, FileText, Scale, CheckCircle, AlertCircle, Info, ChevronDown, ChevronUp } from 'lucide-react'
import { getActById, getBillLifecycle } from '../services/api'
import LifecycleTimeline from '../components/LifecycleTimeline'

export default function ActDetailPage() {
  const { actId } = useParams()
  const [act, setAct] = useState(null)
  const [billLifecycles, setBillLifecycles] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expandedBills, setExpandedBills] = useState(new Set())

  // Fetch act on mount
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    getActById(actId)
      .then((response) => {
        if (!cancelled) {
          if (response.success && response.act) {
            setAct(response.act)
            // Fetch lifecycle for each linked bill
            const bills = response.act.bills || []
            bills.forEach((bill) => {
              if (bill.id) {
                getBillLifecycle(bill.id)
                  .then((lifeRes) => {
                    if (!cancelled && lifeRes.success) {
                      setBillLifecycles((prev) => ({
                        ...prev,
                        [bill.id]: lifeRes.events || [],
                      }))
                    }
                  })
                  .catch(() => {
                    // Silently fail - lifecycle is optional enhancement
                  })
              }
            })
          } else {
            setError('Act not found')
          }
        }
      })
      .catch((err) => {
        if (!cancelled) {
          if (err?.response?.status === 404) {
            setError('Act not found')
          } else {
            setError(err?.message || 'Failed to load act')
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [actId])

  const toggleBillExpand = (billId) => {
    setExpandedBills((prev) => {
      const next = new Set(prev)
      if (next.has(billId)) next.delete(billId)
      else next.add(billId)
      return next
    })
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return '—'
    try {
      return new Date(dateStr).toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    } catch {
      return dateStr
    }
  }

  const getStatusBadgeClass = (status) => {
    if (!status) return 'badge-slate'
    const s = status.toLowerCase()
    if (s === 'active' || s === 'passed' || s === 'assented') return 'badge-emerald'
    if (s === 'repealed' || s === 'withdrawn' || s === 'lapsed') return 'badge-rose'
    if (s === 'pending' || s === 'introduced' || s === 'referred') return 'badge-amber'
    return 'badge-slate'
  }

  if (loading) {
    return (
      <div className="container animate-fade-in" style={{ padding: '2rem 1rem' }}>
        <div style={{ textAlign: 'center', padding: '4rem' }}>
          <span className="spinner-ring" style={{ width: 32, height: 32, borderWidth: 3 }} />
          <p className="empty-state-text" style={{ marginTop: '1rem' }}>Loading act…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container animate-fade-in" style={{ padding: '2rem 1rem' }}>
        <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center', borderRadius: 16, maxWidth: 600, margin: '0 auto' }}>
          {error === 'Act not found' ? (
            <>
              <AlertCircle size={48} style={{ margin: '0 auto 1rem', color: 'var(--warn)' }} />
              <h2 style={{ margin: '0 0 0.5rem', fontSize: '1.3rem' }}>Act Not Found</h2>
              <p className="empty-state-text" style={{ marginBottom: '1.5rem' }}>
                No act exists with the ID <code style={{ fontFamily: 'var(--font-mono)', background: 'var(--hover)', padding: '0.1rem 0.4rem', borderRadius: 4 }}>{actId}</code>
              </p>
            </>
          ) : (
            <>
              <AlertCircle size={48} style={{ margin: '0 auto 1rem', color: 'var(--danger)' }} />
              <h2 style={{ margin: '0 0 0.5rem', fontSize: '1.3rem' }}>Failed to Load Act</h2>
              <p style={{ color: 'var(--danger)', margin: '0 0 0.5rem' }}>⚠️ {error}</p>
              <p className="empty-state-text" style={{ marginBottom: '1.5rem' }}>Is the backend running on :5000?</p>
            </>
          )}
          <Link to="/acts" className="btn btn-primary" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
            <ArrowLeft size={16} /> Back to Acts
          </Link>
        </div>
      </div>
    )
  }

  if (!act) {
    return null
  }

  return (
    <div className="container animate-fade-in" style={{ padding: '2rem 1rem', maxWidth: '1000px' }}>
      {/* Back link */}
      <Link
        to="/acts"
        className="btn btn-ghost"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.4rem',
          marginBottom: '1.5rem',
          fontSize: '0.85rem',
          padding: '0.4rem 0.8rem',
        }}
      >
        <ArrowLeft size={16} /> Back to Acts
      </Link>

      {/* Act Header */}
      <div className="card card-hover" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'flex-start', marginBottom: '1rem' }}>
          <div style={{ flex: 1, minWidth: 280 }}>
            <h1 className="page-title" style={{ margin: '0 0 0.5rem', lineHeight: 1.3 }}>
              {act.title || act.short_title || act.act_id}
            </h1>
            {act.short_title && act.short_title !== act.title && (
              <p style={{ color: 'var(--text-2)', fontSize: '0.95rem', margin: 0 }}>
                {act.short_title}
              </p>
            )}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
            <Scale size={24} style={{ color: 'var(--accent)' }} />
            <span className="badge badge-vidhan" style={{ fontSize: '0.75rem' }}>
              {act.act_id}
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem', fontSize: '0.88rem', color: 'var(--text-2)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ color: 'var(--text-3)' }}>Year:</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 500, color: 'var(--text-1)' }}>
              {act.year || '—'}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ color: 'var(--text-3)' }}>Act No.:</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 500, color: 'var(--text-1)' }}>
              {act.act_number || '—'}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ color: 'var(--text-3)' }}>Status:</span>
            <span className={getStatusBadgeClass(act.status)}>
              {act.status || 'unknown'}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ color: 'var(--text-3)' }}>Assented:</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 500, color: 'var(--text-1)' }}>
              {formatDate(act.assent_date)}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ color: 'var(--text-3)' }}>Commenced:</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 500, color: 'var(--text-1)' }}>
              {formatDate(act.commencement_date)}
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '1rem' }}>
          {act.pdf_url && (
            <a
              href={act.pdf_url}
              target="_blank"
              rel="noreferrer"
              className="btn btn-secondary"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.82rem' }}
            >
              <FileText size={16} /> Act PDF
            </a>
          )}
          {act.source_url && (
            <a
              href={act.source_url}
              target="_blank"
              rel="noreferrer"
              className="btn btn-ghost"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.82rem' }}
            >
              <ExternalLink size={16} /> Source (PRS)
            </a>
          )}
        </div>
      </div>

      {/* Bills this came from */}
      {act.bills && act.bills.length > 0 && (
        <section style={{ marginBottom: '2rem' }}>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 700, margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Scale size={20} style={{ color: 'var(--accent)' }} />
            Bills This Came From ({act.bills.length})
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {act.bills.map((bill) => {
              const lifecycleEvents = billLifecycles[bill.id] || []
              const isExpanded = expandedBills.has(bill.id)
              const hasLifecycle = lifecycleEvents.length > 0

              return (
                <div key={bill.id} className="card card-hover" style={{ overflow: 'hidden' }}>
                  {/* Bill header - always visible */}
                  <div
                    style={{
                      padding: '1rem 1.25rem',
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: '1rem',
                      alignItems: 'center',
                      cursor: hasLifecycle ? 'pointer' : 'default',
                      borderBottom: hasLifecycle ? '1px solid var(--border)' : 'none',
                    }}
                    onClick={() => hasLifecycle && toggleBillExpand(bill.id)}
                  >
                    <div style={{ flex: 1, minWidth: 240 }}>
                      <div style={{ fontWeight: 500, color: 'var(--text-1)', marginBottom: '0.2rem' }}>
                        {bill.title}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-3)' }}>
                        Bill ID: <span style={{ fontFamily: 'var(--font-mono)' }}>{bill.bill_id}</span>
                      </div>
                    </div>

                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', alignItems: 'center' }}>
                      <span className={`badge ${getStatusBadgeClass(bill.status)}`}>
                        {bill.status || 'unknown'}
                      </span>
                      <span className="badge badge-slate" style={{ fontSize: '0.65rem' }}>
                        {bill.link_type || 'linked'}
                      </span>
                      {bill.verified && (
                        <span
                          className="badge badge-emerald"
                          style={{ fontSize: '0.65rem', display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}
                          title="Verified match"
                        >
                          <CheckCircle size={10} /> Verified
                        </span>
                      )}
                      {!bill.verified && bill.match_confidence && (
                        <span
                          className="badge badge-amber"
                          style={{ fontSize: '0.65rem', display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}
                          title={`Match confidence: ${Math.round(bill.match_confidence * 100)}%`}
                        >
                          <Info size={10} /> {Math.round(bill.match_confidence * 100)}%
                        </span>
                      )}
                      {bill.url && (
                        <a
                          href={bill.url}
                          target="_blank"
                          rel="noreferrer"
                          className="btn btn-ghost"
                          style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem' }}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <ExternalLink size={14} /> Bill
                        </a>
                      )}
                      {hasLifecycle && (
                        <span
                          className="badge badge-vidhan"
                          style={{ fontSize: '0.65rem', display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}
                        >
                          {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                          {lifecycleEvents.length} event{lifecycleEvents.length === 1 ? '' : 's'}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Bill evidence - small text */}
                  {bill.evidence && (
                    <div
                      style={{
                        padding: '0 1.25rem 0.75rem',
                        fontSize: '0.72rem',
                        color: 'var(--text-3)',
                        fontFamily: 'var(--font-mono)',
                        fontStyle: 'italic',
                        borderBottom: hasLifecycle ? '1px solid var(--border)' : 'none',
                      }}
                    >
                      Evidence: {bill.evidence}
                    </div>
                  )}

                  {/* Expanded lifecycle timeline */}
                  {hasLifecycle && isExpanded && (
                    <div style={{ padding: '1rem 1.25rem', background: 'var(--surface-2)' }}>
                      <h3 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-2)', margin: '0 0 0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        Lifecycle Events (from Bill Tracker)
                      </h3>
                      <LifecycleTimeline events={lifecycleEvents} compact={true} />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* No linked bills */}
      {act.bills && act.bills.length === 0 && (
        <div className="card" style={{ padding: '2rem', textAlign: 'center' }}>
          <FileText size={48} style={{ margin: '0 auto 1rem', color: 'var(--text-3)' }} />
          <p className="empty-state-text">No bills linked to this act yet.</p>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-3)', marginTop: '0.5rem' }}>
            The act may predate the bill tracking system or the link hasn't been established.
          </p>
        </div>
      )}

      {/* Act's own lifecycle events (usually empty) */}
      {act.lifecycle_events && act.lifecycle_events.length > 0 && (
        <section>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 700, margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Info size={20} style={{ color: 'var(--accent)' }} />
            Act Lifecycle Events
          </h2>
          <LifecycleTimeline events={act.lifecycle_events} compact={false} />
        </section>
      )}
    </div>
  )
}