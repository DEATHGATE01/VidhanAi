import { ExternalLink, Calendar, Building2, Clock } from 'lucide-react'

export default function LifecycleTimeline({ events, compact = false }) {
  if (!events || events.length === 0) {
    return (
      <p className="empty-state-text" style={{ margin: compact ? '0.5rem 0' : '1rem 0' }}>
        No lifecycle events recorded for this bill.
      </p>
    )
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return null
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

  const getSourceLabel = (source) => {
    if (!source) return 'Source'
    const lower = source.toLowerCase()
    if (lower.includes('prs')) return 'PRS'
    if (lower.includes('loksabha') || lower.includes('lok_sabha')) return 'Lok Sabha'
    if (lower.includes('rajyasabha') || lower.includes('rajya_sabha')) return 'Rajya Sabha'
    if (lower.includes('gazette')) return 'Gazette'
    if (lower.includes('sansad')) return 'Sansad'
    return source
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: compact ? '0.65rem' : '1rem',
        paddingLeft: compact ? '0.5rem' : '0',
      }}
    >
      {events.map((event, idx) => {
        const formattedDate = formatDate(event.event_date)
        const isUndated = !event.event_date
        const hasHouse = event.house && event.house.trim()

        return (
          <div
            key={`${event.event_type}-${event.event_date || 'undated'}-${idx}`}
            style={{
              display: 'flex',
              gap: compact ? '0.6rem' : '0.85rem',
              alignItems: 'flex-start',
              position: 'relative',
              paddingBottom: idx === events.length - 1 ? 0 : compact ? '0.5rem' : '0.75rem',
              borderLeft: `1px solid var(--border)`,
              paddingLeft: compact ? '0.85rem' : '1rem',
            }}
          >
            {/* Timeline dot + line */}
            <div
              style={{
                flex: '0 0 10px',
                position: 'relative',
                top: compact ? '2px' : '3px',
                display: 'flex',
                alignItems: 'flex-start',
              }}
            >
              <div
                style={{
                  width: '10px',
                  height: '10px',
                  borderRadius: '50%',
                  background: isUndated ? 'var(--text-3)' : 'var(--accent)',
                  border: '2px solid var(--surface)',
                  boxShadow: '0 0 0 1px var(--border)',
                  zIndex: 1,
                  opacity: isUndated ? 0.5 : 1,
                }}
              />
              {idx < events.length - 1 && (
                <div
                  style={{
                    position: 'absolute',
                    left: '4px',
                    top: '10px',
                    bottom: 0,
                    width: '1px',
                    background: 'var(--border)',
                    zIndex: 0,
                  }}
                />
              )}
            </div>

            {/* Event content */}
            <div style={{ flex: 1, minWidth: 0 }}>
              {/* Title */}
              <div
                style={{
                  fontWeight: 600,
                  fontSize: compact ? '0.85rem' : '0.9rem',
                  color: 'var(--text-1)',
                  marginBottom: compact ? '0.15rem' : '0.25rem',
                }}
              >
                {event.title || event.event_type || 'Lifecycle Event'}
              </div>

              {/* Date + House chips */}
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  alignItems: 'center',
                  gap: '0.5rem',
                  marginBottom: compact ? '0.15rem' : '0.25rem',
                }}
              >
                {formattedDate ? (
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                      fontSize: compact ? '0.75rem' : '0.8rem',
                      color: 'var(--text-2)',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    <Calendar size={12} />
                    {formattedDate}
                  </span>
                ) : (
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                      fontSize: compact ? '0.75rem' : '0.8rem',
                      color: 'var(--warn)',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    <Clock size={12} />
                    Date not on source
                  </span>
                )}

                {hasHouse && (
                  <span
                    className="badge badge-slate"
                    style={{
                      fontSize: compact ? '0.65rem' : '0.7rem',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.2rem',
                    }}
                  >
                    <Building2 size={10} />
                    {event.house}
                  </span>
                )}

                {event.is_estimated && (
                  <span
                    className="badge badge-amber"
                    style={{
                      fontSize: compact ? '0.6rem' : '0.65rem',
                      textTransform: 'uppercase',
                      letterSpacing: '0.02em',
                    }}
                  >
                    Estimated
                  </span>
                )}
              </div>

              {/* Source link + Notes */}
              {event.source_url && (
                <a
                  href={event.source_url}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.3rem',
                    fontSize: compact ? '0.7rem' : '0.75rem',
                    color: 'var(--accent)',
                    textDecoration: 'none',
                    marginTop: compact ? '0.1rem' : '0.15rem',
                  }}
                  onMouseOver={(e) => (e.target.style.textDecoration = 'underline')}
                  onMouseOut={(e) => (e.target.style.textDecoration = 'none')}
                >
                  <ExternalLink size={11} />
                  Source: {getSourceLabel(event.source)}
                </a>
              )}

              {event.notes && (
                <p
                  style={{
                    marginTop: compact ? '0.25rem' : '0.35rem',
                    fontSize: compact ? '0.78rem' : '0.82rem',
                    color: 'var(--text-2)',
                    lineHeight: 1.5,
                  }}
                >
                  {event.notes}
                </p>
              )}

              {event.act_id && (
                <span
                  style={{
                    display: 'inline-block',
                    marginTop: compact ? '0.2rem' : '0.3rem',
                    fontSize: compact ? '0.7rem' : '0.75rem',
                    color: 'var(--ok)',
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  Became Act: {event.act_id}
                </span>
              )}

              {event.pdf_url && (
                <a
                  href={event.pdf_url}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.3rem',
                    marginTop: compact ? '0.2rem' : '0.3rem',
                    fontSize: compact ? '0.7rem' : '0.75rem',
                    color: 'var(--accent)',
                    textDecoration: 'none',
                  }}
                  onMouseOver={(e) => (e.target.style.textDecoration = 'underline')}
                  onMouseOut={(e) => (e.target.style.textDecoration = 'none')}
                >
                  <ExternalLink size={11} />
                  PDF
                </a>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}