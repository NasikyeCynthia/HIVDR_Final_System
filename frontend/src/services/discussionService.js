import { request } from './api.js';
export const discussionService = {
  add: (id, body) => request(`/discussions/${id}`, { method: 'POST', data: { body } }),
};
