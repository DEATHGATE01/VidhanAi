import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============================================================================
// HEALTH & SYSTEM
// ============================================================================

export const checkHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

// ============================================================================
// SEARCH & BILLS
// ============================================================================

export const searchBills = async (keyword, userId = null) => {
  const params = { query: keyword };
  if (userId) params.user_id = userId;
  const response = await api.get('/semantic-search', { params });
  return response.data;
};

export const getBillById = async (billId, userId = null, trackReading = false) => {
  const params = {};
  if (userId) params.user_id = userId;
  if (trackReading) params.track_reading = true;
  const response = await api.get(`/bills/${billId}`, { params });
  return response.data;
};

export const getAllBills = async (page = 1, perPage = 20) => {
  const response = await api.get('/bills', {
    params: { page, per_page: perPage }
  });
  return response.data;
};

export const getBillSummary = async (billId) => {
  const response = await api.get(`/bills/${billId}/summary`);
  return response.data;
};

// ============================================================================
// USER MANAGEMENT
// ============================================================================

export const registerUser = async (userData) => {
  const response = await api.post('/users/register', userData);
  return response.data;
};

export const getUserById = async (userId) => {
  const response = await api.get(`/users/${userId}`);
  return response.data;
};

export const getUserAnalytics = async (userId) => {
  const response = await api.get(`/users/${userId}/analytics`);
  return response.data;
};

// ============================================================================
// FAVORITES
// ============================================================================

export const getUserFavorites = async (userId) => {
  const response = await api.get(`/users/${userId}/favorites`);
  return response.data;
};

export const addFavorite = async (userId, billId) => {
  const response = await api.post(`/users/${userId}/favorites`, { bill_id: billId });
  return response.data;
};

// ============================================================================
// READING HISTORY
// ============================================================================

export const getUserHistory = async (userId) => {
  const response = await api.get(`/users/${userId}/history`);
  return response.data;
};

// ============================================================================
// ANALYTICS (BIG DATA)
// ============================================================================

export const getTrendingSearches = async (limit = 10) => {
  const response = await api.get('/analytics/trending', {
    params: { limit }
  });
  return response.data;
};

export const getMinistryAnalytics = async () => {
  const response = await api.get('/analytics/ministry');
  return response.data;
};

export const getReadingHeatmap = async (userId = null) => {
  const params = {};
  if (userId) params.user_id = userId;
  const response = await api.get('/analytics/heatmap', { params });
  return response.data;
};

export const getSystemStats = async () => {
  const response = await api.get('/analytics/stats');
  return response.data;
};

export default api;
