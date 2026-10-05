import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { diffAmendments } from '../services/api'

// Delta-aware amendment diff UI — POST /api/amendment/diff.
// Response sections: {title, content_preview, similarity, changed_facts[]}
const STATS_LABELS = {
  added_count: 'Added',
  removed_count: 'Removed',
  modified_count: 'Modified',
  similarity: 'Overall Similarity',
}

// What each side of the diff can be: the Bill as introduced, the Act it became, or a
// statute an Act amends (whose own text is read from India Code).
const KIND_LABELS = { bill: '📜 Bill', act: '⚖️ Act', statute: '🏛️ Statute' }
const kindLabel = (kind) => KIND_LABELS[kind] || '📄 Document'

export default function AmendmentsPage() {
  const [searchParams] = useSearchParams()
  // The Act page deep-links here with both sides chosen (v1 = the statute as it stood,
  // v2 = the Act that amends it). Prefilled, not auto-run — the diff spends an LLM
  // call, so the user presses the button.
  const [v1, setV1] = useState(() => searchParams.get('v1') || '')
  const [v2, setV2] = useState(() => searchParams.get('v2') || '')
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
      // 409 "matches more than one document" comes back with candidates to click.
      const data = err?.response?.data
      setError(
        data?.error
          ? { message: data.error, candidates: data.candidates || [], field: data.field || 'v1' }
          : { message: err?.message || 'Diff failed', candidates: [] }
      )
    } finally {
      setLoading(false)
    }
  }

  // Fill a field from a suggested document (kind + id come from the API).
  // Named apply* not use* — a `useX` name makes the rules-of-hooks linter treat this as
  // a hook, which cannot then be called from an onClick callback.
  const applyCandidate = (candidate) => {
    const value = candidate.id
    if (error?.field === 'v2') setV2(value)
    else setV1(value)
    setError(null)
  }

  return (
    <div className="container animate-fade-in" style={{ padding: '2rem 1rem' }}>
      <header style={{ marginBottom: '1.75rem' }}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: 800, letterSpacing: '-0.5px', margin: 0 }}>
          ⚖️ Amendment Diff
        </h1>
        <p style={{ color: 'var(--text-2)', fontSize: '0.85rem', margin: 0 }}>
          Delta-aware structural + factual diff between a bill, the Act it became, or a statute an Act amends · pure-Python engine, LLM narrative layer
        </p>
      </header>

      {/* Diff form */}
      <form onSubmit={handleDiff} className="glass-panel" style={{ borderRadius: 16, padding: '1.25rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) auto minmax(0,1fr)', gap: '0.75rem', alignItems: 'center', marginBottom: '0.5rem' }}>
          <input
            value={v1}
            onChange={(e) => setV1(e.target.value)}
            placeholder="Older — title or ID, e.g. andhra pradesh reorganisation act 2014"
            className="premium-input"
            style={{ width: '100%', padding: '0.7rem 1rem', fontSize: '0.85rem' }}
            aria-label="Older bill or Act"
          />
          <span style={{ color: 'var(--accent)', fontWeight: 800, fontSize: '1.2rem' }}>→</span>
          <input
            value={v2}
            onChange={(e) => setV2(e.target.value)}
            placeholder="Newer — title or ID, e.g. andhra pradesh reorganisation act 2026"
            className="premium-input"
            style={{ width: '100%', padding: '0.7rem 1rem', fontSize: '0.85rem' }}
            aria-label="Newer bill or Act"
          />
        </div>
        <p style={{ color: 'var(--text-3)', fontSize: '0.75rem', margin: '0 0 1rem' }}>
          Type the title as you know it (spaces are fine) or the document's ID — a Bill, the Act it
          became, or a statute an Act amends. Either side can be any of the three, so "the 2026 Act
          against the 2014 statute it changes" is a comparison this screen can actually run.
        </p>
        <button type="submit" disabled={loading || !v1.trim() || !v2.trim()} className="btn btn-primary" style={{ padding: '0.7rem 1.6rem', fontSize: '0.9rem' }}>
          {loading ? <><span className="spinner-ring" /> Computing delta…</> : '⚖️ Compute Diff'}
        </button>
        {error && (
          <div role="alert" style={{ marginTop: '0.85rem' }}>
            <p style={{ color: 'var(--danger)', fontSize: '0.85rem', margin: 0 }}>⚠️ {error.message}</p>
            {error.candidates?.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.6rem' }}>
                {error.candidates.map((c) => (
                  <button
                    key={`${c.kind}-${c.id}`}
                    type="button"
                    onClick={() => applyCandidate(c)}
                    title={`Use this ${c.kind}: ${c.id}`}
                    style={{
                      cursor: 'pointer', font: 'inherit', fontSize: '0.75rem', textAlign: 'left',
                      padding: '0.4rem 0.65rem', borderRadius: 8, color: 'var(--text-1)',
                      background: 'var(--surface-2)', border: '1px solid var(--border-1)',
                    }}
                  >
                    {kindLabel(c.kind)}
                    {' · '}{c.title}{c.year ? ` (${c.year})` : ''}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </form>

      {loading && (
        <p className="empty-state-text" style={{ textAlign: 'center', padding: '2rem' }}>Running structural analysis…</p>
      )}

      {result && (
        <div className="animate-fade-in">
          {/* Titles */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'baseline', marginBottom: '1rem' }}>
            <KindTag kind={result.kind_v1} />
            <strong style={{ color: 'var(--text-1)' }}>{result.title_v1}</strong>
            <span style={{ color: 'var(--accent)' }}>→</span>
            <KindTag kind={result.kind_v2} />
            <strong style={{ color: 'var(--text-1)' }}>{result.title_v2}</strong>
            <span className="badge badge-vidhan" style={{ marginLeft: 'auto' }}>model: {result.model_version}</span>
          </div>

          {/* When a whole statute was compared with an amending instrument the section
              counts are not a list of changes, so say so before showing them. */}
          {result.comparison_note && (
            <div className="glass-panel rounded-2xl" style={{ padding: '0.9rem 1.1rem', marginBottom: '1.1rem', borderLeft: '3px solid var(--warn, #d97706)' }}>
              <strong style={{ fontSize: '0.82rem', display: 'block', marginBottom: '0.3rem', color: 'var(--text-1)' }}>
                What this comparison is
              </strong>
              <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--text-2)', lineHeight: 1.6 }}>
                {result.comparison_note}
              </p>
            </div>
          )}

          {/* Stats row */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.75rem', marginBottom: '1.25rem' }}>
            {Object.entries(result.stats || {}).map(([k, val]) => (
              <div key={k} className="glass-panel rounded-xl text-center" style={{ padding: '0.85rem 0.5rem' }}>
                <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--accent-2)' }}>{String(val)}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-2)', fontWeight: 600, textTransform: 'uppercase' }}>{STATS_LABELS[k] || k.replace(/_/g, ' ')}</div>
              </div>
            ))}
          </div>

          {/* Narrative */}
          <section className="glass-panel rounded-2xl" style={{ padding: '1.25rem', marginBottom: '1.25rem' }} aria-label="Change narrative">
            <h2 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--accent-2)', margin: '0 0 0.5rem' }}>🧠 Change Narrative</h2>
            <p style={{ margin: 0, color: 'var(--text-1)', fontSize: '0.92rem', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
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
              <h2 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--accent-2)', margin: '0 0 0.65rem' }}>🔢 Factual Figure Changes</h2>
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

// Which document each side actually resolved to — the title alone can't say whether the
// diff compared a Bill, an Act, or one of each.
function KindTag({ kind }) {
  if (!kind) return null
  return (
    <span
      className="badge"
      style={{
        fontSize: '0.68rem', background: 'var(--surface-2)', color: 'var(--text-2)',
        border: '1px solid var(--border-1)', whiteSpace: 'nowrap',
      }}
    >
      {kindLabel(kind)}
    </span>
  )
}

function SectionList({ tone, icon, heading, sections }) {
  const borderTone = { emerald: 'var(--ok)', rose: 'var(--danger)', amber: 'var(--warn)' }[tone]
  return (
    <section className="glass-panel rounded-2xl" style={{ padding: '1rem', borderLeft: `3px solid ${borderTone}` }} aria-label={heading}>
      <h3 style={{ fontSize: '0.82rem', fontWeight: 700, margin: '0 0 0.6rem', color: borderTone }}>
        {icon} {heading}
      </h3>
      {!sections || sections.length === 0 ? (
        <p style={{ margin: 0, color: 'var(--text-3)', fontSize: '0.8rem' }}>None</p>
      ) : (
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '0.55rem', maxHeight: 320, overflowY: 'auto' }}>
          {sections.map((s, i) => (
            <li key={i} style={{ background: 'var(--surface-2)', borderRadius: 8, padding: '0.6rem 0.75rem' }}>
              <strong style={{ fontSize: '0.8rem', color: 'var(--text-1)', display: 'block', marginBottom: '0.25rem' }}>{s.title}</strong>
              {s.content_preview && (
                <p style={{ margin: 0, color: 'var(--text-2)', fontSize: '0.76rem', lineHeight: 1.55 }}>{s.content_preview}</p>
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
