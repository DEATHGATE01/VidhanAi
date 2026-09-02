import { ExternalLink, Heart } from 'lucide-react'

// Card for a single bill in Explore grid/list views.
// bill shape (from /api/bills): { id, title, ministry, status,
//   introduction_date, url, ... }
export default function BillCard({ bill, onViewDetails, onAddFavorite, isSelected, onToggleSelect }) {
  const dateLabel = bill.introduction_date
    ? new Date(bill.introduction_date).toLocaleDateString('en-IN', { year: 'numeric', month: 'short', day: 'numeric' })
    : null

  const statusTone =
    bill.status?.toLowerCase().includes('pass')
      ? 'badge-emerald'
      : bill.status?.toLowerCase().includes('withdraw') || bill.status?.toLowerCase().includes('laps')
        ? 'badge-rose'
        : 'badge-vidhan'

  return (
    <article
      className="card card-hover rounded-2xl"
      style={{
        padding: '1.25rem',
        background: 'var(--surface)',
        borderColor: isSelected ? 'rgba(99,102,241,0.5)' : 'var(--border)',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.6rem',
      }}
      aria-selected={isSelected}
    >
      {/* Badges + select checkbox */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', alignItems: 'center' }}>
        <span className={`badge ${statusTone}`}>{bill.status || 'Unknown'}</span>
        {dateLabel && <span className="badge badge-slate">📅 {dateLabel}</span>}
        <button
          type="button"
          onClick={onToggleSelect}
          aria-label={isSelected ? `Deselect ${bill.title}` : `Select ${bill.title}`}
          style={{
            marginLeft: 'auto',
            width: 20,
            height: 20,
            borderRadius: 6,
            border: '1px solid var(--border-strong)',
            background: isSelected ? 'var(--accent)' : 'transparent',
            color: 'var(--on-accent)',
            fontSize: '0.7rem',
            lineHeight: 1,
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {isSelected ? '✓' : ''}
        </button>
      </div>

      {/* Title — opens the in-app summary panel */}
      <h3 style={{ fontSize: '1rem', fontWeight: 600, lineHeight: 1.45, margin: 0 }}>
        <button
          type="button"
          onClick={onViewDetails}
          title={`Open summary for ${bill.title}`}
          className="hover:text-vidhan-300 transition-colors"
          style={{
            padding: 0,
            border: 0,
            background: 'none',
            color: 'inherit',
            cursor: 'pointer',
            font: 'inherit',
            textAlign: 'left',
          }}
        >
          {bill.title}
        </button>
      </h3>

      {/* Ministry */}
      {bill.ministry && (
        <p style={{ margin: 0, color: 'var(--text-2)', fontSize: '0.8rem' }}>🏛️ {bill.ministry}</p>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', gap: '0.5rem', marginTop: 'auto', paddingTop: '0.5rem' }}>
        <button type="button" onClick={onViewDetails} className="btn btn-secondary" style={{ padding: '0.35rem 0.85rem', fontSize: '0.78rem' }}>
          <ExternalLink size={13} /> Details
        </button>
        <button
          type="button"
          onClick={onAddFavorite}
          className="btn btn-ghost"
          style={{ padding: '0.35rem 0.85rem', fontSize: '0.78rem' }}
          aria-label={`Add ${bill.title} to favorites`}
        >
          <Heart size={13} /> Favorite
        </button>
      </div>
    </article>
  )
}
