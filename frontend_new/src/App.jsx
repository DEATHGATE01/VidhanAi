import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import LandingPage from './pages/LandingPage'
import ExplorePage from './pages/ExplorePage'
import ResearchPage from './pages/ResearchPage'
import AmendmentsPage from './pages/AmendmentsPage'
import AlertsPage from './pages/AlertsPage'
import ArchitecturePage from './pages/ArchitecturePage'
import PlaygroundPage from './pages/PlaygroundPage'
import SearchPage from './pages/SearchPage'

// App shell: main.jsx provides <BrowserRouter>. Layout mirrors the CRM SaaS
// reference — floating sidebar + content column.
export default function App() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text-1)' }}>
      <Sidebar />
      <div className="app-main">
        <main style={{ flex: 1 }}>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/explore" element={<ExplorePage />} />
            <Route path="/research" element={<ResearchPage />} />
            <Route path="/amendments" element={<AmendmentsPage />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="/architecture" element={<ArchitecturePage />} />
            <Route path="/playground" element={<PlaygroundPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route
              path="*"
              element={
                <div className="container" style={{ padding: '4rem 1rem', textAlign: 'center' }}>
                  <div style={{ fontSize: '3rem', marginBottom: '0.75rem' }}>🔍</div>
                  <h1 className="page-title" style={{ marginBottom: '0.5rem' }}>Page not found</h1>
                  <p className="page-sub" style={{ marginBottom: '1.25rem' }}>
                    The page you are looking for does not exist.
                  </p>
                  <a href="/" className="btn btn-primary">Back to Home</a>
                </div>
              }
            />
          </Routes>
        </main>
        <footer className="container" style={{ padding: '1.5rem 1.25rem', borderTop: '1px solid var(--border)', marginTop: '2rem' }}>
          <div className="flex flex-col sm:flex-row items-center justify-between gap-2">
            <p className="text-xs" style={{ color: 'var(--text-3)', margin: 0 }}>
              © {new Date().getFullYear()} VidhanAI · Generative AI Legislative Simplification Engine
            </p>
            <p className="text-xs" style={{ color: 'var(--text-3)', margin: 0 }}>
              Data from PRS Legislative Research
            </p>
          </div>
        </footer>
      </div>
    </div>
  )
}
