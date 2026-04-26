import { useEffect, useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { getReadingHeatmap } from '../../services/api';

export default function ReadingHeatmap({ userId }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await getReadingHeatmap(userId);
        if (response.success && response.heatmap) {
          // Transform for area chart
          const chartData = response.heatmap.map(item => ({
            date: new Date(item.date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }),
            reads: item.read_count
          }));
          setData(chartData);
        }
      } catch (err) {
        console.error('Failed to load heatmap:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [userId]);

  if (loading) {
    return (
      <div className="analytics-card">
        <h3 className="analytics-title">📈 Reading Activity</h3>
        <div className="loading">
          <div className="spinner"></div>
          <p>Loading activity...</p>
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="analytics-card">
        <h3 className="analytics-title">📈 Reading Activity</h3>
        <div className="empty-state">
          <p>No reading activity data yet.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="analytics-card">
      <h3 className="analytics-title">📈 Reading Activity Over Time</h3>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="colorReads" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#667eea" stopOpacity={0.8}/>
              <stop offset="95%" stopColor="#667eea" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Area 
            type="monotone" 
            dataKey="reads" 
            stroke="#667eea" 
            fillOpacity={1} 
            fill="url(#colorReads)" 
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
