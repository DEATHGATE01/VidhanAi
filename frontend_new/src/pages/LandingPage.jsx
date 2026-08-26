import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'

const FEATURES = [
  { icon: '🤖', chip: 'icon-purple', title: 'Multi-Agent Research', description: 'CrewAI orchestrator dispatches 7 specialist tools — bill lookup, semantic search, summarizer, fact-checker, amendment diff, citations.', path: '/research' },
  { icon: '⚖️', chip: 'icon-green', title: 'Amendment Diff', description: 'Delta-aware summarization — the novel research contribution. See exactly what changed between any two versions of a bill.', path: '/amendments' },
  { icon: '🔔', chip: 'icon-blue', title: 'Smart Alerts', description: 'Track a bill or follow a topic. Welcome email with the AI summary, then alerts when bills appear or change.', path: '/alerts' },
  { icon: '🔬', chip: 'icon-amber', title: 'Model Playground', description: 'Generate bill summaries and audit exactly which model produced them — every result carries its model_version.', path: '/playground' },
]

const STATS = [
  { value: '958+', label: 'Bills Indexed', icon: '📄', chip: 'icon-blue' },
  { value: '140+', label: 'Full-Text Bills', icon: '📑', chip: 'icon-purple' },
  { value: '7', label: 'AI Agents', icon: '🤖', chip: 'icon-amber' },
  { value: '$0', label: 'Monthly Cost', icon: '💸', chip: 'icon-green' },
]

export default function LandingPage() {
  return (
    <div className="animate-fade-in">
      {/* Hero */}
      <section className="container" style={{ paddingTop: '4.5rem', paddingBottom: '3rem', textAlign: 'center' }}>
        <span className="badge badge-vidhan" style={{ fontSize: '0.78rem', padding: '0.35rem 0.9rem' }}>
          Delta-Aware Amendment Summarization · Live
        </span>
        <h1 style={{ fontSize: 'clamp(2.2rem, 5vw, 3.4rem)', fontWeight: 800, letterSpacing: '-0.03em', lineHeight: 1.12, margin: '1rem 0 1.1rem' }}>
          Indian Legislation,{' '}
          <span style={{ color: '#818cf8' }}>Decoded by AI</span>
        </h1>
        <p style={{ color: 'var(--text-2)', fontSize: '1.02rem', lineHeight: 1.7, maxWidth: 640, margin: '0 auto 2rem' }}>
          VidhanAI translates dense parliamentary bills into plain English using a QLoRA fine-tuned
          Llama-3.2-3B, CrewAI multi-agent orchestration, and semantic RAG over PRS India data.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link to="/research" className="btn btn-primary" style={{ padding: '0.75rem 1.6rem' }}>
            Try Research Assistant <ArrowRight size={16} />
          </Link>
          <Link to="/explore" className="btn btn-secondary" style={{ padding: '0.75rem 1.6rem' }}>
            Browse Bills
          </Link>
        </div>
      </section>

      {/* KPI stats row — reference design's stat cards */}
      <section className="container" style={{ paddingBottom: '3rem' }}>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {STATS.map((s) => (
            <div key={s.label} className="stat-card">
              <span className={`icon-chip ${s.chip}`} aria-hidden="true">{s.icon}</span>
              <div>
                <div style={{ fontSize: '1.45rem', fontWeight: 800, letterSpacing: '-0.02em' }}>{s.value}</div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-2)', fontWeight: 500 }}>{s.label}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="container" style={{ paddingBottom: '3.5rem' }}>
        <div className="grid md:grid-cols-2 gap-4">
          {FEATURES.map((f) => (
            <Link
              key={f.title}
              to={f.path}
              className="card card-hover block group"
              style={{ padding: '1.4rem' }}
            >
              <div className="flex items-start gap-3.5">
                <span className={`icon-chip ${f.chip}`} aria-hidden="true">{f.icon}</span>
                <div>
                  <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: '0 0 0.35rem' }}>{f.title}</h3>
                  <p style={{ color: 'var(--text-2)', fontSize: '0.86rem', lineHeight: 1.6, margin: 0 }}>{f.description}</p>
                  <span className="inline-flex items-center gap-1 mt-3 text-sm font-semibold" style={{ color: '#818cf8' }}>
                    Explore <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="container" style={{ paddingBottom: '3rem' }}>
        <div className="card" style={{ padding: 'clamp(1.75rem, 4vw, 3rem)', textAlign: 'center', background: 'linear-gradient(135deg, rgba(99,102,241,0.16), rgba(99,102,241,0.08))' }}>
          <h2 style={{ fontSize: 'clamp(1.35rem, 3vw, 1.9rem)', fontWeight: 800, letterSpacing: '-0.02em', margin: '0 0 0.6rem' }}>
            Ready to decode Indian legislation?
          </h2>
          <p style={{ color: 'var(--text-2)', marginBottom: '1.4rem' }}>
            Grounded in source text, never fabricated. Free-tier architecture.
          </p>
          <Link to="/alerts" className="btn btn-primary" style={{ padding: '0.7rem 1.5rem' }}>
            Track a bill <ArrowRight size={15} />
          </Link>
        </div>
      </section>
    </div>
  )
}
