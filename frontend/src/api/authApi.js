import { USE_MOCK, request, delay, ApiError } from './client';
import { ROLES } from '../constants/roles';

/**
 * Backend contract:
 *   POST /auth/register  { name, email, password, taxId, homeAddress } -> { user, accessToken }
 *   POST /auth/login     { email, password }                          -> { user, accessToken }
 *   POST /auth/logout
 *   GET  /auth/me                                                      -> { user }
 * Password hashing (bcrypt/argon2) is the BACKEND's job; the frontend only sends the password over HTTPS.
 */

// Demo users — mock mode only. One per role for testing.
const demoUsers = [
  { id: 1, name: 'Alice Customer', email: 'customer@demo.com', role: ROLES.CUSTOMER, taxId: '11111111111', homeAddress: 'Kadıköy, Istanbul' },
  { id: 2, name: 'Sarah Sales', email: 'sales@demo.com', role: ROLES.SALES_MANAGER },
  { id: 3, name: 'Paul Product', email: 'product@demo.com', role: ROLES.PRODUCT_MANAGER },
  { id: 4, name: 'Sam Support', email: 'support@demo.com', role: ROLES.SUPPORT_AGENT },
];
const DEMO_PASSWORD = 'Demo1234';

export async function login({ email, password }) {
  if (USE_MOCK) {
    await delay(400);
    const user = demoUsers.find((u) => u.email === email.trim().toLowerCase());
    if (!user || password !== DEMO_PASSWORD) throw new ApiError('Incorrect email or password', 401);
    return { user, accessToken: `mock-token-${user.id}` };
  }
  return request('/auth/login', { method: 'POST', body: { email, password } });
}

export async function register(payload) {
  if (USE_MOCK) {
    await delay(400);
    if (demoUsers.some((u) => u.email === payload.email.toLowerCase())) {
      throw new ApiError('This email is already registered', 409);
    }
    // Every new sign-up is a "customer" — the role can NOT be chosen from the frontend.
    const user = { id: Date.now(), name: payload.name, email: payload.email.toLowerCase(),
      taxId: payload.taxId, homeAddress: payload.homeAddress, role: ROLES.CUSTOMER };
    demoUsers.push(user);
    return { user, accessToken: `mock-token-${user.id}` };
  }
  return request('/auth/register', { method: 'POST', body: payload });
}

export async function logout() {
  if (USE_MOCK) return;
  return request('/auth/logout', { method: 'POST' });
}
