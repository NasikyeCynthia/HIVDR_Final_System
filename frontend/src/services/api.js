/** All frontend requests use the Vite /api proxy and the HttpOnly session cookie. */
export async function request(path, { method = 'GET', data } = {}) {
  let response;
  try {
    response = await fetch(`/api${path}`, {
      method,
      credentials: 'same-origin',
      headers: data === undefined ? {} : { 'Content-Type': 'application/json' },
      body: data === undefined ? undefined : JSON.stringify(data),
    });
  } catch {
    throw new Error('Cannot reach the backend. Start FastAPI on port 8000.');
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(body.detail)
      ? body.detail.map(item => `${item.loc?.slice(1).join('.')}: ${item.msg}`).join('; ')
      : body.detail;
    const error = new Error(body.error || detail || `Request failed (${response.status})`);
    error.status = response.status;
    throw error;
  }
  return body;
}
