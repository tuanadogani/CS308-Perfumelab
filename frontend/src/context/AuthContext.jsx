import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import * as authApi from '../api/authApi';
import { setAccessToken } from '../api/client';

const AuthContext = createContext(null);
const SESSION_KEY = 'ml_session';

// JWT session is scoped to this tab. Expired access tokens are refreshed by the API client.
function loadSession() {
  try {
    const s = JSON.parse(sessionStorage.getItem(SESSION_KEY));
    if (s?.user && s.accessToken) { setAccessToken(s.accessToken); return s.user; }
  } catch { /* ignore */ }
  return null;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(loadSession);

  useEffect(() => {
    const expire = () => setUser(null);
    window.addEventListener('auth:expired', expire);
    return () => window.removeEventListener('auth:expired', expire);
  }, []);

  const startSession = ({ user, accessToken, refreshToken }) => {
    setAccessToken(accessToken);
    sessionStorage.setItem(SESSION_KEY, JSON.stringify({ user, accessToken, refreshToken }));
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
