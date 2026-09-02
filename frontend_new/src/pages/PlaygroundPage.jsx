import { useState, useEffect } from 'react'
import { getAllBills, getBillSummary } from '../services/api'

// Model playground — pick a bill, generate its summary, and see exactly
// which backend produced it (model_version), per the Phase-1 honesty rules.
export default function PlaygroundPage() {
  const [bills, setBills] = useState([])
  const [billId, setBillId] = useState('')
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    getAllBills(1, 50)
      .then((data) => {
        if (!cancelled && data.success) setBills(data.bills || [])
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [])

  const handleGenerate = async (e) => {
    e.preventDefault()
    if (!billId || loading) return
    setLoading(true)
    setError(null)
    setSummary(null)
    try {
      const data = await getBillSummary(billId)
      if (data.success) setSummary(data.summary)
      else setError(data.error || 'Summary generation failed')
    } catch (err) {
      setError(err?.response?.data?.error || err?.message || 'Request failed — is the backend on :5000?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container animate-fade-in" style={{ padding: '2rem 1rem' }}>
      <header style={{ marginBottom: '1.75rem' }}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: 800, letterSpacing: '-0.5px', margin: 0 }}>
          🔬 Model Playground
        </h1>
        <p style={{ color: 'var(--text-2)', fontSize: '0.85rem', margin: 0 }}>
          Generate bill summaries and audit which model produced them · every result carries its model_version
        </p>
      </header>

      <form onSubmit={handleGenerate} className="glass-panel rounded-2xl" style={{ padding: '1.25rem', marginBottom: '1.5rem' }}>
        <label htmlFor="pg-bill" style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-2)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.4rem' }}>
          Select a bill
        </label>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <select
            id="pg-bill"
            value={billId}
            onChange={(e) => setBillId(e.target.value)}
            className="premium-input"
            style={{ flex: 1, minWidth: 260, padding: '0.65rem 0.85rem', fontSize: '0.88rem', cursor: 'pointer' }}
          >
            <option value="">— choose a bill ({bills.length} loaded) —</option>
            {bills.map((b) => (
              <option key={b.id} value={b.bill_id || b.id}>{b.title}</option>
            ))}
          </select>
          <button type="submit" disabled={!billId || loading} className="btn btn-primary" style={{ padding: '0.7rem 1.5rem', fontSize: '0.9rem' }}>
            {loading ? <><span className="spinner-ring" /> Generating…</> : '⚡ Generate Summary'}
          </button>
        </div>
        {error && (
          <p role="alert" style={{ marginTop: '0.85rem', color: 'var(--danger)', fontSize: '0.85rem', marginBottom: 0 }}>⚠️ {error}</p>
        )}
      </form>

      {loading && (
        <p className="empty-state-text" style={{ textAlign: 'center', padding: '2rem' }}>
          First generation may take ~30s (Groq free tier)…
        </p>
      )}

      {summary && (
        <section className="glass-panel rounded-2xl animate-fade-in" style={{ padding: '1.5rem' }} aria-label="Generated summary">
          {/* Provenance chips */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.45rem', marginBottom: '1rem' }}>
            <span className="badge badge-vidhan">model: {summary.model_version || 'unknown'}</span>
            {summary.guardrail_applied != null && (
              <span className={`badge ${summary.guardrail_applied ? 'badge-emerald' : 'badge-rose'}`}>
                guardrail: {summary.guardrail_applied ? 'applied' : 'not applied'}
              </span>
            )}
            {summary.guardrail_version && (
              <span className="badge badge-slate">guardrail v{summary.guardrail_version}</span>
            )}
            {summary.generated_at && (
              <span className="badge badge-slate">
                {new Date(summary.generated_at).toLocaleString('en-IN')}
              </span>
            )}
          </div>

          <h2 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--accent-2)', margin: '0 0 0.5rem' }}>📝 Plain-English Summary</h2>
          <p style={{ margin: 0, color: 'var(--text-1)', fontSize: '0.95rem', lineHeight: 1.75, whiteSpace: 'pre-wrap' }}>
            {summary.summary}
          </p>
        </section>
      )}
    </div>
  )
}
