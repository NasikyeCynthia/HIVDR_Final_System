import { request } from './api.js';
export const labService = {
  save: (id, data) => request(`/lab/${id}`, { method: 'PUT', data }),
  requestRepeat: id => request(`/lab/${id}/repeat-request`, { method: 'POST' }),
};
