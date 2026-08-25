import { useState, useRef, useEffect } from 'react'
import { runAgentResearch } from '../services/api'

const AGENT_COLOURS = {
  GuardrailAgent:     { color: '#f87171', bg: 'rgba(248,113,113,0.1)', icon: '🛡️' },
  DataServiceAgent:   { color: '#34d399', bg: 'rgba(52,211,153,0.1)', icon: '🗄️' },
  RAGServiceAgent:    { color: '#60a5fa', bg: 'rgba(96,165,250,0.1)', icon: '🔍' },
  LLMServiceAgent:    { color: '#fbbf24', bg: 'rgba(251,191,36,0.1)', icon: '🤖' },
  FactCheckerAgent:   { color: '#a78bfa', bg: 'rgba(167,139,250,0.1)', icon: '✅' },
  AmendmentDiffAgent: { color: '#22d3ee', bg: 'rgba(34,211,238,0.1)', icon: '⚖️' },
  orchestrator:       { color: '#94a3b8', bg: 'rgba(148,163,184,0.06)', icon: '⚙️' },
}

const SUGGESTIONS = [
  'What is the Digital Personal Data Protection Bill 2023 about?',
  'Explain the Telecommunications Bill 2023',
  'Find bills related to criminal law reform',
]

export default function ResearchPage() {
  const [messages, setMessages] = useState([
    {
      role: 'agent',
      text:
        "Hi — I'm the VidhanAI Researcher 🔬\n\nAsk me anything about Indian legislation and I'll ground every answer in PRS India data, ChromaDB semantic search, and the QLoRA fine-tuned Llama-3.2-3B.",
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [useLlm, setUseLlm] = useState(false)
  const [trace, setTrace] = useState([])
  const [traceOpen, setTraceOpen] = useState(true)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSubmit = async (e) => {
    e?.preventDefault()
    const question = input.trim()
    if (!question || loading) return

    setInput('')
    setMessages((m) => [...m, { role: 'user', text: question }])
    setLoading(true)
    setTrace([])

    try {
      const data = await runAgentResearch(question, 6, useLlm)
      if (data.success) {
        setMessages((m) => [...m, { role: 'agent', text: data.answer }])
        setTrace(data.trace || [])
      } else {
        setMessages((m) => [...m, { role: 'agent', text: `⚠️ ${data.error || 'Research failed. Try rephrasing.'}` }])
      }
    } catch (err) {
      setMessages((m) => [...m, { role: 'agent', text: `Network error: ${err?.message || err}. Is the backend on :5000?` }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  return (
    <div className="container" style={{ padding: '2rem 1rem' }}>
      <header style={{ marginBottom: '1.75rem' }}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: 800, letterSpacing: '-0.5px', margin: 0 }}>
          🔬 Research Assistant
        </h1>
        <p style={{ color: '#64748b', fontSize: '0.85rem', margin: 0 }}>
          Multi-agent orchestrator · PRS India · ChromaDB · QLoRA Llama-3.2-3B
        </p>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,3fr) minmax(260px,1fr)', gap: '1.25rem', alignItems: 'start' }}>
        {/* Chat panel */}
        <section
          className="glass-panel"
          style={{ borderRadius: 16, display: 'flex', flexDirection: 'column', minHeight: 520 }}
          aria-label="Research chat"
        >
          <div style={{ padding: '0.75rem 1.25rem', borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span style={{ display: 'flex', gap: '0.4rem' }}>
              {['#f87171', '#fbbf24', '#34d399'].map((c) => (
                <i key={c} style={{ width: 10, height: 10, borderRadius: '50%', background: c, opacity: 0.7 }} />
              ))}
            </span>
            <code style={{ fontSize: '0.78rem', color: '#475569' }}>vidhanai-researcher</code>
            <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <i style={{ width: 7, height: 7, borderRadius: '50%', background: '#34d399', boxShadow: '0 0 6px #34d399', animation: 'pulse-glow 2s infinite' }} />
              <b style={{ fontSize: '0.7rem', color: '#34d399', fontWeight: 600 }}>online</b>
            </span>
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            {messages.map((m, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
                {m.role === 'agent' && (
                  <span className="bot-avatar" aria-hidden="true">🤖</span>
                )}
                <div
                  className={m.role === 'user' ? 'chat-bubble chat-bubble-user' : 'chat-bubble'}
                  style={{ whiteSpace: 'pre-wrap' }}
                >
                  {m.text}
                </div>
                {!m.role && <div ref={messagesEndRef} />}
              </div>
            ))}

            {loading && (
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.6rem' }}>
                <span className="bot-avatar" aria-hidden="true">🤖</span>
                <div className="chat-bubble" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span className="spinner-ring" />
                  <span style={{ color: '#64748b', fontSize: '0.85rem' }}>Reasoning across PRS bills, ChromaDB & LoRA…</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Suggestions */}
          {messages.length <= 1 && !loading && (
            <div style={{ padding: '0 1.25rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setInput(s)}
                  className="chip"
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <form onSubmit={handleSubmit} style={{ padding: '0.85rem 1.25rem', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ display: 'flex', gap: '0.6rem' }}>
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about any Indian bill…"
                disabled={loading}
                className="premium-input"
                style={{ flex: 1, padding: '0.7rem 1rem', fontSize: '0.9rem' }}
                aria-label="Ask a question about Indian legislation"
              />
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="btn btn-primary"
                style={{ padding: '0.7rem 1.4rem', fontSize: '0.88rem' }}
              >
                {loading ? <><span className="spinner-ring" /> Asking</> : 'Ask →'}
              </button>
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.6rem', fontSize: '0.72rem', color: '#475569', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={useLlm}
                onChange={(e) => setUseLlm(e.target.checked)}
                style={{ width: 14, height: 14, accentColor: '#8b5cf6' }}
              />
              Use CrewAI LLM planner (slower; default deterministic rule-based)
            </label>
          </form>
        </section>

        {/* Agent trace panel */}
        <aside className="glass-panel" style={{ borderRadius: 16, overflow: 'hidden' }} aria-label="Agent trace">
          <button
            type="button"
            onClick={() => setTraceOpen(!traceOpen)}
            aria-expanded={traceOpen}
            className="w-full"
            style={{
              padding: '0.75rem 1rem',
              borderBottom: '1px solid rgba(255,255,255,0.05)',
              background: 'transparent',
              borderLeft: 'none',
              borderRight: 'none',
              borderTop: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <span style={{ textAlign: 'left' }}>
              <strong style={{ display: 'block', fontSize: '0.85rem', color: '#cbd5e1' }}>Agent Trace</strong>
              <small style={{ fontSize: '0.68rem', color: '#475569' }}>{trace.length > 0 ? `${trace.length} steps` : 'awaiting query'}</small>
            </span>
            <span style={{ color: '#475569', fontSize: '0.8rem', transform: traceOpen ? 'rotate(0deg)' : 'rotate(-90deg)', transition: 'transform 0.2s' }}>▼</span>
          </button>

          {traceOpen && (
            <div style={{ padding: '0.85rem', maxHeight: 460, overflowY: 'auto' }}>
              {trace.length === 0 ? (
                <p style={{ textAlign: 'center', padding: '2rem 0.5rem', color: '#334155', fontSize: '0.78rem', margin: 0 }}>
                  ⚙️<br />Send a question to see multi-agent steps here
                </p>
              ) : (
                <ol style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                  {trace.map((step, i) => {
                    const meta = AGENT_COLOURS[step.agent] || AGENT_COLOURS.orchestrator
                    return (
                      <li
                        key={i}
                        style={{
                          marginBottom: '0.75rem',
                          borderLeft: `2px solid ${meta.color}`,
                          paddingLeft: '0.75rem',
                          animation: 'fade-in-up 0.3s ease-out both',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.2rem' }}>
                          <span aria-hidden="true">{meta.icon}</span>
                          <strong style={{ fontSize: '0.72rem', color: meta.color }}>{step.agent || 'Agent'}</strong>
                          <span style={{ fontSize: '0.65rem', color: '#334155', marginLeft: 'auto' }}>step {i + 1}</span>
                        </div>
                        <pre
                          className="trace-output"
                          style={{
                            margin: 0,
                            maxHeight: 140,
                            overflowY: 'auto',
                            whiteSpace: 'pre-wrap',
                            borderColor: `${meta.color}22`,
                            background: meta.bg,
                          }}
                        >
                          {step.output}
                        </pre>
                      </li>
                    )
                  })}
                </ol>
              )}
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}
