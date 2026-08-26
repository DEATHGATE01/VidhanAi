import { useState, useEffect } from 'react'
import { getArchitecture } from '../services/api'

// Live service inventory — GET /api/architecture.
export default function ArchitecturePage() {
  const [arch, setArch] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    getArchitecture()
      .then((data) => { if (!cancelled) setArch(data.architecture) })
      .catch((err) => { if (!cancelled) setError(err?.message || 'Failed to load architecture') })
    return () => { cancelled = true }
  }, [])

  if (error) {
    return (
      <div className="container" style={{ padding: '3rem 1rem' }}>
        <div className="glass-panel rounded-2xl" style={{ padding: '2rem', textAlign: 'center' }}>
          <p style={{ color: '#f87171', margin: '0 0 0.5rem' }}>⚠️ {error}</p>
          <p className="empty-state-text">Is the backend running on :5000?</p>
        </div>
      </div>
    )
  }

  if (!arch) {
    return (
      <div className="container" style={{ padding: '4rem 1rem', textAlign: 'center' }}>
        <span className="spinner-ring" style={{ width: 32, height: 32, borderWidth: 3 }} />
        <p className="empty-state-text" style={{ marginTop: '1rem' }}>Loading service inventory…</p>
      </div>
    )
  }

  return (
    <div className="container animate-fade-in" style={{ padding: '2rem 1rem' }}>
      <header style={{ marginBottom: '1.75rem' }}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: 800, letterSpacing: '-0.5px', margin: 0 }}>
          🏗️ Live Architecture
        </h1>
        <p style={{ color: 'var(--text-2)', fontSize: '0.85rem', margin: 0 }}>
          {arch.service} v{arch.version} · live inventory from GET /api/architecture
        </p>
      </header>

      {/* LLM backends */}
      <CardGrid heading="LLM Backends">
        {(arch.llm_backends || []).map((b) => (
          <InfoCard key={b.name} icon={b.type === 'local' ? '💻' : '☁️'} title={b.name} badge={b.tier}>
            <Meta>{b.type} · {b.status}</Meta>
          </InfoCard>
        ))}
      </CardGrid>

      {/* Data sources */}
      <CardGrid heading="Data Sources">
        {(arch.data_sources || []).map((d) => (
          <InfoCard key={d.name} icon={d.name === 'ChromaDB' ? '🧲' : d.name === 'SQLite' ? '🗄️' : '📰'} title={d.name}>
            <Meta>{d.role}</Meta>
            {d.url && (
              <a href={d.url} target="_blank" rel="noopener noreferrer" className="link" style={{ fontSize: '0.78rem', display: 'block' }}>
                {d.url}
              </a>
            )}
            {d.path && <code style={{ fontSize: '0.72rem', color: 'var(--text-2)', display: 'block' }}>{d.path}</code>}
            {d.bills_indexed != null && <Meta>{Number(d.bills_indexed).toLocaleString('en-IN')} bills indexed</Meta>}
          </InfoCard>
        ))}
      </CardGrid>

      {/* Orchestration */}
      <CardGrid heading={`Orchestration — ${arch.orchestration?.framework || ''}`}>
        {(arch.orchestration?.agents || []).map((a) => (
          <InfoCard key={a.role} icon="🧭" title={a.role}>
            <Meta>{a.responsibility}</Meta>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.5rem' }}>
              {(a.tools || []).map((t) => (
                <span key={t} className="badge badge-vidhan" style={{ fontSize: '0.68rem' }}>{t}</span>
              ))}
            </div>
          </InfoCard>
        ))}
        {arch.orchestration?.cost_model && (
          <InfoCard icon="💸" title="Cost Model">
            <Meta>{arch.orchestration.cost_model}</Meta>
          </InfoCard>
        )}
      </CardGrid>

      {/* Tools */}
      <CardGrid heading={`Specialist Tools (${(arch.tools || []).length})`}>
        {(arch.tools || []).map((t) => (
          <InfoCard key={t.name} icon={t.icon || '🔧'} title={t.name}>
            <Meta>{t.description}</Meta>
            {t.endpoint && <code style={{ fontSize: '0.72rem', color: '#60a5fa' }}>{t.endpoint}</code>}
          </InfoCard>
        ))}
      </CardGrid>
    </div>
  )
}

function CardGrid({ heading, children }) {
  return (
    <section style={{ marginBottom: '1.75rem' }} aria-label={heading}>
      <h2 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#a5b4fc', margin: '0 0 0.75rem' }}>{heading}</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(270px, 1fr))', gap: '0.85rem' }}>
        {children}
      </div>
    </section>
  )
}

function InfoCard({ icon, title, badge, children }) {
  return (
    <article className="glass-panel rounded-xl" style={{ padding: '1rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.45rem' }}>
        <span aria-hidden="true">{icon}</span>
        <strong style={{ fontSize: '0.88rem', color: 'var(--text-1)' }}>{title}</strong>
        {badge && <span className="badge badge-emerald" style={{ marginLeft: 'auto', fontSize: '0.65rem' }}>{badge}</span>}
      </div>
      {children}
    </article>
  )
}

function Meta({ children }) {
  return <p style={{ margin: '0 0 0.3rem', color: 'var(--text-2)', fontSize: '0.8rem', lineHeight: 1.55 }}>{children}</p>
}
