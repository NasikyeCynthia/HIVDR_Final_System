import { request } from './api.js';
export const settingsService = {
  dataset: () => request('/settings/dataset'),
  updateDataset: source => request('/settings/dataset', { method: 'PUT', data: { source } }),
  users: () => request('/settings/users'),
  importCsv: data => request('/settings/import', { method: 'POST', data }),
  audit: () => request('/settings/audit'),
  integrations: () => request('/integrations/status'),
  notifications: () => request('/notifications'),
};
