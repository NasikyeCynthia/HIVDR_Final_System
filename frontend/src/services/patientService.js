import { request } from './api.js';
export const patientService = {
  list: () => request('/patients'),
  get: id => request(`/patients/${id}`),
  create: data => request('/patients', { method: 'POST', data }),
  updateProfile: (id, data) => request(`/patients/${id}/profile`, { method: 'PATCH', data }),
  assign: (id, assigned_to) => request(`/patients/${id}/assignment`, { method: 'PATCH', data: { assigned_to: Number(assigned_to) } }),
};
