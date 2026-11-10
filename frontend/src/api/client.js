// Every HTTP request goes through here. When the backend is ready, this is the only place to touch.
export const USE_MOCK = (import.meta.env.VITE_USE_MOCK ?? 'false') === 'true';
const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '');

let accessToken = null; // Kept in memory (never written to localStorage → lower XSS risk)
export const setAccessToken = (t) => { accessToken = t; };

export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

let refreshing = null;
export function clearSession() {
  accessToken = null;
  sessionStorage.removeItem('ml_session');
  window.dispatchEvent(new Event('auth:expired'));
}

async function refreshSession() {
  const session = JSON.parse(sessionStorage.getItem('ml_session') || 'null');
  if (!session?.refreshToken) throw new Error('No refresh token');
  const data = await request('/auth/refresh/', {
    method: 'POST', body: { refresh: session.refreshToken }, retry: false,
  });
  setAccessToken(data.access);
  sessionStorage.setItem('ml_session', JSON.stringify({
    ...session, accessToken: data.access, refreshToken: data.refresh,
  }));
}

export async function request(path, { method = 'GET', body, headers = {}, retry = true } = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    credentials: 'omit', // JWT authentication uses the Authorization header
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401 && retry && accessToken && !path.startsWith('/auth/login')) {
    try {
      if (!refreshing) refreshing = refreshSession().finally(() => { refreshing = null; });
      await refreshing;
    } catch {
      clearSession();
      throw new ApiError('Your session expired. Please log in again.', 401);
    }
    const retryBody = path === '/auth/logout/'
      ? { refresh: JSON.parse(sessionStorage.getItem('ml_session')).refreshToken }
      : body;
    return request(path, { method, body: retryBody, headers, retry: false });
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(data?.message || data?.detail || (data && Object.entries(data).map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(' ') : value}`).join(' ')) || 'Something went wrong', res.status);
  return data;
}

// Simulates network latency for the mocks
export const delay = (ms = 300) => new Promise((r) => setTimeout(r, ms));

// Binary downloads (e.g. invoice PDFs). Same auth + refresh flow as `request`,
// but returns a Blob so the browser can open or save it.
export async function requestBlob(path, { retry = true } = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    credentials: 'omit',
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
  });
  if (res.status === 401 && retry && accessToken) {
    try {
      if (!refreshing) refreshing = refreshSession().finally(() => { refreshing = null; });
      await refreshing;
    } catch {
      clearSession();
      throw new ApiError('Your session expired. Please log in again.', 401);
    }
    return requestBlob(path, { retry: false });
  }
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new ApiError(data?.message || data?.detail || 'Could not download the file', res.status);
  }
  return res.blob();
}
