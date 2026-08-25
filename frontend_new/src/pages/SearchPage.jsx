import { useState } from 'react'
import { searchBills } from '../services/api'

// Semantic search UI — GET /api/semantic-search (ChromaDB + input guardrails).
// A 403 with is_guardrailed=true means the query was blocked by the
// prompt-injection filter, which we surface distinctly.
export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [guardrailed, setGuardrailed] = useState(false)
  const [searched, setSearched] = useState(false)

  const handleSearch = async (e) => {
    e.preventDefault()
    const q = query.trim()
    if (!q || loading) return
    setLoading(true)
    setError(null)
    setGuardrailed(false)
    setResults([])
    try {
      const data = await searchBills(q)
      setResults(data.results || [])
      setSearched(true)
    } catch (err) {
      if (err?.response?.status === 403 && err.response.data?.is_guardrailed) {
        setGuardrailed(true)
        setError(err.response.data.error || 'Query blocked by input guardrails')
      } else {
        setError(err?.response?.data?.error || err?.message || 'Search failed — is the backend on :5000?')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container animate-fade-in" style={{ padding: '2rem 1rem' }}>
      <header style={{ marginBottom: '1.75rem' }}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: 800, letterSpacing: '-0.5px', margin: 0 }}>
          🔍 Semantic Search
        </h1>
        <p style={{ color: '#64748b', fontSize: '0.85rem', margin: 0 }}>
          Meaning-based retrieval over ChromaDB embeddings (all-MiniLM-L6-v2) · protected by input guardrails
        </p>
      </header>

      <form onSubmit={handleSearch} className="glass-panel rounded-2xl" style={{ padding: '1.25rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Describe what you're looking for… e.g. 'privacy of digital communications'"
            className="premium-input"
            style={{ flex: 1, padding: '0.75rem 1.1rem', fontSize: '0.92rem' }}
            aria-label="Semantic search query"
          />
          <button type="submit" disabled={loading || !query.trim()} className="btn btn-primary" style={{ padding: '0.7rem 1.5rem', fontSize: '0.9rem' }}>
            {loading ? <><span className="spinner-ring" /> Searching</> : 'Search'}
          </button>
        </div>
        {error && (
          <p role="alert" style={{ marginTop: '0.85rem', color: guardrailed ? '#fbbf24' : '#f87171', fontSize: '0.85rem', marginBottom: 0 }}>
            {guardrailed ? '🛡️ Guardrail: ' : '⚠️ '}{error}
          </p>
        )}
      </form>

      {searched && !loading && results.length === 0 && !error && (
        <div className="empty-state" style={{ padding: '3rem 1rem' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem', opacity: 0.5 }}>🫥</div>
          <p className="empty-state-text">No bills matched that meaning. Try rephrasing.</p>
        </div>
      )}

      {results.length > 0 && (
        <>
          <p style={{ color: '#64748b', fontSize: '0.82rem', margin: '0 0 0.85rem' }}>
            {results.length} result{results.length === 1 ? '' : 's'} · ranked by semantic similarity
          </p>
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            {results.map((bill) => (
              <li key={bill.id}>
                <article className="glass-panel card-hover rounded-xl" style={{ padding: '1.15rem' }}>
                  <h3 style={{ fontSize: '1rem', fontWeight: 600, margin: '0 0 0.35rem', lineHeight: 1.45 }}>
                    {bill.url ? (
                      <a href={bill.url} target="_blank" rel="noopener noreferrer" className="hover:text-vidhan-300 transition-colors">
                        {bill.title}
                      </a>
                    ) : (
                      bill.title
                    )}
                  </h3>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                    {bill.status && <span className="badge badge-vidhan">{bill.status}</span>}
                    {bill.ministry && <span className="badge badge-slate">{bill.ministry}</span>}
                    {bill.introduction_date && (
                      <span className="badge badge-slate">
                        📅 {new Date(bill.introduction_date).toLocaleDateString('en-IN', { year: 'numeric', month: 'short' })}
                      </span>
                    )}
                  </div>
                </article>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
