import { useState, useEffect } from 'react'
import { Link, useParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import { ArrowLeft, ExternalLink, FileText, Scale, CheckCircle, AlertCircle, Info, ChevronDown, ChevronUp } from 'lucide-react'
import { getActById, getActSummary, getBillLifecycle } from '../services/api'
import LifecycleTimeline from '../components/LifecycleTimeline'

export default function ActDetailPage() {
  const { actId } = useParams()
  const [act, setAct] = useState(null)
  const [billLifecycles, setBillLifecycles] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expandedBills, setExpandedBills] = useState(new Set())
  const [actSummary, setActSummary] = useState(null)
  const [actSummaryErr, setActSummaryErr] = useState('')
  // "How it became law": the API assembles this from the linked bills' sourced
  // PRS events plus the Act's own assent/commencement. It was on file all along;
  // the page simply never received it.
  const [timeline, setTimeline] = useState([])

  // "Statute history": the earlier law this Act amends, read from the Act's own text
  // ("further to amend the Andhra Pradesh Reorganisation Act, 2014 ... in section 5").
  // The timeline above only covers the bill that produced THIS Act — an amending Act
  // is one chapter of a longer statute, and this is the rest of it that we can source.
  const [statuteLineage, setStatuteLineage] = useState([])
  const [lineageNote, setLineageNote] = useState('')

  // Fetch act on mount
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    getActById(actId)
      .then((response) => {
        if (!cancelled) {
          if (response.success && response.act) {
            setAct(response.act)
            setTimeline(response.act.timeline || [])
            setStatuteLineage(response.act.amends || [])
            setLineageNote(response.act.amends_note || '')
            // Fetch lifecycle for each linked bill
            const bills = response.act.bills || []
            bills.forEach((bill) => {
              if (bill.id) {
                getBillLifecycle(bill.id)
                  .then((lifeRes) => {
                    if (!cancelled && lifeRes.success) {
                      setBillLifecycles((prev) => ({
                        ...prev,
                        [bill.id]: lifeRes.events || [],
                      }))
                    }
                  })
                  .catch(() => {
                    // Silently fail - lifecycle is optional enhancement
                  })
              }
            })
          } else {
            setError('Act not found')
          }
        }
      })
      .catch((err) => {
        if (!cancelled) {
          if (err?.response?.status === 404) {
            setError('Act not found')
          } else {
            setError(err?.message || 'Failed to load act')
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [actId])

  const toggleBillExpand = (billId) => {
    setExpandedBills((prev) => {
      const next = new Set(prev)
      if (next.has(billId)) next.delete(billId)
      else next.add(billId)
      return next
    })
  }

  // The Act's own summary. Cache-through on the server: first open may generate
  // (a few seconds), later opens are instant. A failure states the reason rather
  // than showing an invented summary.
  useEffect(() => {
    let cancelled = false
    setActSummary(null)
    setActSummaryErr('')
    getActSummary(actId)
      .then((data) => {
        if (cancelled) return
        if (data?.success && data.summary) setActSummary(data.summary)
        else setActSummaryErr(data?.error || 'No summary is available for this Act yet.')
      })
      .catch((err) => {
        if (!cancelled) setActSummaryErr(err?.response?.data?.error || err?.message || 'Could not load the Act summary.')
      })
    return () => { cancelled = true }
  }, [actId])

  const formatDate = (dateStr) => {
    if (!dateStr) return '—'
    try {
      return new Date(dateStr).toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    } catch {
      return dateStr
    }
  }

  const getStatusBadgeClass = (status) => {
    if (!status) return 'badge-slate'
    const s = status.toLowerCase()
    if (s === 'active' || s === 'passed' || s === 'assented' || s === 'in_force') return 'badge-emerald'
    if (s === 'repealed' || s === 'withdrawn' || s === 'lapsed') return 'badge-rose'
    if (s === 'pending' || s === 'introduced' || s === 'referred') return 'badge-amber'
    return 'badge-slate'
  }

  // Human labels for the status codes the API stores ('in_force' -> 'In force').
  const STATUS_LABELS = { in_force: 'In force', repealed: 'Repealed', spent: 'Spent', unknown: 'Unknown' }
  const statusLabel = (s) => STATUS_LABELS[(s || '').toLowerCase()] || s

  // Which authority a value came from. The header used to hardcode "Source
  // (PRS)" for every act, which mislabelled India Code URLs as PRS ones.
  // Includes the scrapers' internal slugs, which the lifecycle timeline reports
  // (`prs_billtrack`) — the page must never print a raw slug at the user.
  const SOURCE_LABELS = {
    prs: 'PRS India',
    prs_acts: 'PRS India',
    prs_act_pdf: 'PRS India (the Act PDF)',
    prs_billtrack: 'PRS India',
    indiacode: 'India Code',
    india_code: 'India Code',
    egazette: 'eGazette',
    wikipedia: 'Wikipedia',
  }
  const sourceLabel = (s) => SOURCE_LABELS[s] || (s ? String(s).replace(/_/g, ' ') : 'source')

  // A missing detail must never render as a bare "not published": the backend
  // stores which sources were searched for it and when (acts.lookup_note /
  // details_checked_at), so the field says a search happened and the trail is
  // shown under the field row. See docs/CTO_V2.md §2.
  const MissingDetail = () => (
    <span
      style={{ color: 'var(--text-3)', fontStyle: 'italic' }}
      title={act?.lookup_note || 'No source was reachable'}
    >
      Not found{act?.details_checked_at ? ' — sources checked' : ''}
    </span>
  )

  const missingDetails = [
    !act?.act_number && 'Act number',
    !(act?.status && act.status !== 'unknown') && 'in-force status',
    // A commencement PROVISION ("by notification") is a sourced answer, so it is
    // only missing when the Act says nothing at all about commencement.
    !act?.commencement_date && !act?.commencement_note && 'commencement',
  ].filter(Boolean)

  if (loading) {
    return (
      <div className="container animate-fade-in" style={{ padding: '2rem 1rem' }}>
        <div style={{ textAlign: 'center', padding: '4rem' }}>
          <span className="spinner-ring" style={{ width: 32, height: 32, borderWidth: 3 }} />
          <p className="empty-state-text" style={{ marginTop: '1rem' }}>Loading act…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container animate-fade-in" style={{ padding: '2rem 1rem' }}>
        <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center', borderRadius: 16, maxWidth: 600, margin: '0 auto' }}>
          {error === 'Act not found' ? (
            <>
              <AlertCircle size={48} style={{ margin: '0 auto 1rem', color: 'var(--warn)' }} />
              <h2 style={{ margin: '0 0 0.5rem', fontSize: '1.3rem' }}>Act Not Found</h2>
              <p className="empty-state-text" style={{ marginBottom: '1.5rem' }}>
                No act exists with the ID <code style={{ fontFamily: 'var(--font-mono)', background: 'var(--hover)', padding: '0.1rem 0.4rem', borderRadius: 4 }}>{actId}</code>
              </p>
            </>
          ) : (
            <>
              <AlertCircle size={48} style={{ margin: '0 auto 1rem', color: 'var(--danger)' }} />
              <h2 style={{ margin: '0 0 0.5rem', fontSize: '1.3rem' }}>Failed to Load Act</h2>
              <p style={{ color: 'var(--danger)', margin: '0 0 0.5rem' }}>⚠️ {error}</p>
              <p className="empty-state-text" style={{ marginBottom: '1.5rem' }}>Is the backend running on :5000?</p>
            </>
          )}
          <Link to="/acts" className="btn btn-primary" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
            <ArrowLeft size={16} /> Back to Acts
          </Link>
        </div>
      </div>
    )
  }

  if (!act) {
    return null
  }

  return (
    <div className="container animate-fade-in" style={{ padding: '2rem 1rem', maxWidth: '1000px' }}>
      {/* Back link */}
      <Link
        to="/acts"
        className="btn btn-ghost"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.4rem',
          marginBottom: '1.5rem',
          fontSize: '0.85rem',
          padding: '0.4rem 0.8rem',
        }}
      >
        <ArrowLeft size={16} /> Back to Acts
      </Link>

      {/* Act Header */}
      <div className="card card-hover" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'flex-start', marginBottom: '1rem' }}>
          <div style={{ flex: 1, minWidth: 280 }}>
            <h1 className="page-title" style={{ margin: '0 0 0.5rem', lineHeight: 1.3 }}>
              {act.title || act.short_title || act.act_id}
            </h1>
            {act.short_title && act.short_title !== act.title && (
              <p style={{ color: 'var(--text-2)', fontSize: '0.95rem', margin: 0 }}>
                {act.short_title}
              </p>
            )}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
            <Scale size={24} style={{ color: 'var(--accent)' }} />
            <span className="badge badge-vidhan" style={{ fontSize: '0.75rem' }}>
              {act.act_id}
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem', fontSize: '0.88rem', color: 'var(--text-2)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ color: 'var(--text-3)' }}>Year:</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 500, color: 'var(--text-1)' }}>
              {act.year || '—'}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ color: 'var(--text-3)' }}>Act No.:</span>
            {act.act_number ? (
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 500, color: 'var(--text-1)' }}>
                {act.act_number}
              </span>
            ) : act.bill_number ? (
              /* The gazetted Act number is unpublished, but we hold the Bill number
                 it came from — the same law under its earlier name. Showing that is
                 worth far more than "not found", and it is labelled as what it is. */
              <span style={{ fontSize: '0.8rem', color: 'var(--text-2)' }}>
                not yet published; this Act came from{' '}
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-1)' }}>
                  Bill No. {act.bill_number}
                </span>
              </span>
            ) : (
              <MissingDetail />
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ color: 'var(--text-3)' }}>Status:</span>
            {act.status && act.status !== 'unknown' ? (
              <>
                <span className={getStatusBadgeClass(act.status)}>
                  {statusLabel(act.status)}
                </span>
                {act.status_basis && (
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-3)' }}
                        title={act.status_basis}>
                    derived — see sources checked
                  </span>
                )}
              </>
            ) : (
              <MissingDetail />
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ color: 'var(--text-3)' }}>Assented:</span>
            {act.assent_date ? (
              formatDate(act.assent_date)
            ) : (
              <MissingDetail />
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ color: 'var(--text-3)' }}>Commenced:</span>
            {act.commencement_date ? (
              formatDate(act.commencement_date)
            ) : act.commencement_note ? (
              /* Most Indian Acts fix no date and commence by notification. That is
                 a sourced fact from the Act's own text, not a missing value, so it
                 is shown here rather than "not found". */
              <span style={{ fontSize: '0.8rem', color: 'var(--text-2)' }} title={act.commencement_note}>
                {act.commencement_note}
              </span>
            ) : (
              <MissingDetail />
            )}
          </div>
        </div>

        {/* Where these details came from — or where we looked and did not find
            them. Makes "unknown" auditable instead of an excuse. */}
        {(missingDetails.length > 0 || act.evidence || act.lookup_note) && (
          <details style={{ marginTop: '0.9rem', fontSize: '0.82rem', color: 'var(--text-3)' }}>
            <summary style={{ cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
              <Info size={14} />
              {missingDetails.length > 0
                ? `${missingDetails.join(', ')} not published by PRS — every source checked is listed below`
                : `Sourced from ${act.source ? sourceLabel(act.source) : 'the source'}`}
            </summary>
            <div style={{ marginTop: '0.5rem', lineHeight: 1.55, maxWidth: '70ch' }}>
              {act.details_checked_at && (
                <p style={{ margin: '0 0 0.35rem' }}>
                  <strong style={{ color: 'var(--text-2)' }}>Last checked:</strong>{' '}
                  {formatDate(act.details_checked_at)}
                </p>
              )}
              {act.lookup_note && (
                <p style={{ margin: '0 0 0.35rem', whiteSpace: 'pre-wrap' }}>
                  <strong style={{ color: 'var(--text-2)' }}>Sources consulted:</strong>{' '}
                  {act.lookup_note}
                </p>
              )}
              {act.evidence && (
                <p style={{ margin: 0 }}>
                  <strong style={{ color: 'var(--text-2)' }}>Evidence for the values above:</strong>{' '}
                  {act.evidence}
                </p>
              )}
            </div>
          </details>
        )}

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '1rem' }}>
          {act.pdf_url && (
            <a
              href={act.pdf_url}
              target="_blank"
              rel="noreferrer"
              className="btn btn-secondary"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.82rem' }}
            >
              <FileText size={16} /> Act PDF
            </a>
          )}
          {act.source_url && (
            <a
              href={act.source_url}
              target="_blank"
              rel="noreferrer"
              className="btn btn-ghost"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.82rem' }}
            >
              <ExternalLink size={16} /> Source ({sourceLabel(act.source)})
            </a>
          )}
        </div>
      </div>

      {/* How it became law — sourced PRS events from the linked bills plus the
          Act's own assent and commencement. Undated steps say so; estimates are
          labelled rather than quietly smoothed over. */}
      {timeline.length > 0 && (
        <section style={{ marginBottom: '2rem' }}>
          <div className="card" style={{ padding: '1.5rem' }}>
            <h2 style={{ margin: '0 0 0.9rem', fontSize: '1.05rem', fontWeight: 600 }}>
              How it became law
            </h2>
            <ol style={{ margin: 0, padding: 0, listStyle: 'none' }}>
              {timeline.map((step, i) => (
                <li key={`${step.event}-${step.date || 'nd'}-${i}`}
                    style={{ display: 'flex', gap: '0.85rem', paddingBottom: '0.65rem' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem',
                                 color: 'var(--text-2)', minWidth: '7.5rem' }}>
                    {step.date ? formatDate(step.date) : 'date not stated'}
                  </span>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-1)' }}>
                    {step.label || step.event}
                    {step.house ? <span style={{ color: 'var(--text-3)' }}> · {step.house}</span> : null}
                    {step.is_estimated ? <span style={{ color: 'var(--text-3)' }}> · estimated</span> : null}
                    <span style={{ display: 'block', fontSize: '0.73rem', color: 'var(--text-3)' }}>
                      {step.stage === 'act'
                        ? "from the Act's own document"
                        : `from ${sourceLabel(step.source)}`}
                      {step.notes && step.stage === 'act' ? ` — ${step.notes}` : ''}
                    </span>
                  </span>
                </li>
              ))}
            </ol>
          </div>
        </section>
      )}

      {/* Statute history — the longer story the timeline above cannot show. An
          amending Act says in its own text which earlier law it changes, so that
          parent statute is a sourced chapter even though we do not hold its page.
          Shown only when there is something sourced to say. */}
      {(statuteLineage.length > 0 || /amend|repeal/i.test(act?.title || '')) && (
        <section style={{ marginBottom: '2rem' }}>
          <div className="card" style={{ padding: '1.5rem' }}>
            <h2 style={{ margin: '0 0 0.6rem', fontSize: '1.05rem', fontWeight: 600 }}>
              Statute history
            </h2>
            {statuteLineage.length > 0 ? (
              <>
                <p style={{ margin: '0 0 0.9rem', fontSize: '0.85rem', color: 'var(--text-2)' }}>
                  The timeline above is this Act's own passage. This Act also changes an earlier
                  law, so it is the latest chapter of a longer story — the chapters before it are
                  read from India Code's catalogue and listed below.
                </p>
                {statuteLineage.map((parent, i) => (
                  <div key={`${parent.title}-${parent.year}-${i}`}
                       style={{ padding: '0.7rem 0',
                                borderTop: i ? '1px solid var(--border, rgba(0,0,0,0.08))' : 'none' }}>
                    <div style={{ fontSize: '0.92rem', fontWeight: 600, color: 'var(--text-1)' }}>
                      amends {parent.title}, {parent.year}
                    </div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-2)', marginTop: '0.2rem' }}>
                      {parent.cited_act_number ? `No. ${parent.cited_act_number} · ` : ''}
                      {parent.sections && parent.sections.length
                        ? `section${parent.sections.length > 1 ? 's' : ''} ${parent.sections.join(', ')}`
                        : 'sections not named in the pages read'}
                      {' · '}
                      <a href={`https://indiacode.gov.in/search?query=${encodeURIComponent(`${parent.title}, ${parent.year}`)}`}
                         target="_blank" rel="noreferrer" style={{ color: 'var(--accent, #2563eb)' }}>
                        its own history on India Code
                      </a>
                    </div>
                    <div style={{ fontSize: '0.73rem', color: 'var(--text-3)', marginTop: '0.2rem' }}>
                      {parent.evidence}
                    </div>
                    {/* The parent's own chapters. Read from India Code's catalogue, one
                        link per instrument, and this Act shown last so the chain reads as
                        a history rather than a list. */}
                    {((parent.history && (parent.history.entries || []).length > 0)
                      || (parent.tracked_acts || []).length > 0) && (
                      <div style={{ marginTop: '0.55rem', paddingLeft: '0.8rem',
                                    borderLeft: '2px solid var(--border, rgba(0,0,0,0.08))' }}>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-3)', marginBottom: '0.25rem' }}>
                          {((parent.history?.entries || []).length + (parent.tracked_acts || []).length)} earlier chapter
                          {((parent.history?.entries || []).length + (parent.tracked_acts || []).length) > 1 ? 's' : ''} of this statute:
                        </div>
                        {((parent.history && parent.history.entries) || []).map((chapter, j) => (
                          <div key={`${chapter.handle || chapter.title}-${j}`}
                               style={{ display: 'flex', gap: '0.6rem', fontSize: '0.8rem', padding: '0.12rem 0' }}>
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.74rem',
                                           color: 'var(--text-2)', minWidth: '2.6rem' }}>
                              {chapter.year || '—'}
                            </span>
                            <span style={{ color: 'var(--text-1)' }}>
                              <a href={chapter.url} target="_blank" rel="noreferrer"
                                 style={{ color: 'var(--accent, #2563eb)' }}>
                                {chapter.title}
                              </a>
                              {chapter.act_number ? (
                                <span style={{ color: 'var(--text-2)' }}> · {chapter.act_number}</span>
                              ) : null}
                              {chapter.repealed_by ? (
                                <span style={{ color: 'var(--text-3)' }}> · repealed by {chapter.repealed_by}</span>
                              ) : null}
                            </span>
                          </div>
                        ))}
                        {/* Other Acts in THIS set that amend the same parent, linked to
                            their pages. India Code's catalogue lags (it has no 2025 record
                            for the Births and Deaths Act), so these come from the other
                            Acts' own text and are the chapters we can verify ourselves. */}
                        {(parent.tracked_acts || []).map((other) => (
                          <div key={`tracked-${other.id}`}
                               style={{ display: 'flex', gap: '0.6rem', fontSize: '0.8rem', padding: '0.12rem 0' }}>
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.74rem',
                                           color: 'var(--text-2)', minWidth: '2.6rem' }}>
                              {other.year || '—'}
                            </span>
                            <span style={{ color: 'var(--text-1)' }}>
                              <Link to={`/acts/${other.act_id}`} style={{ color: 'var(--accent, #2563eb)' }}>
                                {other.title}
                              </Link>
                              <span style={{ color: 'var(--text-3)' }}> · tracked in this set</span>
                            </span>
                          </div>
                        ))}
                        <div style={{ display: 'flex', gap: '0.6rem', fontSize: '0.8rem', padding: '0.12rem 0' }}>
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.74rem',
                                         color: 'var(--text-2)', minWidth: '2.6rem' }}>
                            {act?.year}
                          </span>
                          <span style={{ color: 'var(--text-1)', fontWeight: 600 }}>
                            {act?.title} — this Act
                          </span>
                        </div>
                        {parent.history && (
                          <div style={{ fontSize: '0.73rem', color: 'var(--text-3)', paddingTop: '0.25rem' }}>
                            {parent.history.note}
                          </div>
                        )}
                      </div>
                    )}
                    {!(parent.history && (parent.history.entries || []).length)
                      && !(parent.tracked_acts || []).length && (
                      <div style={{ fontSize: '0.73rem', color: 'var(--text-3)', marginTop: '0.35rem' }}>
                        {(parent.history && parent.history.note)
                          || 'No record of this statute has been read yet — run the statute-history build to read India Code.'}
                      </div>
                    )}
                  </div>
                ))}
                <p style={{ margin: '0.9rem 0 0', fontSize: '0.75rem', color: 'var(--text-3)' }}>
                  The earlier chapters are read from India Code's own catalogue and linked to
                  their records. Parent statutes do not have their own page in this set yet —
                  only the Acts listed under /acts do.
                </p>
              </>
            ) : (
              <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-2)' }}>
                {lineageNote || "No earlier statute is named in this Act's text."}
              </p>
            )}
          </div>
        </section>
      )}

      {/* Summary of the Act itself — rendered exactly like a bill summary on
          /explore (react-markdown inside .markdown-body), because it is the same
          kind of content and should read the same way.

          The model and 'generative' chips are deliberately NOT shown here: the
          reader wants the explanation, not the pipeline. Provenance is not lost —
          the source document, its size and the "not the law" caveat stay in the
          line below, and the full record (model_version, source_url) is on the API.
          The one badge that remains is the honesty one: a rule-based extractive
          summary is labelled as not AI-generated, as on the bills panel. */}
      <section style={{ marginBottom: '2rem' }}>
        <div className="card" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center', marginBottom: '0.85rem' }}>
            <h2 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600 }}>
              Summary of this Act
            </h2>
            {actSummary && (actSummary.summary_type === 'extractive'
                            || /rule_based/i.test(actSummary.model_version || '')) && (
              <span className="badge badge-amber"
                    title="No LLM backend produced output when this was generated — it is a rule-based extraction, not a model answer.">
                Rule-based extractive summary — not AI-generated
              </span>
            )}
          </div>

          {actSummary ? (
            <>
              <div className="markdown-body">
                <ReactMarkdown>{actSummary.summary || ''}</ReactMarkdown>
              </div>
              <p style={{ margin: '1rem 0 0', fontSize: '0.74rem', color: 'var(--text-3)', lineHeight: 1.5 }}>
                Generated from this Act&apos;s own official text
                {actSummary.source_url ? (
                  <>
                    {' ('}
                    <a href={actSummary.source_url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent)' }}>
                      the Act PDF
                    </a>
                    {')'}
                  </>
                ) : null}
                {actSummary.text_chars ? ` · ${actSummary.text_chars.toLocaleString('en-IN')} characters of source text` : ''}.
                A plain-English explanation, not the text of the law — check the Act itself before relying on it.
              </p>
            </>
          ) : (
            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-3)' }}>
              {actSummaryErr || 'Generating a summary from this Act\u2019s own text…'}
            </p>
          )}
        </div>
      </section>

      {/* Bills this came from */}
      {act.bills && act.bills.length > 0 && (
        <section style={{ marginBottom: '2rem' }}>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 700, margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Scale size={20} style={{ color: 'var(--accent)' }} />
            Bills This Came From ({act.bills.length})
          </h2>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-3)', margin: '-0.5rem 0 0.85rem' }}>
            Rows badged "Verified" are exact normalized title matches against PRS data.
            Rows badged "Candidate" are unconfirmed links shown for transparency only — they are not established facts.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {act.bills.map((bill) => {
              const lifecycleEvents = billLifecycles[bill.id] || []
              const isExpanded = expandedBills.has(bill.id)
              const hasLifecycle = lifecycleEvents.length > 0

              return (
                <div key={bill.id} className="card card-hover" style={{ overflow: 'hidden' }}>
                  {/* Bill header - always visible */}
                  <div
                    style={{
                      padding: '1rem 1.25rem',
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: '1rem',
                      alignItems: 'center',
                      cursor: hasLifecycle ? 'pointer' : 'default',
                      borderBottom: hasLifecycle ? '1px solid var(--border)' : 'none',
                    }}
                    onClick={() => hasLifecycle && toggleBillExpand(bill.id)}
                  >
                    <div style={{ flex: 1, minWidth: 240 }}>
                      <div style={{ fontWeight: 500, color: 'var(--text-1)', marginBottom: '0.2rem' }}>
                        {bill.title}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-3)' }}>
                        Bill ID: <span style={{ fontFamily: 'var(--font-mono)' }}>{bill.bill_id}</span>
                      </div>
                    </div>

                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', alignItems: 'center' }}>
                      <span className={`badge ${getStatusBadgeClass(bill.status)}`}>
                        {bill.status || 'unknown'}
                      </span>
                      <span className="badge badge-slate" style={{ fontSize: '0.65rem' }}>
                        {bill.link_type || 'linked'}
                      </span>
                      {bill.verified && (
                        <span
                          className="badge badge-emerald"
                          style={{ fontSize: '0.65rem', display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}
                          title="Verified match"
                        >
                          <CheckCircle size={10} /> Verified
                        </span>
                      )}
                      {!bill.verified && bill.match_confidence && (
                        <span
                          className="badge badge-amber"
                          style={{ fontSize: '0.65rem', display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}
                          title={`Unverified candidate match — not confirmed (${Math.round(bill.match_confidence * 100)}% title similarity against PRS data)`}
                        >
                          <Info size={10} /> Candidate {Math.round(bill.match_confidence * 100)}% — not confirmed
                        </span>
                      )}
                      {bill.url && (
                        <a
                          href={bill.url}
                          target="_blank"
                          rel="noreferrer"
                          className="btn btn-ghost"
                          style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem' }}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <ExternalLink size={14} /> Bill
                        </a>
                      )}
                      {hasLifecycle && (
                        <span
                          className="badge badge-vidhan"
                          style={{ fontSize: '0.65rem', display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}
                        >
                          {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                          {lifecycleEvents.length} event{lifecycleEvents.length === 1 ? '' : 's'}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Bill evidence - small text */}
                  {bill.evidence && (
                    <div
                      style={{
                        padding: '0 1.25rem 0.75rem',
                        fontSize: '0.72rem',
                        color: 'var(--text-3)',
                        fontFamily: 'var(--font-mono)',
                        fontStyle: 'italic',
                        borderBottom: hasLifecycle ? '1px solid var(--border)' : 'none',
                      }}
                    >
                      Evidence: {bill.evidence}
                    </div>
                  )}

                  {/* Expanded lifecycle timeline */}
                  {hasLifecycle && isExpanded && (
                    <div style={{ padding: '1rem 1.25rem', background: 'var(--surface-2)' }}>
                      <h3 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-2)', margin: '0 0 0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        Lifecycle Events (from Bill Tracker)
                      </h3>
                      <LifecycleTimeline events={lifecycleEvents} compact={true} />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* No linked bills */}
      {act.bills && act.bills.length === 0 && (
        <div className="card" style={{ padding: '2rem', textAlign: 'center' }}>
          <FileText size={48} style={{ margin: '0 auto 1rem', color: 'var(--text-3)' }} />
          <p className="empty-state-text">No bills linked to this act yet.</p>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-3)', marginTop: '0.5rem' }}>
            The act may predate the bill tracking system or the link hasn't been established.
          </p>
        </div>
      )}

      {/* Act's own lifecycle events (usually empty) */}
      {act.lifecycle_events && act.lifecycle_events.length > 0 && (
        <section>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 700, margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Info size={20} style={{ color: 'var(--accent)' }} />
            Act Lifecycle Events
          </h2>
          <LifecycleTimeline events={act.lifecycle_events} compact={false} />
        </section>
      )}
    </div>
  )
}