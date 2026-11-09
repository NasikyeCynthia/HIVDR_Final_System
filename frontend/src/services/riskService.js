import { request } from './api.js';
export const riskService = {
  rules: () => request('/risk/rules'),
  assess: id => request(`/risk/${id}`),
  refer: id => request(`/risk/${id}/refer`, { method: 'POST' }),
};
