import { useState, useRef, useEffect, Fragment } from 'react'
import { ArrowUp, Scale, Bot, FileText } from 'lucide-react'
import { runAgentResearch } from '../services/api'
import Vid from '../components/Vid'

const SUGGESTIONS = [
  'What is the Digital Personal Data Protection Bill 2023 about?',
  'Explain the Telecommunications Bill 2023',
  'Find bills related to criminal law reform',
  'Which bills changed recently?',
  'What did the Finance Bill amend?',
  'Summarize the latest GST amendment',
]

// KPI cards — the "RIGHT NOW" column. Static product stats (real numbers from
// the landing page), adapted to the Brik dashboard reference.
const KPIS = [
  { icon: Scale, chipBg: 'rgba(99,102,241,0.12)', chipColor: 'var(--accent)', value: '958+', label: 'Bills indexed', sub: 'from PRS BillTrack', purple: true },
  { icon: Bot, chipBg: 'rgba(251,191,36,0.16)', chipColor: '#b45309', value: '7', label: 'AI agents', sub: 'research pipeline live', purple: false },
  { icon: FileText, chipBg: 'rgba(251,191,36,0.16)', chipColor: '#b45309', value: '140+', label: 'Full-text bills', sub: 'ready for semantic search', purple: false },
]

// The 4-stage processing pipeline — what the AI tells the user it is doing.
// Mirrors the Brik "Grouping RTOs by region" pattern: contextual operation
// messages instead of a generic spinner.
const STAGES = [
  'Understanding your question',
  'Searching PRS bills & ChromaDB',
  'Cross-checking facts & sources',
  'Writing your answer',
]

// Pull source URLs out of the agent's answer so they render as citation chips.
function extractUrls(text) {
  const found = (text || '').match(/https?:\/\/[^\s)\]'"<>]+/g) || []
  return [...new Set(found.map((u) => u.replace(/[.,;:]+$/, '')))]
}

function domainOf(url) {
  let label = url.replace(/^https?:\/\//, '').split('/')[0]
  if (label.startsWith('www.')) label = label.slice(4)
  return label
}

function greetingPrefix() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning,'
  if (h < 17) return 'Good afternoon,'
  return 'Good evening,'
}

const QUERY_BUBBLE = {
  background: 'var(--accent-soft)',
  border: '1px solid rgba(99,102,241,0.25)',
  color: 'var(--text-1)',
  padding: '0.6rem 1rem',
  borderRadius: 16,
  fontSize: '0.9rem',
  maxWidth: '72%',
}

export default function ResearchPage() {
  const [input, setInput] = useState('')
  const [useLlm, setUseLlm] = useState(false)
  // IDLE → PROCESSING → RESULT — the AI-analysis state machine (Brik reference).
  const [phase, setPhase] = useState('idle')
  const [activeQuery, setActiveQuery] = useState('')
  const [answer, setAnswer] = useState('')
  const [progress, setProgress] = useState(0)
  const inputRef = useRef(null)

  const loading = phase === 'processing'

  useEffect(() => {
    if (phase !== 'processing') return
    setProgress(1)
    const iv = setInterval(() => setProgress((p) => Math.min(p + 1, 4)), 2600)
    return () => clearInterval(iv)
  }, [phase])

  const currentOp = STAGES[Math.max(0, Math.min(progress - 1, STAGES.length - 1))]

  const send = async (question) => {
    const q = (question ?? input).trim()
    if (!q || loading) return
    setInput('')
    setActiveQuery(q)
    setAnswer('')
    setPhase('processing')
    try {
      const data = await runAgentResearch(q, 6, useLlm)
      setAnswer(data.success ? data.answer : `⚠️ ${data.error || 'Research failed. Try rephrasing.'}`)
    } catch (err) {
      setAnswer(`Network error: ${err?.message || err}. Is the backend on :5000?`)
    } finally {
      setPhase('result')
      inputRef.current?.focus()
    }
  }

  const onSubmit = (e) => {
    e?.preventDefault()
    send()
  }

  const resultUrls = phase === 'result' ? extractUrls(answer) : []

  return (
    <div className="ask-page" aria-label="Ask VidhanAI chat">
      {/* Header — title + subtitle, controls on the right */}
      <header style={{ padding: '1.5rem 2rem 0.9rem', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.35rem', fontWeight: 800, letterSpacing: '-0.02em', margin: 0 }}>Ask VidhanAI</h1>
          <p style={{ color: 'var(--text-2)', fontSize: '0.85rem', margin: '0.15rem 0 0' }}>
            Ask anything about Indian legislation, in plain words
          </p>
        </div>
        <label style={{ display: 'inline-flex', alignItems: 'center', gap: '0.45rem', fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-2)', cursor: 'pointer', flexShrink: 0, background: 'var(--chat-card)', border: '1px solid var(--border)', borderRadius: 999, padding: '0.45rem 0.9rem', boxShadow: 'var(--shadow-sm)' }}>
          <input
            type="checkbox"
            checked={useLlm}
            onChange={(e) => setUseLlm(e.target.checked)}
            style={{ width: 13, height: 13, accentColor: 'var(--accent)' }}
          />
          CrewAI LLM planner
        </label>
      </header>

      {/* Body — left AI workspace + right KPI column */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
        <div style={{ pointerEvents: 'none', position: 'absolute', inset: 0, background: 'var(--chat-glow)' }} aria-hidden="true" />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
          <div style={{ position: 'relative', flex: 1, overflowY: 'auto', padding: '1rem 2rem 1.5rem' }}>

            {phase === 'idle' && (
              /* Greeting — the Brik-style center-left hero */
              <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', alignItems: 'flex-start', justifyContent: 'center', minHeight: '100%', padding: '0.5rem 0' }}>
                <div style={{ position: 'relative', marginBottom: '1.15rem' }}>
                  <Vid size={112} expression="cheerful" lively />
                  <div aria-hidden="true" style={{ position: 'absolute', left: '50%', transform: 'translateX(-50%)', bottom: -12, width: 88, height: 16, borderRadius: '50%', background: 'var(--orb-shadow)', filter: 'blur(5px)' }} />
                </div>
                <h2 style={{ fontSize: 'clamp(1.8rem, 3.6vw, 2.5rem)', fontWeight: 800, letterSpacing: '-0.03em', lineHeight: 1.14, margin: '0 0 0.7rem' }}>
                  {greetingPrefix()}
                  <br />
                  VidhanAI is ready for
                  <br />
                  Parliament.
                </h2>
                <p style={{ color: 'var(--text-2)', fontSize: '1rem', lineHeight: 1.65, margin: 0, maxWidth: '46ch' }}>
                  Ask about bills, amendments, alerts or search — in your own words.
                </p>
              </div>
            )}

            {phase === 'processing' && (
              /* AI processing state — query bubble + progress pipeline + mascot */
              <div style={{ position: 'relative', display: 'flex', flexDirection: 'column' }}>
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '1rem' }}>
                  <div style={QUERY_BUBBLE}>{activeQuery}</div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem', paddingTop: '1.25rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', width: 'min(380px, 90%)' }}>
                    {STAGES.map((_, sIdx) => {
                      const s = sIdx + 1
                      const done = s <= progress
                      return (
                        <Fragment key={s}>
                          {sIdx > 0 && (
                            <div style={{ flex: 1, height: 2, borderRadius: 1, background: done ? 'var(--accent)' : 'var(--line-2)', transition: 'background .3s ease' }} />
                          )}
                          <div
                            style={{
                              width: 16, height: 16, borderRadius: '50%', flexShrink: 0,
                              background: done ? 'var(--accent)' : 'transparent',
                              border: done ? 'none' : '2px solid var(--line-2)',
                              boxShadow: done ? '0 0 0 3px var(--accent-soft)' : 'none',
                              transition: 'all .3s ease',
                            }}
                          />
                        </Fragment>
                      )
                    })}
                  </div>
                  <p style={{ color: 'var(--text-2)', fontSize: '0.92rem', fontWeight: 600, margin: 0 }}>{currentOp}</p>
                  <div style={{ position: 'relative', marginTop: '0.75rem' }}>
                    <Vid size={80} expression="cheerful" walking />
                    <div aria-hidden="true" style={{ position: 'absolute', left: '50%', transform: 'translateX(-50%)', bottom: -10, width: 72, height: 14, borderRadius: '50%', background: 'var(--orb-shadow)', filter: 'blur(4px)' }} />
                  </div>
                </div>
              </div>
            )}

            {phase === 'result' && (
              /* Result — query bubble + answer insight card */
              <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <div style={QUERY_BUBBLE}>{activeQuery}</div>
                </div>
                <div className="card" style={{ padding: '1.25rem 1.4rem', background: 'var(--chat-card)', boxShadow: 'var(--shadow-sm)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', marginBottom: '0.75rem' }}>
                    <Vid size={30} lively />
                    <span style={{ fontWeight: 700, fontSize: '0.88rem', color: 'var(--accent-ink)' }}>VidhanAI</span>
                  </div>
                  <div style={{ whiteSpace: 'pre-wrap', fontSize: '0.95rem', lineHeight: 1.75, color: 'var(--text-1)' }}>{answer}</div>
                  {resultUrls.length > 0 && (
                    <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginTop: '0.9rem' }}>
                      {resultUrls.slice(0, 4).map((u) => (
                        <a
                          key={u}
                          href={u}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            display: 'inline-flex', alignItems: 'center', gap: '0.25rem',
                            fontSize: '0.72rem', fontWeight: 600,
                            color: 'var(--accent-2)', background: 'var(--accent-soft)',
                            border: '1px solid rgba(99,102,241,0.25)', borderRadius: 999,
                            padding: '0.2rem 0.6rem', textDecoration: 'none',
                          }}
                        >
                          {domainOf(u)} <span style={{ opacity: 0.6 }}>↗</span>
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right KPI column */}
        <aside className="ask-kpi" style={{ flexShrink: 0, padding: '1.25rem 2rem 1.5rem 2.75rem', overflowY: 'auto' }} aria-label="Key metrics">
          <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.66rem', letterSpacing: '0.16em', textTransform: 'uppercase', color: 'var(--text-3)', margin: '0 0 0.85rem' }}>
            Right now
          </p>
          {KPIS.map((k) => (
            <div
              key={k.label}
              className="card"
              style={{ padding: '1rem 1.1rem', marginBottom: '0.75rem', display: 'flex', gap: '0.85rem', alignItems: 'center', boxShadow: 'var(--shadow-sm)', background: 'var(--chat-card)' }}
            >
              <span
                style={{
                  width: 42, height: 42, borderRadius: 12, background: k.chipBg, color: k.chipColor,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}
                aria-hidden="true"
              >
                <k.icon size={19} />
              </span>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: '1.4rem', fontWeight: 800, letterSpacing: '-0.02em', lineHeight: 1.1, color: k.purple ? 'var(--accent-ink)' : 'var(--text-1)' }}>
                  {k.value}
                </div>
                <div style={{ fontSize: '0.78rem', fontWeight: 600, marginTop: '0.15rem' }}>{k.label}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-3)', marginTop: '0.1rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{k.sub}</div>
              </div>
            </div>
          ))}
          <div className="card" style={{ padding: '0.62rem 0.9rem', borderRadius: 999, fontSize: '0.72rem', color: 'var(--text-2)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', background: 'var(--chat-card)' }}>
            <b style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-ink)', fontSize: '0.64rem', letterSpacing: '0.14em', marginRight: '0.45rem' }}>TODAY</b>
            958 bills · 7 agents · 140+ full-text
          </div>
        </aside>
      </div>

      {/* Input + suggestions — anchored at the bottom of the workspace */}
      <div style={{ padding: '1rem 2rem 1.75rem' }}>
        <form onSubmit={onSubmit} style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about bills, amendments, alerts or search…"
            disabled={loading}
            className="premium-input"
            style={{ flex: 1, padding: '0.95rem 1.25rem', fontSize: '0.95rem', borderRadius: 18, background: 'var(--chat-card)', borderColor: 'rgba(99,102,241,0.45)', boxShadow: '0 10px 28px rgba(99,102,241,0.12)' }}
            aria-label="Ask a question about Indian legislation"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="btn btn-primary"
            style={{ padding: '0.95rem 1.5rem', borderRadius: 18, fontSize: '0.92rem', fontWeight: 700, flexShrink: 0 }}
          >
            {loading ? <><span className="spinner-ring" /> Asking</> : <><span>Ask</span> <ArrowUp size={17} /></>}
          </button>
        </form>
        {phase !== 'processing' && (
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.75rem' }}>
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => send(s)}
                className="chip"
                style={{ fontSize: '0.76rem', padding: '0.4rem 0.9rem', background: 'var(--chat-card)' }}
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
