import { request } from './api.js';
export const decisionService = {
  approve: (id, data) => request(`/decisions/${id}/approve`, { method: 'POST', data }),
  implement: (id, data) => request(`/decisions/${id}/implement`, { method: 'POST', data }),
};
