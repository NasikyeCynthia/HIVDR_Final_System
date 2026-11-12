import { request } from './api.js';
export const patientService = {
  list: () => request('/patients'),
  columns: () => request('/patients/columns'),
  table: (ids, fields) => request(`/patients/table?${ids.map(id=>`ids=${encodeURIComponent(id)}`).join('&')}${fields.length?'&'+fields.map(field=>`fields=${encodeURIComponent(field)}`).join('&'):''}`),
  get: id => request(`/patients/${id}`),
  create: data => request('/patients', { method: 'POST', data }),
  updateProfile: (id, data) => request(`/patients/${id}/profile`, { method: 'PATCH', data }),
  vlSample: (id, data) => request(`/patients/${id}/vl-samples`, { method: 'POST', data }),
  vlResult: (id, sampleId, data) => request(`/patients/${id}/vl-samples/${sampleId}/result`, { method: 'PUT', data }),
  assign: (id, assigned_to) => request(`/patients/${id}/assignment`, { method: 'PATCH', data: { assigned_to: Number(assigned_to) } }),
};
