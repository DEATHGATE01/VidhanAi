import { useState } from 'react'
import { NavLink, Link } from 'react-router-dom'
import { Menu, X, Scale, Brain, FileText, Bell, LogIn, LogOut } from 'lucide-react'
import ThemeToggle from './ThemeToggle'
import Vid from './Vid'
import SignInModal from './SignInModal'
import { useUser } from '../context/UserContext'

// Floating sidebar — the signature element of the CRM SaaS reference design.
// Desktop: fixed rounded card with margin. Mobile: slide-down panel.
// Architecture / Playground / Search were folded into Explore (summaries +
// semantic search live there now) and removed from the app.
const NAV = [
  { id: 'research', label: 'Research', icon: Brain, description: 'Multi-agent legislative research' },
  { id: 'explore', label: 'Explore', icon: FileText, description: 'Browse, search & read bill summaries' },
  { id: 'amendments', label: 'Amendments', icon: Scale, description: 'Delta-aware legislative diff' },
  { id: 'alerts', label: 'Alerts', icon: Bell, description: 'Email alerts for bills & topics' },
]

export default function Sidebar() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [signInOpen, setSignInOpen] = useState(false)
  const { user, signOut } = useUser()

  const openSignIn = () => { setMobileOpen(false); setSignInOpen(true) }

  return (
    <>
      {/* Mobile top bar */}
      <div
        className="lg:hidden sticky top-0 z-40 flex items-center justify-between px-4 h-14"
        style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)' }}
      >
        <Link to="/" className="flex items-center gap-2 font-bold" style={{ color: 'var(--text-1)' }} aria-label="VidhanAI Home">
          <span className="icon-chip icon-purple" style={{ width: 32, height: 32 }}><Vid size={24} /></span>
          Vidhan<span style={{ color: 'var(--accent)' }}>AI</span>
        </Link>
        <div className="flex items-center gap-1">
          <ThemeToggle size={20} />
          <button
            type="button"
            className="btn btn-ghost p-2"
            onClick={() => setMobileOpen((o) => !o)}
            aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={mobileOpen}
          >
            {mobileOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <nav className="lg:hidden px-3 py-2 animate-fade-in" style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)' }} aria-label="Mobile navigation">
          {NAV.map(({ id, label, icon: Icon }) => (
            <NavLink
              key={id}
              to={`/${id}`}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
            >
              <Icon size={17} /> {label}
            </NavLink>
          ))}
          <div style={{ borderTop: '1px solid var(--border)', marginTop: '0.5rem', paddingTop: '0.5rem' }}>
            {user ? (
              <button type="button" onClick={() => { setMobileOpen(false); signOut() }} className="sidebar-link" style={{ width: '100%', alignItems: 'center' }}>
                <LogOut size={17} /> Sign out {user.email}
              </button>
            ) : (
              <button type="button" onClick={openSignIn} className="sidebar-link" style={{ width: '100%', alignItems: 'center' }}>
                <LogIn size={17} /> Sign in / Sign up
              </button>
            )}
          </div>
        </nav>
      )}

      {/* Desktop floating sidebar */}
      <aside className="sidebar hidden lg:flex" aria-label="Main navigation">
        <Link to="/" className="flex items-center gap-2.5 px-2 pb-5" aria-label="VidhanAI Home">
          <span className="icon-chip icon-purple" style={{ width: 36, height: 36 }}><Vid size={28} /></span>
          <span className="font-bold text-lg tracking-tight" style={{ color: 'var(--text-1)' }}>
            Vidhan<span style={{ color: 'var(--accent)' }}>AI</span>
          </span>
        </Link>

        <nav className="flex flex-col gap-1 flex-1">
          {NAV.map(({ id, label, icon: Icon, description }) => (
            <NavLink
              key={id}
              to={`/${id}`}
              title={description}
              className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
            >
              <Icon size={17} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="px-2 pt-3 text-xs" style={{ borderTop: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
          {user ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="icon-chip icon-green" style={{ width: 28, height: 28, flex: '0 0 auto' }}>
                {(user.username || user.email || '?').slice(0, 1).toUpperCase()}
              </span>
              <div style={{ minWidth: 0, lineHeight: 1.25 }}>
                <p style={{ margin: 0, color: 'var(--text-1)', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {user.username || 'Guest'}
                </p>
                <p style={{ margin: 0, color: 'var(--text-3)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {user.email}
                </p>
              </div>
              <button type="button" onClick={signOut} className="btn btn-ghost p-1" style={{ marginLeft: 'auto', flex: '0 0 auto' }} title="Sign out" aria-label="Sign out">
                <LogOut size={14} />
              </button>
            </div>
          ) : (
            <button type="button" onClick={openSignIn} className="btn btn-secondary" style={{ padding: '0.45rem 0.7rem', fontSize: '0.8rem' }}>
              <LogIn size={14} /> Sign in / Sign up
            </button>
          )}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
            <p style={{ color: 'var(--text-3)', margin: 0 }}>
              PRS India data · free-tier stack
            </p>
            <ThemeToggle />
          </div>
        </div>
      </aside>

      <SignInModal open={signInOpen} onClose={() => setSignInOpen(false)} />
    </>
  )
}
