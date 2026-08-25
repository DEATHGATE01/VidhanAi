import { Link } from 'react-router-dom'
import { Globe, MessageCircle, Mail } from 'lucide-react'

// Site footer. Product links route in-app; the rest are placeholders.
const PRODUCT_LINKS = [
  { label: 'Research', to: '/research' },
  { label: 'Explore Bills', to: '/explore' },
  { label: 'Amendments', to: '/amendments' },
  { label: 'Architecture', to: '/architecture' },
  { label: 'Playground', to: '/playground' },
]

const SOCIAL_LINKS = [
  { icon: Globe, href: 'https://github.com', label: 'GitHub' },
  { icon: MessageCircle, href: 'https://twitter.com', label: 'Twitter' },
  { icon: Mail, href: 'mailto:hello@vidhanai.org', label: 'Email' },
]

export default function Footer() {
  return (
    <footer
      style={{ background: '#05070f', borderTop: '1px solid rgba(255,255,255,0.06)' }}
      className="mt-16"
    >
      <div className="container py-12">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-10">
          {/* Brand */}
          <div className="col-span-2">
            <div className="flex items-center gap-2.5 mb-4">
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 11,
                  background: 'linear-gradient(135deg,#8b5cf6,#3b82f6)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '1.05rem',
                }}
              >
                ⚖️
              </div>
              <span className="font-bold text-lg text-white">VidhanAI</span>
            </div>
            <p className="text-sm text-slate-400 max-w-xs leading-relaxed">
              Generative AI legislative simplification for Indian parliamentary bills —
              multi-agent orchestration over PRS India data.
            </p>
            <div className="flex gap-3 mt-5">
              {SOCIAL_LINKS.map(({ icon: Icon, href, label }) => (
                <a
                  key={label}
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={label}
                  className="p-2 rounded-lg text-slate-500 hover:text-vidhan-400 transition-colors"
                >
                  <Icon size={18} />
                </a>
              ))}
            </div>
          </div>

          {/* Product */}
          <div>
            <h4 className="font-semibold text-slate-200 mb-4">Product</h4>
            <ul className="space-y-2.5">
              {PRODUCT_LINKS.map(({ label, to }) => (
                <li key={label}>
                  <Link
                    to={to}
                    className="text-sm text-slate-500 hover:text-vidhan-400 transition-colors"
                  >
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h4 className="font-semibold text-slate-200 mb-4">Data & Docs</h4>
            <ul className="space-y-2.5">
              <li>
                <a
                  href="https://prsindia.org/billtrack"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-slate-500 hover:text-vidhan-400 transition-colors"
                >
                  PRS BillTrack
                </a>
              </li>
              <li>
                <Link to="/architecture" className="text-sm text-slate-500 hover:text-vidhan-400 transition-colors">
                  Live Architecture
                </Link>
              </li>
              <li>
                <span className="text-sm text-slate-600">API Reference — /api/health</span>
              </li>
            </ul>
          </div>
        </div>

        <div
          className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-3"
          style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}
        >
          <p className="text-xs text-slate-600">
            © {new Date().getFullYear()} VidhanAI · Generative AI Legislative Simplification Engine
          </p>
          <p className="text-xs text-slate-600">
            Data sourced from PRS Legislative Research · Free-tier architecture
          </p>
        </div>
      </div>
    </footer>
  )
}
