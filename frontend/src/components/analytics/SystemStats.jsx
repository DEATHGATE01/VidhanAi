import { useEffect, useState } from 'react';
import { getSystemStats } from '../../services/api';

export default function SystemStats() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await getSystemStats();
        if (response.success) {
          setStats(response.stats);
        }
      } catch (err) {
        console.error('Failed to load stats:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="stats-grid">
        <div className="stat-card">
          <div className="spinner" style={{ width: '30px', height: '30px', margin: '0 auto' }}></div>
        </div>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="stats-grid">
      <div className="stat-card">
        <div className="stat-value">{stats.total_bills || 0}</div>
        <div className="stat-label">Total Bills</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{stats.total_users || 0}</div>
        <div className="stat-label">Active Users</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{stats.total_searches || 0}</div>
        <div className="stat-label">Total Searches</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{stats.unique_keywords || 0}</div>
        <div className="stat-label">Unique Keywords</div>
      </div>
    </div>
  );
}
