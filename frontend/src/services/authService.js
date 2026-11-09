import { request } from './api.js';
export const authService = {
  me: () => request('/auth/me'),
  login: data => request('/auth/login', { method: 'POST', data }),
  logout: () => request('/auth/logout', { method: 'POST' }),
};
