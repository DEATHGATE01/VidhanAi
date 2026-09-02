import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { X, Bell, ExternalLink, ShieldCheck, Cpu, CalendarDays } from 'lucide-react'
import { getBillSummary, subscribeToAlerts } from '../services/api'
import { useUser } from '../context/UserContext'
import SignInModal from './SignInModal'

const FREQUENCIES = [
  { value: 'instant', label: 'Instant' },
  { value: 'daily', label: 'Daily digest' },
  { value: 'weekly', label: 'Weekly digest' },
]

// n8n welcome-email webhook (same wiring as AlertsPage).
const N8N_WEBHOOK_URL = import.meta.env.VITE_N8N_WEBHOOK_URL || 'http://localhost:5678/webhook/vidhanai-welcome-email'

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

// Slide-over panel showing one bill's AI summary (markdown-rendered) plus a
// "Get alerts for this bill" control that subscribes with the profile email.
export default function BillSummaryPanel({ bill, onClose }) {
  const { user } = useUser()
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [freq, setFreq] = useState('instant')
  const [subBusy, setSubBusy] = useState(false)
  const [subMsg, setSubMsg] = useState(null)
  const [signInOpen, setSignInOpen] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setLoadError('')
    setSummary(null)
    setSubMsg(null)
    getBillSummary(bill.id)
      .then((data) => { if (!cancelled) setSummary(data?.summary || null) })
      .catch((err) => { if (!cancelled) setLoadError(err?.response?.data?.error || err?.message || 'Could not load the summary.') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [bill.id])

  useEffect(() => {
    if (!onClose) return undefined
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
    }
  }, [onClose])

  const subscribe = async () => {
    setSubBusy(true)
    setSubMsg(null)
    try {
      const res = await subscribeToAlerts({
        email: user.email,
        specificBills: [bill.id],
        keywords: [],
        ministries: [],
        frequency: freq,
      })
      const sent = await triggerWelcomeEmail(res)
      setSubMsg({
        kind: 'ok',
        text: sent
          ? `Subscribed to this bill. A welcome email with its summary is on its way to ${user.email}.`
          : 'Subscribed to this bill. (n8n is offline, so the welcome email is pending.)',
      })
    } catch (err) {
      const m = err?.response?.data?.error || err?.message || 'Subscribe failed.'
      setSubMsg(/already/i.test(m) ? { kind: 'ok', text: `${m} — status-change alerts stay active.` } : { kind: 'err', text: m })
    } finally {
      setSubBusy(false)
    }
  }

  const dateLabel = bill.introduction_date
    ? new Date(bill.introduction_date).toLocaleDateString('en-IN', { year: 'numeric', month: 'short', day: 'numeric' })
    : null

  const statusTone = bill.status?.toLowerCase().includes('pass')
    ? 'badge-emerald'
    : bill.status?.toLowerCase().includes('withdraw') || bill.status?.toLowerCase().includes('laps')
      ? 'badge-rose'
      : 'badge-vidhan'

  return (
    <div className="dialog-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="bill-panel glass-panel animate-slide-in" role="dialog" aria-modal="true" aria-label={`Summary for ${bill.title}`}>
        {/* Header */}
        <header className="bill-panel-header">
          <div style={{ minWidth: 0 }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginBottom: '0.45rem' }}>
              {bill.status && <span className={`badge ${statusTone}`}>{bill.status}</span>}
              {dateLabel && <span className="badge badge-slate"><CalendarDays size={11} /> {dateLabel}</span>}
            </div>
            <h2 style={{ margin: 0, fontSize: '1.15rem', lineHeight: 1.35, letterSpacing: '-0.01em' }}>{bill.title}</h2>
            {bill.ministry && <p style={{ margin: '0.3rem 0 0', fontSize: '0.8rem', color: 'var(--text-2)' }}>🏛️ {bill.ministry}</p>}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', alignItems: 'flex-end' }}>
            <button type="button" onClick={onClose} className="btn btn-ghost p-2" aria-label="Close panel"><X size={18} /></button>
            {bill.url && (
              <a href={bill.url} target="_blank" rel="noopener noreferrer" className="btn btn-ghost" style={{ fontSize: '0.72rem', padding: '0.3rem 0.6rem' }}>
                PRS <ExternalLink size={12} />
              </a>
            )}
          </div>
        </header>

        {/* Body */}
        <div className="bill-panel-body">
          {loading && (
            <div style={{ textAlign: 'center', padding: '3rem 0' }}>
              <span className="spinner-ring" style={{ width: 30, height: 30, borderWidth: 3 }} />
              <p className="empty-state-text" style={{ marginTop: '1rem' }}>Generating the plain-English summary…</p>
            </div>
          )}

          {!loading && loadError && (
            <p role="alert" style={{ color: 'var(--danger)', fontSize: '0.85rem', padding: '0.5rem 0' }}>⚠️ {loadError}</p>
          )}

          {!loading && !loadError && summary && (
            <>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginBottom: '1rem' }}>
                {summary.model_version && (
                  <span className="chip" title="Model that produced this summary">
                    <Cpu size={11} /> {summary.model_version}
                  </span>
                )}
                {summary.guardrail_applied && (
                  <span className="chip" title="Legal disclaimer appended"><ShieldCheck size={11} /> Guardrail applied</span>
                )}
                {summary.generated_at && (
                  <span className="chip">
                    {new Date(summary.generated_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}
                  </span>
                )}
              </div>
              <div className="markdown-body">
                <ReactMarkdown>{summary.summary || ''}</ReactMarkdown>
              </div>
            </>
          )}
        </div>

        {/* Footer — get alerts */}
        <footer className="bill-panel-footer">
          {user ? (
            subMsg?.kind === 'ok' ? (
              <div className="chip" style={{ color: 'var(--ok)', gap: '0.4rem' }}>✓ {subMsg.text}</div>
            ) : (
              <>
                <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', flexWrap: 'wrap' }}>
                  <label htmlFor="bp-freq" style={{ fontSize: '0.8rem', color: 'var(--text-2)' }}>Get alerts for this bill</label>
                  <select id="bp-freq" value={freq} onChange={(e) => setFreq(e.target.value)} className="premium-input" style={{ padding: '0.5rem 0.7rem', fontSize: '0.82rem' }}>
                    {FREQUENCIES.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
                  </select>
                  <button type="button" onClick={subscribe} disabled={subBusy} className="btn btn-primary" style={{ padding: '0.5rem 1rem', fontSize: '0.82rem' }}>
                    {subBusy ? <><span className="spinner-ring" style={{ width: 14, height: 14, borderWidth: 2 }} /> Subscribing…</> : <><Bell size={14} /> Subscribe</>}
                  </button>
                </div>
                {subMsg?.kind === 'err' && <p role="alert" style={{ margin: '0.5rem 0 0', color: 'var(--danger)', fontSize: '0.8rem' }}>⚠️ {subMsg.text}</p>}
                <p style={{ margin: '0.55rem 0 0', fontSize: '0.72rem', color: 'var(--text-3)' }}>
                  Alerts to <strong>{user.email}</strong> · status changes (e.g. Introduced → Passed) and updates.
                </p>
              </>
            )
          ) : (
            <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', flexWrap: 'wrap' }}>
              <button type="button" onClick={() => setSignInOpen(true)} className="btn btn-primary" style={{ padding: '0.55rem 1rem', fontSize: '0.85rem' }}>
                <Bell size={15} /> Get alerts for this bill
              </button>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-2)' }}>Sign in once — we use the email from your profile.</span>
            </div>
          )}
        </footer>
      </div>

      <SignInModal open={signInOpen} onClose={() => setSignInOpen(false)} />
    </div>
  )
}
