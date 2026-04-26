import { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { getTrendingSearches } from '../../services/api';

export default function TrendingChart() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await getTrendingSearches(10);
        if (response.success && response.trending) {
          // Transform data for recharts
          const chartData = response.trending.map(item => ({
            keyword: item.keyword,
            searches: item.search_count,
            users: item.unique_users
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
        <h3 className="analytics-title">📊 Trending Searches</h3>
        <div className="loading">
          <div className="spinner"></div>
          <p>Loading trending data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="analytics-card">
        <h3 className="analytics-title">📊 Trending Searches</h3>
        <div className="error-message">Failed to load trending searches: {error}</div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="analytics-card">
        <h3 className="analytics-title">📊 Trending Searches</h3>
        <div className="empty-state">
          <p>No search data available yet. Start searching to see trends!</p>
        </div>
      </div>
    );
  }

  return (
    <div className="analytics-card">
      <h3 className="analytics-title">📊 Trending Searches</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="keyword" angle={-45} textAnchor="end" height={80} />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="searches" fill="#667eea" name="Total Searches" />
          <Bar dataKey="users" fill="#764ba2" name="Unique Users" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
