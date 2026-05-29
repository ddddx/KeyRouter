import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Channels
export const getChannels = () => api.get('/channels').then(r => r.data)
export const createChannel = (data) => api.post('/channels', data).then(r => r.data)
export const getChannel = (id) => api.get(`/channels/${id}`).then(r => r.data)
export const updateChannel = (id, data) => api.put(`/channels/${id}`, data).then(r => r.data)
export const deleteChannel = (id) => api.delete(`/channels/${id}`).then(r => r.data)

// Keys
export const getKeys = (params) => api.get('/keys', { params }).then(r => r.data)
export const createKey = (data) => api.post('/keys', data).then(r => r.data)
export const batchCreateKeys = (data) => api.post('/keys/batch', data).then(r => r.data)
export const updateKey = (id, data) => api.put(`/keys/${id}`, data).then(r => r.data)
export const deleteKey = (id) => api.delete(`/keys/${id}`).then(r => r.data)
export const batchDeleteKeys = (params) => api.delete('/keys/batch', { params }).then(r => r.data)

// Stats
export const getDashboardStats = () => api.get('/admin/stats/dashboard').then(r => r.data)
export const getChannelStats = (id) => api.get(`/admin/stats/channel/${id}`).then(r => r.data)
export const getKeyStats = (id) => api.get(`/admin/stats/key/${id}`).then(r => r.data)

// Logs
export const getLogs = (params) => api.get('/admin/logs', { params }).then(r => r.data)

// Config
export const getConfig = () => api.get('/admin/config').then(r => r.data)

export default api