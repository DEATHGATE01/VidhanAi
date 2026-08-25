import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'

// Landing page content only — Header/Footer come from the App shell.
const FEATURES = [
  {
    icon: '🤖',
    title: 'Multi-Agent Research',
    description: 'CrewAI orchestrator dispatches to 7 specialist tools — bill lookup, semantic search, summarizer, fact-checker, amendment diff, citations.',
    color: '#8b5cf6',
    path: '/research',
  },
  {
    icon: '⚖️',
    title: 'Amendment Diff',
    description: 'Delta-aware legislative summarization — the proposal\'s novel research contribution. See exactly what changed between any two versions of a bill.',
    color: '#34d399',
    path: '/amendments',
  },
  {
    icon: '🔬',
    title: 'Model Playground',
    description: 'Generate a bill summary and see exactly which model produced it — full model_version metadata, honestly labelled.',
    color: '#fbbf24',
    path: '/playground',
  },
  {
    icon: '🏗️',
    title: 'Live Architecture',
    description: 'IDE-like service map of every layer — LLM backends, ChromaDB, SQLite, embeddings, guardrails, orchestration graph.',
    color: '#60a5fa',
    path: '/architecture',
  },
]

const STATS = [
  { value: '958+', label: 'Bills Indexed' },
  { value: '140+', label: 'Full-Text Bills' },
  { value: '7', label: 'AI Agents' },
  { value: '$0', label: 'Monthly Cost' },
]

export default function LandingPage() {
  return (
    <div className="animate-fade-in">
      {/* Hero */}
      <section className="container" style={{ paddingTop: '4.5rem', paddingBottom: '3rem', textAlign: 'center' }}>
        <div
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full mb-6"
          style={{ background: 'rgba(139,92,246,0.12)', border: '1px solid rgba(139,92,246,0.3)', fontSize: '0.82rem', fontWeight: 600, color: '#c4b5fd' }}
        >
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#34d399', animation: 'pulse-glow 2s infinite' }} />
          Delta-Aware Amendment Summarization · Live
        </div>

        <h1 className="font-bold tracking-tight text-white" style={{ fontSize: 'clamp(2.2rem, 5vw, 3.6rem)', lineHeight: 1.15, marginBottom: '1.25rem' }}>
          Indian Legislation,{' '}
          <span style={{ background: 'linear-gradient(90deg,#a78bfa,#60a5fa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Decoded by AI
          </span>
        </h1>

        <p style={{ color: '#94a3b8', fontSize: '1.05rem', lineHeight: 1.7, marginBottom: '2rem', maxWidth: 700, margin: '0 auto 2rem' }}>
          VidhanAI translates dense parliamentary bills into plain English using a QLoRA fine-tuned
          Llama-3.2-3B, CrewAI multi-agent orchestration, and semantic RAG over PRS India data.
          Research-grade. Free tier.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link to="/research" className="btn btn-primary" style={{ padding: '0.8rem 1.75rem', fontSize: '0.95rem' }}>
            Try Research Assistant <ArrowRight size={17} />
          </Link>
          <Link
            to="/explore"
            className="btn"
            style={{ padding: '0.8rem 1.75rem', fontSize: '0.95rem', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.12)', color: '#e2e8f0' }}
          >
            Browse Bills
          </Link>
        </div>
      </section>

      {/* Stats bar */}
      <section className="container" style={{ paddingBottom: '3.5rem' }}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4" style={{ maxWidth: 900, margin: '0 auto' }}>
          {STATS.map((s) => (
            <div key={s.label} className="text-center rounded-2xl" style={{ padding: '1.25rem 0.75rem', background: 'rgba(30,41,59,0.45)', border: '1px solid rgba(255,255,255,0.06)' }}>
              <div className="font-bold" style={{ fontSize: '1.65rem', background: 'linear-gradient(90deg,#a78bfa,#60a5fa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                {s.value}
              </div>
              <div style={{ fontSize: '0.78rem', color: '#64748b', fontWeight: 600 }}>{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="container" style={{ paddingBottom: '4rem' }}>
        <div className="grid md:grid-cols-2 gap-5" style={{ maxWidth: 980, margin: '0 auto' }}>
          {FEATURES.map((f) => (
            <Link
              key={f.title}
              to={f.path}
              className="group rounded-2xl transition-all duration-300 hover:-translate-y-1 block"
              style={{ padding: '1.5rem', background: 'rgba(30,41,59,0.45)', border: '1px solid rgba(255,255,255,0.07)' }}
            >
              <div className="flex items-center justify-center mb-4 rounded-xl" style={{ width: 46, height: 46, background: `${f.color}18`, border: `1px solid ${f.color}35`, fontSize: '1.4rem' }}>
                <span aria-hidden="true">{f.icon}</span>
              </div>
              <h3 className="text-white font-semibold text-lg mb-2">{f.title}</h3>
              <p style={{ color: '#94a3b8', fontSize: '0.88rem', lineHeight: 1.65 }}>{f.description}</p>
              <div className="flex items-center gap-1.5 mt-4 text-sm font-semibold opacity-70 group-hover:opacity-100 transition-opacity" style={{ color: f.color }}>
                Explore <ArrowRight size={15} />
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* CTA band */}
      <section className="container" style={{ paddingBottom: '4rem' }}>
        <div
          className="rounded-3xl"
          style={{
            maxWidth: 980,
            margin: '0 auto',
            padding: 'clamp(2rem, 5vw, 4rem)',
            background: 'linear-gradient(120deg, rgba(109,40,217,0.55), rgba(37,99,235,0.45))',
            border: '1px solid rgba(139,92,246,0.35)',
          }}
        >
          <h2 className="text-white font-bold tracking-tight" style={{ fontSize: 'clamp(1.5rem, 3vw, 2.2rem)', marginBottom: '0.75rem' }}>
            Ready to decode Indian legislation?
          </h2>
          <p style={{ color: '#ddd6fe', marginBottom: '1.5rem', maxWidth: 560 }}>
            Citizens, journalists, and researchers use VidhanAI to understand Parliament — grounded in source text, never fabricated.
          </p>
          <Link to="/amendments" className="btn" style={{ background: '#fff', color: '#5b21b6', fontWeight: 700, padding: '0.75rem 1.6rem' }}>
            Try the Amendment Diff <ArrowRight size={16} />
          </Link>
        </div>
      </section>
    </div>
  )
}
