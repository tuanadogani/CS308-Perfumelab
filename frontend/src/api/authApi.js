import { USE_MOCK, request, delay, ApiError } from './client';
import { ROLES } from '../constants/roles';

// Real backend uses JWT access/refresh tokens; profile is fetched from /auth/me/.
// Demo users — mock mode only. One per role for testing.
const demoUsers = [
  { id: 1, name: 'Ross Customer', email: 'customer@demo.com', role: ROLES.CUSTOMER, taxId: '11111111111', homeAddress: 'Kadıköy, Istanbul' },
  { id: 2, name: 'Monica Sales', email: 'sales@demo.com', role: ROLES.SALES_MANAGER },
  { id: 3, name: 'Phoebe Product', email: 'product@demo.com', role: ROLES.PRODUCT_MANAGER },
  { id: 4, name: 'Joey Support', email: 'support@demo.com', role: ROLES.SUPPORT_AGENT },
];
const DEMO_PASSWORD = 'Demo1234';

export async function login({ email, password }) {
  if (USE_MOCK) {
    await delay(400);
    const user = demoUsers.find((u) => u.email === email.trim().toLowerCase());
    if (!user || password !== DEMO_PASSWORD) throw new ApiError('Incorrect email or password', 401);
    return { user, accessToken: `mock-token-${user.id}` };
  }
  const tokens = await request('/auth/login/', { method: 'POST', body: { email, password } });
  // Fetch the profile using the newly issued access token.
  const user = await request('/auth/me/', { headers: { Authorization: `Bearer ${tokens.access}` }, retry: false });
  return { user, accessToken: tokens.access, refreshToken: tokens.refresh };
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
  const data = await request('/auth/register/', { method: 'POST', body: payload });
  return { user: data.user, accessToken: data.access, refreshToken: data.refresh };
}

export async function logout() {
  if (USE_MOCK) return;
  const session = JSON.parse(sessionStorage.getItem('ml_session') || 'null');
  return request('/auth/logout/', { method: 'POST', body: { refresh: session?.refreshToken } });
}
