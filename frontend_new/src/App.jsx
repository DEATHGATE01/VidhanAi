import { Routes, Route } from 'react-router-dom'
import Header from './components/Header'
import Footer from './components/Footer'
import LandingPage from './pages/LandingPage'
import ExplorePage from './pages/ExplorePage'
import ResearchPage from './pages/ResearchPage'
import AmendmentsPage from './pages/AmendmentsPage'
import AlertsPage from './pages/AlertsPage'
import ArchitecturePage from './pages/ArchitecturePage'
import PlaygroundPage from './pages/PlaygroundPage'
import SearchPage from './pages/SearchPage'

// App shell: main.jsx provides <BrowserRouter>, so this component only lays
// out Header / routes / Footer. Dark-first palette lives in index.css (@theme).
export default function App() {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        background: '#070a14',
        color: '#e2e8f0',
      }}
    >
      <Header />
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
                <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>
                  Page not found
                </h1>
                <p style={{ color: '#64748b', marginBottom: '1.25rem' }}>
                  The page you are looking for does not exist.
                </p>
                <a href="/" className="btn btn-primary">Back to Home</a>
              </div>
            }
          />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}
