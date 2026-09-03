import axios from 'axios'

// API base URL. Defaults to '/api' (works in dev via the Vite proxy in
// vite.config.js, and in production if you front the backend with a rewrite).
// To point the built frontend at a different API host, set VITE_API_URL at
// build time, e.g. VITE_API_URL=https://vidhanai.onrender.com/api
// (See frontend/.env.example)
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ============================================================================
// HEALTH & SYSTEM
// ============================================================================

export const checkHealth = async () => {
  const response = await api.get('/health')
  return response.data
}

// ============================================================================
// SEARCH & BILLS
// ============================================================================

export const searchBills = async (keyword, userId = null) => {
  const params = { query: keyword }
  if (userId) params.user_id = userId
  const response = await api.get('/semantic-search', { params })
  return response.data
}

export const getBillById = async (billId, userId = null, trackReading = false) => {
  const params = {}
  if (userId) params.user_id = userId
  if (trackReading) params.track_reading = true
  const response = await api.get(`/bills/${billId}`, { params })
  return response.data
}

export const getAllBills = async (page = 1, perPage = 20) => {
  const response = await api.get('/bills', {
    params: { page, per_page: perPage }
  })
  return response.data
}

export const getBillSummary = async (billId) => {
  const response = await api.get(`/bills/${billId}/summary`)
  return response.data
}

// ============================================================================
// USER MANAGEMENT
// ============================================================================

export const registerUser = async (userData) => {
  const response = await api.post('/users/register', userData)
  return response.data
}

export const loginUser = async ({ email, password }) => {
  const response = await api.post('/users/login', { email, password })
  return response.data
}

export const getUserById = async (userId) => {
  const response = await api.get(`/users/${userId}`)
  return response.data
}

export const getUserAnalytics = async (userId) => {
  const response = await api.get(`/users/${userId}/analytics`)
  return response.data
}

// ============================================================================
// FAVORITES
// ============================================================================

export const getUserFavorites = async (userId) => {
  const response = await api.get(`/users/${userId}/favorites`)
  return response.data
}

export const addFavorite = async (userId, billId) => {
  const response = await api.post(`/users/${userId}/favorites`, { bill_id: billId })
  return response.data
}

// ============================================================================
// READING HISTORY
// ============================================================================

export const getUserHistory = async (userId) => {
  const response = await api.get(`/users/${userId}/history`)
  return response.data
}

// ============================================================================
// ANALYTICS (BIG DATA)
// ============================================================================

export const getTrendingSearches = async (limit = 10) => {
  const response = await api.get('/analytics/trending', {
    params: { limit }
  })
  return response.data
}

export const getMinistryAnalytics = async () => {
  const response = await api.get('/analytics/ministry')
  return response.data
}

export const getReadingHeatmap = async (userId = null) => {
  const params = {}
  if (userId) params.user_id = userId
  const response = await api.get('/analytics/heatmap', { params })
  return response.data
}

export const getSystemStats = async () => {
  const response = await api.get('/analytics/stats')
  return response.data
}

// ============================================================================
// MULTI-AGENT ORCHESTRATION (Phase 3)
// ============================================================================

// /agent/research is the slowest endpoint: the first call lazily imports the
// agent stack (~60s) and the Flask dev server can restart mid-request, which
// the Vite proxy surfaces as a 502 even though the backend is healthy. Retry
// transient failures (no response, or HTTP >= 500) with a short backoff so the
// well-known "retry succeeds" case never reaches the user as a dead-end error.
const researchRetry = async (request) => {
  const MAX_ATTEMPTS = 3
  let lastErr = null
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt += 1) {
    try {
      const response = await request()
      return response.data
    } catch (err) {
      const status = err?.response?.status
      lastErr = err
      // Retry only network/proxy failures and 5xx — never 4xx (e.g. 413/400).
      if ((status && status < 500) || attempt === MAX_ATTEMPTS) break
      await new Promise((resolve) => setTimeout(resolve, 400 * attempt))
    }
  }
  throw lastErr
}

export const runAgentResearch = async (question, maxSteps = 6, useLlmPlanner = false) =>
  researchRetry(() =>
    api.post('/agent/research', {
      question,
      max_steps: maxSteps,
      use_llm_planner: useLlmPlanner,
    }),
  )

// ============================================================================
// AMENDMENT DIFF (Phase 3 — delta-aware summarization)
// ============================================================================

export const diffAmendments = async (billIdV1, billIdV2, textV1 = null, textV2 = null) => {
  const body = { bill_id_v1: billIdV1, bill_id_v2: billIdV2 }
  if (textV1) body.text_v1 = textV1
  if (textV2) body.text_v2 = textV2
  const response = await api.post('/amendment/diff', body)
  return response.data
}

export const getBillVersions = async (billId, limit = 20) => {
  const response = await api.get(`/bills/${billId}/versions`, { params: { limit } })
  return response.data
}

// ============================================================================
// ALERTS (subscription + n8n email pipeline)
// ============================================================================

export const subscribeToAlerts = async ({ email, specificBills = [], keywords = [], ministries = [], frequency = 'instant' }) => {
  const response = await api.post('/subscribe', {
    email,
    specific_bills: specificBills,
    keywords,
    ministries,
    email_frequency: frequency,
  })
  return response.data
}

export const unsubscribeFromAlerts = async (email) => {
  const response = await api.post('/unsubscribe', { email })
  return response.data
}

export const getBillNews = async (billId, limit = 5) => {
  const response = await api.get(`/bills/${billId}/news`, { params: { limit } })
  return response.data
}

export default api