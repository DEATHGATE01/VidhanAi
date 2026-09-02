import { useEffect, useState } from 'react'
import { X, LogIn, UserPlus, BellRing } from 'lucide-react'
import { useUser } from '../context/UserContext'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

// Sign up / sign in against the VidhanAI portal. On success the profile is
// stored by UserProvider (localStorage) — alert emails then come from it.
export default function SignInModal({ open, onClose, onSignedIn, initialMode = 'signin', initialEmail = '' }) {
  const { signIn, signUp } = useUser()
  const [mode, setMode] = useState(initialMode)
  const [email, setEmail] = useState(initialEmail)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (open) {
      setMode(initialMode)
      setEmail(initialEmail)
      setPassword('')
      setError('')
    }
  }, [open, initialMode, initialEmail])

  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    if (!EMAIL_RE.test(email.trim())) { setError('Enter a valid email address.'); return }
    if (mode === 'signup' && username.trim().length < 3) { setError('Username must be at least 3 characters.'); return }
    if (password.length < 6) { setError('Password must be at least 6 characters.'); return }
    setBusy(true)
    try {
      const account = mode === 'signin'
        ? await signIn(email.trim(), password)
        : await signUp({ email: email.trim(), username: username.trim(), password })
      onSignedIn?.(account)
      onClose()
    } catch (err) {
      const msg = err?.response?.data?.error || err?.message || 'Something went wrong.'
      setError(msg)
    } finally {
      setBusy(false)
    }
  }

  const toggleMode = () => {
    setMode((m) => (m === 'signin' ? 'signup' : 'signin'))
    setError('')
  }

  return (
    <div className="dialog-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="dialog-card glass-panel animate-fade-in" role="dialog" aria-modal="true" aria-label={mode === 'signin' ? 'Sign in' : 'Sign up'}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.1rem' }}>
          <span className="icon-chip icon-purple"><BellRing size={18} /></span>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.05rem' }}>{mode === 'signin' ? 'Sign in to VidhanAI' : 'Create your VidhanAI account'}</h3>
            <p style={{ margin: '0.1rem 0 0', fontSize: '0.78rem', color: 'var(--text-2)' }}>
              Alerts use the email on this profile — you won’t retype it.
            </p>
          </div>
          <button type="button" onClick={onClose} className="btn btn-ghost p-2" style={{ marginLeft: 'auto' }} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: '0.7rem' }}>
          {mode === 'signup' && (
            <label style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', fontSize: '0.8rem', color: 'var(--text-2)' }}>
              Username
              <input value={username} onChange={(e) => setUsername(e.target.value)} className="premium-input" autoComplete="username" style={{ padding: '0.6rem 0.85rem' }} placeholder="e.g. aarav" />
            </label>
          )}
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', fontSize: '0.8rem', color: 'var(--text-2)' }}>
            Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="premium-input" autoComplete="email" style={{ padding: '0.6rem 0.85rem' }} placeholder="you@example.com" />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', fontSize: '0.8rem', color: 'var(--text-2)' }}>
            Password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="premium-input" autoComplete={mode === 'signin' ? 'current-password' : 'new-password'} style={{ padding: '0.6rem 0.85rem' }} placeholder="••••••••" />
          </label>

          {error && <p role="alert" style={{ margin: 0, color: 'var(--danger)', fontSize: '0.8rem' }}>⚠️ {error}</p>}

          <button type="submit" disabled={busy} className="btn btn-primary" style={{ padding: '0.65rem 1rem', justifyContent: 'center' }}>
            {busy ? <><span className="spinner-ring" style={{ width: 16, height: 16, borderWidth: 2 }} /> Working…</> : mode === 'signin' ? <><LogIn size={15} /> Sign in</> : <><UserPlus size={15} /> Create account</>}
          </button>
        </form>

        <p style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-2)', margin: '0.9rem 0 0' }}>
          {mode === 'signin' ? 'New here?' : 'Already registered?'}{' '}
          <button type="button" onClick={toggleMode} className="btn-link" style={{ color: 'var(--accent)' }}>
            {mode === 'signin' ? 'Create an account' : 'Sign in instead'}
          </button>
        </p>
      </div>
    </div>
  )
}
