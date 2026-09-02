import { useState, useEffect } from 'react'
import { Bell, CheckCircle, X } from 'lucide-react'
import { getAllBills, subscribeToAlerts } from '../services/api'
import BillPicker from '../components/BillPicker'

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

const labelStyle = {
  display: 'block',
  fontSize: '0.72rem',
  fontWeight: 600,
  color: 'var(--text-2)',
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  marginBottom: '0.4rem',
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
                  : `Subscribed! You'll get an alert whenever a new bill matches your topics.`,
        })
        if (mode === 'bill') setSelectedBill('')
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
    <div className="container animate-fade-in" style={{ padding: '2.25rem 1.25rem', maxWidth: 820 }}>
      <header style={{ marginBottom: '1.5rem' }}>
        <h1 className="page-title">🔔 Alerts</h1>
        <p className="page-sub">Get an email when bills you care about appear or change · powered by n8n + Gmail</p>
      </header>

      {success && (
        <div role="status" className="card animate-fade-in" style={{ padding: '1.1rem 1.25rem', marginBottom: '1.1rem', borderLeft: '3px solid var(--ok)' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
            <CheckCircle size={18} color="var(--ok)" />
            <div style={{ flex: 1 }}>
              <strong style={{ color: 'var(--ok)', fontSize: '0.88rem' }}>{success.billTracked ? 'Bill tracker active' : 'Subscription active'}</strong>
              <p style={{ margin: '0.25rem 0 0', color: 'var(--text-1)', fontSize: '0.86rem', lineHeight: 1.55 }}>{success.message}</p>
            </div>
            <button type="button" onClick={() => setSuccess(null)} aria-label="Dismiss" style={{ background: 'none', border: 'none', color: 'var(--text-3)', cursor: 'pointer' }}>
              <X size={15} />
            </button>
          </div>
        </div>
      )}
      {error && (
        <div role="alert" className="card" style={{ padding: '0.9rem 1.25rem', marginBottom: '1.1rem', borderLeft: '3px solid var(--danger)' }}>
          <p style={{ margin: 0, color: 'var(--danger)', fontSize: '0.86rem' }}>⚠️ {error}</p>
        </div>
      )}

      <form onSubmit={handleSubscribe} className="card" style={{ padding: '1.5rem' }}>
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
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Email */}
        <label htmlFor="al-email" style={labelStyle}>Email address</label>
        <input
          id="al-email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          className="input"
        />

        {/* Bill mode */}
        {mode === 'bill' && (
          <div className="animate-fade-in" style={{ marginTop: '1.25rem' }}>
            <label style={labelStyle}>Bill to track</label>
            <BillPicker bills={bills} value={selectedBill} onChange={setSelectedBill} loading={billsLoading} idPrefix="al" />
            <p style={{ margin: '0.55rem 0 0', color: 'var(--text-3)', fontSize: '0.76rem' }}>
              Welcome email includes the AI summary; you'll get status-change alerts (e.g. Introduced → Passed).
            </p>
          </div>
        )}

        {/* Category mode */}
        {mode === 'category' && (
          <div className="animate-fade-in" style={{ marginTop: '1.25rem' }}>
            <label htmlFor="al-kw" style={labelStyle}>Keywords</label>
            {keywords.length > 0 && (
              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
                {keywords.map((k) => (
                  <span key={k} className="badge badge-vidhan" style={{ fontSize: '0.78rem', padding: '0.3rem 0.7rem' }}>
                    {k}
                    <button type="button" onClick={() => removeKeyword(k)} aria-label={`Remove ${k}`} style={{ background: 'none', border: 'none', color: 'var(--accent-3)', cursor: 'pointer', marginLeft: '0.3rem' }}>✕</button>
                  </span>
                ))}
              </div>
            )}
            <input
              id="al-kw"
              value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addKeyword(keywordInput) } }}
              placeholder="Type a keyword and press Enter…"
              className="input"
            />
            <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginTop: '0.6rem' }}>
              {KEYWORD_SUGGESTIONS.filter((s) => !keywords.includes(s)).map((s) => (
                <button key={s} type="button" onClick={() => addKeyword(s)} className="chip">{s}</button>
              ))}
            </div>

            <label style={{ ...labelStyle, marginTop: '1.1rem' }}>Ministries (optional)</label>
            <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
              {MINISTRIES.map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => toggleMinistry(m)}
                  aria-pressed={ministries.includes(m)}
                  className="chip"
                  style={ministries.includes(m) ? { background: 'var(--accent-soft)', borderColor: 'rgba(99,102,241,.5)', color: 'var(--accent-3)' } : undefined}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Frequency */}
        <fieldset style={{ border: 'none', padding: 0, margin: '1.25rem 0 0' }}>
          <legend style={{ ...labelStyle, padding: 0 }}>Email frequency</legend>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '0.6rem' }}>
            {FREQUENCIES.map((f) => (
              <label
                key={f.value}
                className="card card-hover"
                style={{
                  display: 'block', padding: '0.8rem 0.9rem', cursor: 'pointer',
                  borderColor: frequency === f.value ? 'rgba(99,102,241,.5)' : 'var(--border)',
                  background: frequency === f.value ? 'var(--accent-soft)' : 'var(--surface-2)',
                }}
              >
                <input
                  type="radio"
                  name="frequency"
                  value={f.value}
                  checked={frequency === f.value}
                  onChange={() => setFrequency(f.value)}
                  style={{ width: 13, height: 13, accentColor: '#6366f1', marginRight: '0.4rem' }}
                />
                <strong style={{ fontSize: '0.84rem' }}>{f.label}</strong>
                <div style={{ color: 'var(--text-3)', fontSize: '0.7rem', marginTop: '0.25rem', marginLeft: '1.3rem' }}>{f.hint}</div>
              </label>
            ))}
          </div>
        </fieldset>

        <button type="submit" disabled={!isValid || loading} className="btn btn-primary" style={{ marginTop: '1.4rem', padding: '0.7rem 1.5rem' }}>
          {loading ? <><span className="spinner-ring" /> Subscribing…</> : <><Bell size={15} /> Subscribe to alerts</>}
        </button>
      </form>
    </div>
  )
}

// n8n welcome-email webhook. Override at build time with VITE_N8N_WEBHOOK_URL.
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
