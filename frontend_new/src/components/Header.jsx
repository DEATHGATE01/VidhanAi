import { useState } from 'react'
import { NavLink, Link } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import modules from '../config/modules'

// Top navigation. Nav items come from config/modules.js so the product
// module list lives in one place.
export default function Header() {
  const [mobileOpen, setMobileOpen] = useState(false)

  const navLinkClass = ({ isActive }) =>
    `px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? 'text-white bg-vidhan-600/20 border border-vidhan-500/40'
        : 'text-slate-400 hover:text-slate-200 hover:bg-white/5 border border-transparent'
    }`

  return (
    <header
      className="sticky top-0 z-40 backdrop-blur-xl"
      style={{ background: 'rgba(7,10,20,0.85)', borderBottom: '1px solid rgba(255,255,255,0.06)' }}
    >
      <nav className="container" aria-label="Main navigation">
        <div className="flex items-center justify-between h-16 gap-4">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5 shrink-0" aria-label="VidhanAI Home">
            <div
              style={{
                width: 38,
                height: 38,
                borderRadius: 12,
                background: 'linear-gradient(135deg,#8b5cf6,#3b82f6)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.15rem',
                boxShadow: '0 4px 14px rgba(139,92,246,0.35)',
              }}
            >
              ⚖️
            </div>
            <span className="hidden sm:block font-bold text-lg tracking-tight text-white">
              Vidhan<span style={{ color: '#a78bfa' }}>AI</span>
            </span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden lg:flex items-center gap-1">
            {modules.map((m) => (
              <NavLink key={m.id} to={`/${m.id}`} className={navLinkClass} title={m.description}>
                {m.label}
              </NavLink>
            ))}
          </div>

          {/* Mobile menu toggle */}
          <button
            type="button"
            className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
            onClick={() => setMobileOpen((o) => !o)}
            aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={mobileOpen}
          >
            {mobileOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>

        {/* Mobile nav */}
        {mobileOpen && (
          <div
            className="lg:hidden pb-4 flex flex-col gap-1"
            style={{ borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '0.75rem' }}
          >
            {modules.map((m) => (
              <NavLink
                key={m.id}
                to={`/${m.id}`}
                className={navLinkClass}
                onClick={() => setMobileOpen(false)}
              >
                {m.label}
                <span className="block text-xs text-slate-500 font-normal">{m.description}</span>
              </NavLink>
            ))}
          </div>
        )}
      </nav>
    </header>
  )
}
