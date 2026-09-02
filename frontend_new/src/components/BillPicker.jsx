import { useState, useRef, useEffect } from 'react'
import { Search, ChevronDown, X } from 'lucide-react'
import { smartFilterBills } from '../utils/billSearch'

// Searchable bill combobox — type to filter, click to select.
// Replaces the 100-option <select> in AlertsPage.
export default function BillPicker({ bills, value, onChange, loading, idPrefix = 'bp' }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const boxRef = useRef(null)

  const selected = bills.find((b) => (b.bill_id || b.id) === value)

  useEffect(() => {
    const onDocClick = (e) => {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [])

  const kw = query.trim()
  const filtered = smartFilterBills(bills, kw)

  return (
    <div ref={boxRef} style={{ position: 'relative' }}>
      <button
        type="button"
        id={idPrefix + '-trigger'}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="input"
        style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', textAlign: 'left', cursor: 'pointer', padding: '0.7rem 1rem' }}
      >
        <Search size={15} style={{ color: 'var(--text-3)', flexShrink: 0 }} />
        <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: selected ? 'var(--text-1)' : 'var(--text-3)' }}>
          {loading ? 'Loading bills…' : selected ? selected.title : 'Search bills by name, ministry, or status…'}
        </span>
        <ChevronDown size={15} style={{ color: 'var(--text-3)', flexShrink: 0 }} />
      </button>

      {open && (
        <div
          className="card animate-fade-in"
          role="listbox"
          aria-label="Bills"
          style={{
            position: 'absolute', top: 'calc(100% + 6px)', left: 0, right: 0,
            maxHeight: 300, overflowY: 'auto',
            zIndex: 50, boxShadow: 'var(--shadow-lg)',
          }}
        >
          <div style={{ position: 'sticky', top: 0, padding: '0.6rem', background: 'var(--surface)', borderBottom: '1px solid var(--border)' }}>
            <div style={{ position: 'relative' }}>
              <Search size={14} style={{ position: 'absolute', left: '0.7rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-3)' }} />
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Type to filter… (try 'gst', 'bns', 'income tax')"
                className="input"
                style={{ padding: '0.5rem 2rem 0.5rem 2.1rem', fontSize: '0.85rem' }}
                aria-label="Filter bills"
              />
              {query && (
                <button
                  type="button"
                  onClick={() => setQuery('')}
                  aria-label="Clear filter"
                  style={{ position: 'absolute', right: '0.55rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--text-3)', cursor: 'pointer', padding: 2 }}
                >
                  <X size={13} />
                </button>
              )}
            </div>
          </div>

          {filtered.length === 0 ? (
            <p className="empty-state-text" style={{ padding: '1.25rem', margin: 0, fontSize: '0.85rem' }}>
              No bills match "{query}".
            </p>
          ) : (
            <ul style={{ listStyle: 'none', margin: 0, padding: '0.35rem' }}>
              {filtered.map((b) => {
                const v = b.bill_id || b.id
                const isSel = v === value
                return (
                  <li key={b.id}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={isSel}
                      onClick={() => { onChange(v); setOpen(false) }}
                      className="sidebar-link"
                      style={{
                        width: '100%', textAlign: 'left', fontSize: '0.84rem',
                        background: isSel ? 'var(--accent-soft)' : 'transparent',
                        color: isSel ? 'var(--accent-3)' : 'var(--text-1)',
                      }}
                    >
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{b.title}</span>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
