// Every HTTP request goes through here. When the backend is ready, this is the only place to touch.
export const USE_MOCK = (import.meta.env.VITE_USE_MOCK ?? 'true') === 'true';
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

let accessToken = null; // Kept in memory (never written to localStorage → lower XSS risk)
export const setAccessToken = (t) => { accessToken = t; };

export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

export async function request(path, { method = 'GET', body, headers = {} } = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    credentials: 'include', // send cookies if the backend issues an httpOnly refresh token
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(data?.message || 'Something went wrong', res.status);
  return data;
}

// Simulates network latency for the mocks
export const delay = (ms = 300) => new Promise((r) => setTimeout(r, ms));
