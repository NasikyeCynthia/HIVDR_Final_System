import { request } from './api.js';
// DR-testing eligibility under MoH criteria (replaces the earlier points score).
export const riskService = {
  rules: () => request('/eligibility/rules'),
  assess: id => request(`/eligibility/${id}`),
  addIac: (id, data) => request(`/eligibility/${id}/iac`, { method: 'POST', data }),
  removeIac: (id, sessionId) => request(`/eligibility/${id}/iac/${sessionId}`, { method: 'DELETE' }),
  refer: (id, data = { basis: 'guideline' }) => request(`/eligibility/${id}/refer`, { method: 'POST', data }),
};
