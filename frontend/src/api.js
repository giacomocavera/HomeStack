import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'CF-Access-Client-Id': import.meta.env.VITE_CF_ACCESS_CLIENT_ID || '',
    'CF-Access-Client-Secret': import.meta.env.VITE_CF_ACCESS_CLIENT_SECRET || '',
  },
});

export const api = {
  getLocations: () => apiClient.get('/locations/'),
  createLocation: (data) => apiClient.post('/locations/', data),
  updateLocation: (id, data) => apiClient.put(`/locations/${id}`, data),
  deleteLocation: (id) => apiClient.delete(`/locations/${id}`),
  getLocationItems: (id) => apiClient.get(`/locations/${id}/items`),
  getLocationPrintPayload: (id) => apiClient.get(`/locations/${id}/print-payload/`),

  getItems: () => apiClient.get('/items/'),
  searchItems: (query) => apiClient.get(`/items/search/?q=${encodeURIComponent(query)}`),
  createItem: (data) => apiClient.post('/items/', data),
  updateItem: (id, data) => apiClient.put(`/items/${id}`, data),
  deleteItem: (id) => apiClient.delete(`/items/${id}`),
  getItemPrintPayload: (itemId) => apiClient.get(`/items/${itemId}/print-payload/`),

  scanLookup: (qrCode) => apiClient.get(`/scan/${encodeURIComponent(qrCode)}`),

  analyzeImage: (formData) => apiClient.post('/ai/analyze-image/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  getSettings: () => apiClient.get('/settings/'),
  updateSettings: (data) => apiClient.post('/settings/', data),
};