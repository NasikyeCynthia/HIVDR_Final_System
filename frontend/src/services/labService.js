import { request } from './api.js';
export const labService = {
  options: () => request('/lab/options'),
  collection: (id, data) => request(`/lab/${id}/collection`, { method: 'PUT', data }),
  dispatch: (id, data) => request(`/lab/${id}/dispatch`, { method: 'PUT', data }),
  receipt: (id, data) => request(`/lab/${id}/receipt`, { method: 'PUT', data }),
  result: (id, data) => request(`/lab/${id}/result`, { method: 'PUT', data }),
  mutations: (id,data) => request(`/lab/${id}/mutations`,{method:'PUT',data}),
  requestRepeat: (id, note = '') => request(`/lab/${id}/repeat-request`, { method: 'POST', data: { note } }),
};
