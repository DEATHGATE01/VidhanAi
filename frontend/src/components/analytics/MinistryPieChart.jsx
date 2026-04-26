import { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { getMinistryAnalytics } from '../../services/api';

const COLORS = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b', '#fa709a', '#fee140', '#30cfd0'];

export default function MinistryPieChart() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await getMinistryAnalytics();
        if (response.success && response.ministries) {
          // Transform data for recharts
          const chartData = response.ministries.map(item => ({
            name: item.ministry || 'Unknown',
            value: item.bill_count
          }));
          setData(chartData);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="analytics-card">
        <h3 className="analytics-title">🏛️ Bills by Ministry</h3>
        <div className="loading">
          <div className="spinner"></div>
          <p>Loading ministry data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="analytics-card">
        <h3 className="analytics-title">🏛️ Bills by Ministry</h3>
        <div className="error-message">Failed to load ministry analytics: {error}</div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="analytics-card">
        <h3 className="analytics-title">🏛️ Bills by Ministry</h3>
        <div className="empty-state">
          <p>No ministry data available yet.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="analytics-card">
      <h3 className="analytics-title">🏛️ Bills by Ministry</h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
