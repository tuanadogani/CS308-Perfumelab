import { afterEach, describe, expect, it, vi } from 'vitest';
import { request, setAccessToken } from '../api/client';
import { login } from '../api/authApi';
import { getProducts, getProduct, getCategories } from '../api/productApi';

const response = (data, status = 200) => ({ ok: status < 400, status, json: async () => data });
afterEach(() => { setAccessToken(null); vi.unstubAllGlobals(); });

describe('real API contract', () => {
  it('maps JWT login and loads the profile', async () => {
    const user = { id: 1, name: 'Customer', role: 'customer' };
    const fetch = vi.fn().mockResolvedValueOnce(response({ access: 'access', refresh: 'refresh' }))
      .mockResolvedValueOnce(response(user));
    vi.stubGlobal('fetch', fetch);
    expect(await login({ email: 'a@b.com', password: 'secret' })).toEqual({ user, accessToken: 'access', refreshToken: 'refresh' });
    expect(fetch.mock.calls[0][0]).toBe('/api/auth/login/');
    expect(fetch.mock.calls[1][1].headers.Authorization).toBe('Bearer access');
  });

  it('uses Django trailing slashes for catalog URLs', async () => {
    const fetch = vi.fn().mockResolvedValue(response([]));
    vi.stubGlobal('fetch', fetch);
    await getProducts({ q: 'rose' }); await getProduct(1); await getCategories();
    expect(fetch.mock.calls.map(([url]) => url)).toEqual(['/api/products/?q=rose', '/api/products/1/', '/api/categories/']);
  });

  it('rotates tokens and retries once after expiry', async () => {
    let session = JSON.stringify({ user: { id: 1 }, accessToken: 'old', refreshToken: 'refresh' });
    vi.stubGlobal('sessionStorage', { getItem: () => session, setItem: (_, value) => { session = value; } });
    setAccessToken('old');
    const fetch = vi.fn().mockResolvedValueOnce(response({}, 401))
      .mockResolvedValueOnce(response({ access: 'new', refresh: 'rotated' }))
      .mockResolvedValueOnce(response({ id: 1 }));
    vi.stubGlobal('fetch', fetch);
    expect(await request('/auth/me/')).toEqual({ id: 1 });
    expect(JSON.parse(session).refreshToken).toBe('rotated');
    expect(fetch.mock.calls[2][1].headers.Authorization).toBe('Bearer new');
  });

  it('uses the rotated refresh token when retrying logout', async () => {
    let session = JSON.stringify({ accessToken: 'old', refreshToken: 'refresh' });
    vi.stubGlobal('sessionStorage', { getItem: () => session, setItem: (_, value) => { session = value; } });
    setAccessToken('old');
    const fetch = vi.fn().mockResolvedValueOnce(response({}, 401))
      .mockResolvedValueOnce(response({ access: 'new', refresh: 'rotated' }))
      .mockResolvedValueOnce(response(null, 204));
    vi.stubGlobal('fetch', fetch);
    await request('/auth/logout/', { method: 'POST', body: { refresh: 'refresh' } });
    expect(JSON.parse(fetch.mock.calls[2][1].body)).toEqual({ refresh: 'rotated' });
  });

  it('displays Django field validation errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ email: ['Already registered.'] }, 400)));
    await expect(request('/auth/register/')).rejects.toThrow('email: Already registered.');
  });
});
