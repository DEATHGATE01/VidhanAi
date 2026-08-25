import { useState, useEffect } from 'react'
import { Bell, CheckCircle, X } from 'lucide-react'
import { getAllBills, subscribeToAlerts } from '../services/api'

const MINISTRIES = [
  'Finance', 'Home Affairs', 'Law and Justice',
  'Electronics and Information Technology', 'Health and Family Welfare',
  'Agriculture and Farmers Welfare', 'Education', 'Defence',
  'Commerce and Industry', 'Railways', 'Road Transport and Highways',
  'Civil Aviation', 'Environment, Forest and Climate Change',
  'Housing and Urban Affairs', 'Rural Development',
]

const KEYWORD_SUGGESTIONS = ['tax', 'gaming', 'data protection', 'telecom', 'health', 'education', 'criminal law', 'environment']
const FREQUENCIES = [
  { value: 'instant', label: 'Instant', hint: 'Email as soon as a matching bill appears' },
  { value: 'daily', label: 'Daily digest', hint: 'One email per day with everything new' },
  { value: 'weekly', label: 'Weekly digest', hint: 'One email per week with everything new' },
]

const inputStyle = {
  width: '100%',
  padding: '0.7rem 1rem',
  fontSize: '0.9rem',
}

// n8n welcome-email workflow webhook. Override at build time with
// VITE_N8N_WEBHOOK_URL for production.
const N8N_WEBHOOK_URL = import.meta.env.VITE_N8N_WEBHOOK_URL || 'http://localhost:5678/webhook/vidhanai-welcome-email'

// Fire-and-forget: the subscription is already saved when this runs, so an
// unreachable n8n must never surface as an error to the user.
async function triggerWelcomeEmail(subscribeResponse) {
  try {
    const res = await fetch(N8N_WEBHOOK_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(subscribeResponse),
    })
    return res.ok
  } catch {
    return false
  }
}

export default function AlertsPage() {
  const [mode, setMode] = useState('category')
  const [email, setEmail] = useState('')
  const [bills, setBills] = useState([])
  const [selectedBill, setSelectedBill] = useState('')
  const [keywords, setKeywords] = useState([])
  const [keywordInput, setKeywordInput] = useState('')
  const [ministries, setMinistries] = useState([])
  const [frequency, setFrequency] = useState('instant')
  const [loading, setLoading] = useState(false)
  const [billsLoading, setBillsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  useEffect(() => {
    let cancelled = false
    getAllBills(1, 100)
      .then((data) => { if (!cancelled && data.success) setBills(data.bills || []) })
      .catch(() => {})
      .finally(() => { if (!cancelled) setBillsLoading(false) })
    return () => { cancelled = true }
  }, [])

  const addKeyword = (kw) => {
    const v = kw.trim().toLowerCase()
    if (v && !keywords.includes(v)) setKeywords((k) => [...k, v])
    setKeywordInput('')
  }

  const removeKeyword = (k) => setKeywords((prev) => prev.filter((x) => x !== k))

  const toggleMinistry = (m) => {
    setMinistries((prev) => (prev.includes(m) ? prev.filter((x) => x !== m) : [...prev, m]))
  }

  const isValid =
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()) &&
    (mode === 'bill' ? Boolean(selectedBill) : keywords.length > 0 || ministries.length > 0)

  const handleSubscribe = async (e) => {
    e.preventDefault()
    if (!isValid || loading) return
    setLoading(true)
    setError(null)
    setSuccess(null)
    try {
      const data = await subscribeToAlerts({
        email: email.trim(),
        specificBills: mode === 'bill' ? [selectedBill] : [],
        keywords,
        ministries,
        frequency,
      })
      if (data.success) {
        const n = (data.welcome_alerts || []).length
        const m = (data.recent_matches || []).length
        // Welcome email is best-effort: the subscription is already saved,
        // so an unreachable n8n must never surface as an error.
        const emailSent = n > 0 || m > 0 ? await triggerWelcomeEmail(data) : false
        setSuccess({
          billTracked: n > 0,
          message:
            n > 0
              ? `Tracking "${data.welcome_alerts[0].bill_title}". ${emailSent ? 'A welcome email with its summary is on the way to ' + email.trim() + '.' : 'Could not reach the mail service for the welcome email.'}`
              : mode === 'bill'
                ? 'You are already tracking this bill — the summary email was sent when you first added it, and status-change alerts stay active.'
                : m > 0
                  ? `Subscribed! ${emailSent ? `A welcome email with ${m} recent matching bills is on the way to ${email.trim()}.` : 'Could not reach the mail service for the welcome email.'} You'll get an alert whenever a new bill matches.`
                  : emailSent
                    ? `Subscribed! Confirmation email sent to ${email.trim()}.`
                    : `Subscribed! You'll get an alert whenever a new bill matches your topics.`,
        })
      } else {
        setError(data.error || 'Subscription failed')
      }
    } catch (err) {
      setError(err?.response?.data?.error || err?.message || 'Request failed — is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container animate-fade-in" style={{ padding: '2rem 1rem', maxWidth: 860 }}>
      <header style={{ marginBottom: '1.75rem' }}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: 800, letterSpacing: '-0.5px', margin: 0 }}>
          🔔 Alerts
        </h1>
        <p style={{ color: '#64748b', fontSize: '0.85rem', margin: 0 }}>
          Get an email when bills you care about appear or change · powered by n8n + Gmail
        </p>
      </header>

      {/* Success / error banners */}
      {success && (
        <div role="status" className="glass-panel rounded-2xl animate-fade-in" style={{ padding: '1.25rem', marginBottom: '1.25rem', borderLeft: '3px solid #34d399' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
            <CheckCircle size={20} color="#34d399" />
            <div style={{ flex: 1 }}>
              <strong style={{ color: '#34d399', fontSize: '0.92rem' }}>{success.billTracked ? 'Bill tracker active' : 'Subscription active'}</strong>
              <p style={{ margin: '0.3rem 0 0', color: '#cbd5e1', fontSize: '0.88rem', lineHeight: 1.6 }}>{success.message}</p>
            </div>
            <button type="button" onClick={() => setSuccess(null)} aria-label="Dismiss" style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer' }}>
              <X size={16} />
            </button>
          </div>
        </div>
      )}
      {error && (
        <div role="alert" className="glass-panel rounded-2xl" style={{ padding: '1rem 1.25rem', marginBottom: '1.25rem', borderLeft: '3px solid #f87171' }}>
          <p style={{ margin: 0, color: '#f87171', fontSize: '0.88rem' }}>⚠️ {error}</p>
        </div>
      )}

      <form onSubmit={handleSubscribe} className="glass-panel" style={{ borderRadius: 16, padding: '1.5rem' }}>
        {/* Mode tabs */}
        <div role="tablist" aria-label="Subscription type" style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem' }}>
          {[
            { id: 'bill', label: '🎯 Track a specific bill' },
            { id: 'category', label: '🗂️ Follow a topic' },
          ].map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={mode === t.id}
              onClick={() => setMode(t.id)}
              className={mode === t.id ? 'btn btn-primary' : 'btn btn-secondary'}
              style={{ padding: '0.55rem 1.1rem', fontSize: '0.85rem' }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Email */}
        <label htmlFor="al-email" style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.4rem' }}>
          Email address
        </label>
        <input
          id="al-email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          className="premium-input"
          style={inputStyle}
        />

        {/* Bill mode */}
        {mode === 'bill' && (
          <div className="animate-fade-in" style={{ marginTop: '1.25rem' }}>
            <label htmlFor="al-bill" style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.4rem' }}>
              Bill to track
            </label>
            <select
              id="al-bill"
              value={selectedBill}
              onChange={(e) => setSelectedBill(e.target.value)}
              className="premium-input"
              style={{ ...inputStyle, cursor: 'pointer' }}
            >
              <option value="">
                {billsLoading ? 'Loading bills…' : `— choose a bill (${bills.length} loaded) —`}
              </option>
              {bills.map((b) => (
                <option key={b.id} value={b.bill_id || b.id}>{b.title}</option>
              ))}
            </select>
            <p style={{ margin: '0.6rem 0 0', color: '#475569', fontSize: '0.78rem' }}>
              Welcome email includes the AI summary; you'll get status-change alerts (e.g. Introduced → Passed).
            </p>
          </div>
        )}

        {/* Category mode */}
        {mode === 'category' && (
          <div className="animate-fade-in" style={{ marginTop: '1.25rem' }}>
            <label htmlFor="al-kw" style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.4rem' }}>
              Keywords
            </label>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
              {keywords.map((k) => (
                <span key={k} className="badge badge-vidhan" style={{ fontSize: '0.78rem', padding: '0.35rem 0.75rem' }}>
                  {k}
                  <button type="button" onClick={() => removeKeyword(k)} aria-label={`Remove ${k}`} style={{ background: 'none', border: 'none', color: '#c4b5fd', cursor: 'pointer', marginLeft: '0.35rem', fontSize: '0.85em' }}>✕</button>
                </span>
              ))}
            </div>
            <input
              id="al-kw"
              value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addKeyword(keywordInput) } }}
              placeholder="Type a keyword and press Enter…"
              className="premium-input"
              style={inputStyle}
            />
            <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginTop: '0.6rem' }}>
              {KEYWORD_SUGGESTIONS.filter((s) => !keywords.includes(s)).map((s) => (
                <button key={s} type="button" onClick={() => addKeyword(s)} className="chip">{s}</button>
              ))}
            </div>

            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', margin: '1.1rem 0 0.5rem' }}>
              Ministries (optional)
            </label>
            <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
              {MINISTRIES.map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => toggleMinistry(m)}
                  aria-pressed={ministries.includes(m)}
                  className="chip"
                  style={
                    ministries.includes(m)
                      ? { background: 'rgba(139,92,246,0.2)', borderColor: 'rgba(139,92,246,0.5)', color: '#ddd6fe' }
                      : undefined
                  }
                >
                  {m}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Frequency */}
        <fieldset style={{ border: 'none', padding: 0, margin: '1.25rem 0 0' }}>
          <legend style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem', padding: 0 }}>
            Email frequency
          </legend>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.6rem' }}>
            {FREQUENCIES.map((f) => (
              <label
                key={f.value}
                style={{
                  display: 'block',
                  padding: '0.75rem 0.9rem',
                  borderRadius: 12,
                  border: frequency === f.value ? '1px solid rgba(139,92,246,0.5)' : '1px solid rgba(255,255,255,0.08)',
                  background: frequency === f.value ? 'rgba(139,92,246,0.12)' : 'rgba(255,255,255,0.02)',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="radio"
                  name="frequency"
                  value={f.value}
                  checked={frequency === f.value}
                  onChange={() => setFrequency(f.value)}
                  style={{ width: 14, height: 14, accentColor: '#8b5cf6', marginRight: '0.45rem' }}
                />
                <strong style={{ fontSize: '0.85rem' }}>{f.label}</strong>
                <div style={{ color: '#64748b', fontSize: '0.72rem', marginTop: '0.25rem', marginLeft: '1.35rem' }}>{f.hint}</div>
              </label>
            ))}
          </div>
        </fieldset>

        <button type="submit" disabled={!isValid || loading} className="btn btn-primary" style={{ marginTop: '1.5rem', padding: '0.75rem 1.75rem', fontSize: '0.95rem' }}>
          {loading ? <><span className="spinner-ring" /> Subscribing…</> : <><Bell size={15} /> Subscribe to alerts</>}
        </button>
      </form>
    </div>
  )
}
