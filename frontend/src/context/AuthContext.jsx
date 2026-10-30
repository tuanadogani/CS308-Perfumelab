import { createContext, useContext, useMemo, useState } from 'react';
import * as authApi from '../api/authApi';
import { setAccessToken } from '../api/client';

const AuthContext = createContext(null);
const SESSION_KEY = 'ml_session';

// Sprint 1: the session is kept in sessionStorage (cleared when the tab closes).
// Recommended with the real backend: refresh token in an httpOnly cookie, restore the session with GET /auth/me on load.
function loadSession() {
  try {
    const s = JSON.parse(sessionStorage.getItem(SESSION_KEY));
    if (s?.user) { setAccessToken(s.accessToken); return s.user; }
  } catch { /* ignore */ }
  return null;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(loadSession);

  const startSession = ({ user, accessToken }) => {
    setAccessToken(accessToken);
    sessionStorage.setItem(SESSION_KEY, JSON.stringify({ user, accessToken }));
    setUser(user);
    return user;
  };

  const value = useMemo(() => ({
    user,
    isAuthenticated: !!user,
    hasRole: (...roles) => !!user && roles.includes(user.role),
    login: async (creds) => startSession(await authApi.login(creds)),
    register: async (data) => startSession(await authApi.register(data)),
    logout: async () => {
      await authApi.logout().catch(() => {});
      setAccessToken(null);
      sessionStorage.removeItem(SESSION_KEY);
      setUser(null);
    },
  }), [user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
