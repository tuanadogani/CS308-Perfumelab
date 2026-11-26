import { afterEach, describe, expect, it, vi } from 'vitest';
import { request, requestBlob, setAccessToken } from '../api/client';

const response = (data, status = 200) => ({
  ok: status < 400, status, json: async () => data,
});

afterEach(() => { setAccessToken(null); vi.unstubAllGlobals(); });

describe('API error handling', () => {
  it('propagates a network failure to the page without clearing a valid session', async () => {
    const removeItem = vi.fn();
    vi.stubGlobal('sessionStorage', { removeItem });
    const fetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'));
    vi.stubGlobal('fetch', fetch);
    setAccessToken('valid-access');
    await expect(request('/products/')).rejects.toThrow('Failed to fetch');
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(removeItem).not.toHaveBeenCalled();
  });

  it('propagates a failed invoice download instead of returning an empty file', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Network unavailable')));
    await expect(requestBlob('/sales/invoices/1/pdf/')).rejects.toThrow('Network unavailable');
  });

  it('clears the session and requests login when the refresh token has expired', async () => {
    const removeItem = vi.fn();
    const dispatchEvent = vi.fn();
    vi.stubGlobal('sessionStorage', {
      getItem: () => JSON.stringify({ accessToken: 'expired', refreshToken: 'also-expired' }),
      removeItem,
    });
    vi.stubGlobal('window', { dispatchEvent });
    setAccessToken('expired');
    const fetch = vi.fn().mockResolvedValue(response({ detail: 'Token is invalid or expired' }, 401));
    vi.stubGlobal('fetch', fetch);
    await expect(request('/orders/')).rejects.toMatchObject({
      status: 401, message: 'Your session expired. Please log in again.',
    });
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(removeItem).toHaveBeenCalledWith('ml_session');
    expect(dispatchEvent.mock.calls[0][0].type).toBe('auth:expired');
  });

  it('exposes backend validation messages to the page', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ message: 'Your cart is empty.' }, 400)));
    await expect(request('/checkout/', { method: 'POST', body: {} })).rejects.toMatchObject({
      status: 400, message: 'Your cart is empty.',
    });
    // This mocks the client contract; it does not imply a checkout endpoint exists.
  });

  it('returns a controlled error if an upstream server responds with non-JSON', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 502, json: async () => { throw new SyntaxError('HTML gateway response'); },
    }));
    await expect(request('/products/')).rejects.toMatchObject({ status: 502, message: 'Something went wrong' });
  });
});
