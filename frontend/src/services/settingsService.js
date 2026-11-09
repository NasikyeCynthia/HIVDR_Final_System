import { request } from './api.js';
export const settingsService = {
  users: () => request('/settings/users'),
  importCsv: data => request('/settings/import', { method: 'POST', data }),
  audit: () => request('/settings/audit'),
  integrations: () => request('/integrations/status'),
  notifications: () => request('/notifications'),
};
