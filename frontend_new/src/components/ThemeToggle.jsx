import { Moon, Sun } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'

// Sun/Moon switch between light and dark mode. Theme state lives in
// ThemeContext (persisted to localStorage, applied via data-theme).
export default function ThemeToggle({ size = 18, className = '' }) {
  const { theme, toggleTheme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={`btn btn-ghost p-2 ${className}`}
      style={{ borderRadius: 10 }}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {isDark ? <Sun size={size} /> : <Moon size={size} />}
    </button>
  )
}
