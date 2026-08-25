import { useState } from 'react'
import { diffAmendments } from '../services/api'

// Delta-aware amendment diff UI — POST /api/amendment/diff.
// Response sections: {title, content_preview, similarity, changed_facts[]}
const STATS_LABELS = {
  added_count: 'Added',
  removed_count: 'Removed',
  modified_count: 'Modified',
  similarity: 'Overall Similarity',
}

export default function AmendmentsPage() {
  const [v1, setV1] = useState('')
  const [v2, setV2] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  const handleDiff = async (e) => {
    e.preventDefault()
    if (!v1.trim() || !v2.trim() || loading) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await diffAmendments(v1.trim(), v2.trim())
      setResult(data)
    } catch (err) {
      setError(err?.response?.data?.error || err?.message || 'Diff failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container animate-fade-in" style={{ padding: '2rem 1rem' }}>
      <header style={{ marginBottom: '1.75rem' }}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: 800, letterSpacing: '-0.5px', margin: 0 }}>
          ⚖️ Amendment Diff
        </h1>
        <p style={{ color: '#64748b', fontSize: '0.85rem', margin: 0 }}>
          Delta-aware structural + factual diff between two bills · pure-Python engine, LLM narrative layer
        </p>
      </header>

      {/* Diff form */}
      <form onSubmit={handleDiff} className="glass-panel" style={{ borderRadius: 16, padding: '1.25rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) auto minmax(0,1fr)', gap: '0.75rem', alignItems: 'center', marginBottom: '1rem' }}>
          <input
            value={v1}
            onChange={(e) => setV1(e.target.value)}
            placeholder="Older bill slug (v1) — e.g. criminal-procedure-code-2022"
            className="premium-input"
            style={{ width: '100%', padding: '0.7rem 1rem', fontSize: '0.85rem', fontFamily: 'JetBrains Mono, monospace' }}
            aria-label="Older bill id"
          />
          <span style={{ color: '#8b5cf6', fontWeight: 800, fontSize: '1.2rem' }}>→</span>
          <input
            value={v2}
            onChange={(e) => setV2(e.target.value)}
            placeholder="Newer bill slug (v2) — e.g. central-universities-amendment-2023"
            className="premium-input"
            style={{ width: '100%', padding: '0.7rem 1rem', fontSize: '0.85rem', fontFamily: 'JetBrains Mono, monospace' }}
            aria-label="Newer bill id"
          />
        </div>
        <button type="submit" disabled={loading || !v1.trim() || !v2.trim()} className="btn btn-primary" style={{ padding: '0.7rem 1.6rem', fontSize: '0.9rem' }}>
          {loading ? <><span className="spinner-ring" /> Computing delta…</> : '⚖️ Compute Diff'}
        </button>
        {error && (
          <p role="alert" style={{ marginTop: '0.85rem', color: '#f87171', fontSize: '0.85rem', marginBottom: 0 }}>
            ⚠️ {error}
          </p>
        )}
      </form>

      {loading && (
        <p className="empty-state-text" style={{ textAlign: 'center', padding: '2rem' }}>Running structural analysis…</p>
      )}

      {result && (
        <div className="animate-fade-in">
          {/* Titles */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'baseline', marginBottom: '1rem' }}>
            <strong style={{ color: '#cbd5e1' }}>{result.title_v1}</strong>
            <span style={{ color: '#8b5cf6' }}>→</span>
            <strong style={{ color: '#cbd5e1' }}>{result.title_v2}</strong>
            <span className="badge badge-vidhan" style={{ marginLeft: 'auto' }}>model: {result.model_version}</span>
          </div>

          {/* Stats row */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.75rem', marginBottom: '1.25rem' }}>
            {Object.entries(result.stats || {}).map(([k, val]) => (
              <div key={k} className="glass-panel rounded-xl text-center" style={{ padding: '0.85rem 0.5rem' }}>
                <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#a78bfa' }}>{String(val)}</div>
                <div style={{ fontSize: '0.7rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>{STATS_LABELS[k] || k.replace(/_/g, ' ')}</div>
              </div>
            ))}
          </div>

          {/* Narrative */}
          <section className="glass-panel rounded-2xl" style={{ padding: '1.25rem', marginBottom: '1.25rem' }} aria-label="Change narrative">
            <h2 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#c4b5fd', margin: '0 0 0.5rem' }}>🧠 Change Narrative</h2>
            <p style={{ margin: 0, color: '#e2e8f0', fontSize: '0.92rem', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
              {result.narrative || result.diff_summary_text}
            </p>
          </section>

          {/* Sections */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            <SectionList tone="emerald" icon="➕" heading={`Added (${(result.added_sections || []).length})`} sections={result.added_sections} />
            <SectionList tone="rose" icon="➖" heading={`Removed (${(result.removed_sections || []).length})`} sections={result.removed_sections} />
            <SectionList tone="amber" icon="✏️" heading={`Modified (${(result.modified_sections || []).length})`} sections={result.modified_sections} />
          </div>

          {/* Facts */}
          {(result.facts_added?.length > 0 || result.facts_removed?.length > 0) && (
            <section className="glass-panel rounded-2xl" style={{ padding: '1.25rem', marginTop: '1.25rem' }} aria-label="Factual changes">
              <h2 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#c4b5fd', margin: '0 0 0.65rem' }}>🔢 Factual Figure Changes</h2>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.45rem' }}>
                {(result.facts_added || []).map((f, i) => (
                  <span key={`a${i}`} className="badge badge-emerald">+ {String(f)}</span>
                ))}
                {(result.facts_removed || []).map((f, i) => (
                  <span key={`r${i}`} className="badge badge-rose">− {String(f)}</span>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  )
}

function SectionList({ tone, icon, heading, sections }) {
  const borderTone = { emerald: '#34d399', rose: '#f43f5e', amber: '#f59e0b' }[tone]
  return (
    <section className="glass-panel rounded-2xl" style={{ padding: '1rem', borderLeft: `3px solid ${borderTone}` }} aria-label={heading}>
      <h3 style={{ fontSize: '0.82rem', fontWeight: 700, margin: '0 0 0.6rem', color: borderTone }}>
        {icon} {heading}
      </h3>
      {!sections || sections.length === 0 ? (
        <p style={{ margin: 0, color: '#334155', fontSize: '0.8rem' }}>None</p>
      ) : (
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '0.55rem', maxHeight: 320, overflowY: 'auto' }}>
          {sections.map((s, i) => (
            <li key={i} style={{ background: 'rgba(255,255,255,0.03)', borderRadius: 8, padding: '0.6rem 0.75rem' }}>
              <strong style={{ fontSize: '0.8rem', color: '#cbd5e1', display: 'block', marginBottom: '0.25rem' }}>{s.title}</strong>
              {s.content_preview && (
                <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.76rem', lineHeight: 1.55 }}>{s.content_preview}</p>
              )}
              {s.changed_facts?.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem', marginTop: '0.35rem' }}>
                  {s.changed_facts.map((cf, j) => (
                    <span key={j} className="badge badge-amber" style={{ fontSize: '0.68rem' }}>{String(cf)}</span>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
