import { BrowserRouter as Router, Routes, Route, NavLink, Link } from 'react-router-dom';
import { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Home from './pages/Home';
import Explore from './pages/Explore';
import Favorites from './pages/Favorites';
import History from './pages/History';
import Subscribe from './pages/Subscribe';
import AuthModal from './components/AuthModal';
import './index.css';

function AppContent() {
  const { user, logout } = useAuth();
  const [showAuthModal, setShowAuthModal] = useState(false);

  return (
    <Router>
      <div className="app">
        <header className="header">
          <div className="container header-content">
            <Link to="/" className="logo">
              ⚖️ Vidhan.AI
            </Link>
            <nav className="nav">
              <NavLink to="/" className={({ isActive }) => isActive ? 'active' : ''}>
                Home
              </NavLink>
              <NavLink to="/explore" className={({ isActive }) => isActive ? 'active' : ''}>
                Explore
              </NavLink>
              <NavLink to="/alerts" className={({ isActive }) => isActive ? 'active' : ''}>
                Alerts
              </NavLink>
              {user && (
                <>
                  <NavLink to="/favorites" className={({ isActive }) => isActive ? 'active' : ''}>
                    Favorites
                  </NavLink>
                  <NavLink to="/history" className={({ isActive }) => isActive ? 'active' : ''}>
                    History
                  </NavLink>
                </>
              )}
            </nav>
            <div className="user-section">
              {user ? (
                <div className="user-menu">
                  <span style={{ color: '#94a3b8', fontWeight: 500 }}>{user.name || user.email}</span>
                  <button className="btn btn-secondary" onClick={logout} style={{ padding: '0.4rem 1rem', fontSize: '0.85rem' }}>
                    Logout
                  </button>
                </div>
              ) : (
                <button className="btn btn-primary" onClick={() => setShowAuthModal(true)} style={{ padding: '0.5rem 1.2rem', fontSize: '0.9rem' }}>
                  Sign In
                </button>
              )}
            </div>
          </div>
        </header>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/explore" element={<Explore />} />
            <Route path="/alerts" element={<Subscribe />} />
            <Route path="/favorites" element={<Favorites />} />
            <Route path="/history" element={<History />} />
          </Routes>
        </main>

        <footer style={{ 
          textAlign: 'center', 
          padding: '2rem', 
          color: '#64748b',
          borderTop: '1px solid rgba(255,255,255,0.05)',
          marginTop: 'auto'
        }}>
          <p>© 2026 Vidhan.AI | Generative AI Regulation Alert System</p>
          <p style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>
            Production SaaS Build
          </p>
        </footer>

        {showAuthModal && (
          <AuthModal onClose={() => setShowAuthModal(false)} />
        )}
      </div>
    </Router>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
