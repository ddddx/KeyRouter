import axios from 'axios'

const TOKEN_KEY = 'keyrouter_token'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Request interceptor — attach JWT token
api.interceptors.request.use(config => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor — handle 401 (expired/invalid token)
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response && error.response.status === 401) {
      // Clear token and redirect to login
      localStorage.removeItem(TOKEN_KEY)
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ─── Auth ───
export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)
export const isLoggedIn = () => !!getToken()

export const login = (username, password) => api.post('/auth/login', { username, password }).then(r => r.data)
export const setupAdmin = (username, password) => api.post('/auth/setup', { username, password }).then(r => r.data)
export const changePassword = (old_password, new_password) => api.post('/auth/change-password', { old_password, new_password }).then(r => r.data)
export const getMe = () => api.get('/auth/me').then(r => r.data)
export const getAuthStatus = () => api.get('/auth/status').then(r => r.data)

// ─── Channels ───
export const getChannels = () => api.get('/channels').then(r => r.data)
export const createChannel = (data) => api.post('/channels', data).then(r => r.data)
export const getChannel = (id) => api.get(`/channels/${id}`).then(r => r.data)
export const updateChannel = (id, data) => api.put(`/channels/${id}`, data).then(r => r.data)
export const deleteChannel = (id) => api.delete(`/channels/${id}`).then(r => r.data)

// ─── Keys ───
export const getKeys = (params) => api.get('/keys', { params }).then(r => r.data)
export const createKey = (data) => api.post('/keys', data).then(r => r.data)
export const batchCreateKeys = (data) => api.post('/keys/batch', data).then(r => r.data)
export const updateKey = (id, data) => api.put(`/keys/${id}`, data).then(r => r.data)
export const deleteKey = (id) => api.delete(`/keys/${id}`).then(r => r.data)
export const batchDeleteKeys = (params) => api.delete('/keys/batch', { params }).then(r => r.data)

// ─── Stats ───
export const getDashboardStats = () => api.get('/admin/stats/dashboard').then(r => r.data)
export const getChannelStats = (id) => api.get(`/admin/stats/channel/${id}`).then(r => r.data)
export const getKeyStats = (id) => api.get(`/admin/stats/key/${id}`).then(r => r.data)

// ─── Logs ───
export const getLogs = (params) => api.get('/admin/logs', { params }).then(r => r.data)

// CSV export - returns blob
export const exportLogsCSV = (params) => api.get('/admin/logs/export/csv', { params, responseType: 'blob' }).then(r => r.data)

// ─── Config ───
export const getConfig = () => api.get('/admin/config').then(r => r.data)

export default api