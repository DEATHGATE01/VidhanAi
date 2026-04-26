import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { registerUser } from '../services/api';
import './AuthModal.css';

export default function AuthModal({ onClose }) {
  const { login, register } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    organization: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      if (isLogin) {
        // Mock login for demo (in production, call login API)
        const userData = {
          id: 1,
          name: formData.email.split('@')[0],
          email: formData.email,
          organization: 'Demo Org'
        };
        login(userData);
        onClose();
      } else {
        // Register new user
        const response = await registerUser({
          name: formData.name,
          email: formData.email,
          password: formData.password,
          organization: formData.organization
        });

        if (response.success) {
          register(response.user);
          onClose();
        } else {
          setError(response.error || 'Registration failed');
        }
      }
    } catch (err) {
      setError(err.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={(e) => e.target.className === 'modal-backdrop' && onClose()}>
      <div className="auth-modal">
        <button className="modal-close" onClick={onClose}>✕</button>
        
        <h2 className="auth-title">
          {isLogin ? '👤 Login' : '📝 Register'}
        </h2>

        <form onSubmit={handleSubmit} className="auth-form">
          {!isLogin && (
            <div className="form-group">
              <label>Full Name</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                required
                placeholder="Enter your name"
              />
            </div>
          )}

          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
              placeholder="Enter your email"
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
              placeholder="Enter your password"
              minLength={6}
            />
          </div>

          {!isLogin && (
            <div className="form-group">
              <label>Organization (Optional)</label>
              <input
                type="text"
                name="organization"
                value={formData.organization}
                onChange={handleChange}
                placeholder="Your organization"
              />
            </div>
          )}

          {error && (
            <div className="error-message">{error}</div>
          )}

          <button 
            type="submit" 
            className="btn btn-primary auth-submit"
            disabled={loading}
          >
            {loading ? 'Processing...' : (isLogin ? 'Login' : 'Register')}
          </button>
        </form>

        <div className="auth-switch">
          {isLogin ? "Don't have an account? " : "Already have an account? "}
          <button 
            className="link-button"
            onClick={() => {
              setIsLogin(!isLogin);
              setError('');
            }}
          >
            {isLogin ? 'Register' : 'Login'}
          </button>
        </div>
      </div>
    </div>
  );
}
