// src/api.js
import axios from 'axios';

// Get CSRF token from cookie (Django default name)
function getCookie(name) {
  let cookieValue = null;
  if (typeof document === 'undefined') return null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const trimmed = cookie.trim();
      if (trimmed.startsWith(name + '=')) {
        cookieValue = decodeURIComponent(trimmed.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// attach CSRF and auth tokens
api.interceptors.request.use((config) => {
  const csrfToken = getCookie('csrftoken');
  if (csrfToken) config.headers['X-CSRFToken'] = csrfToken;

  const token = localStorage.getItem('authToken');
  if (token) config.headers.Authorization = `Bearer ${token}`;

  return config;
});

export default api;
