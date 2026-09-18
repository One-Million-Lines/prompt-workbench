import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { api, clearToken, getToken, setToken } from '../api/client';
import type { Principal } from '../api/types';

interface AuthContextValue {
  principal: Principal | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * Provides authentication state. On mount, if a token exists in sessionStorage
 * it validates it via GET /auth/me. The token itself lives in sessionStorage
 * (key `pw_token`); this context only mirrors the resolved principal.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [principal, setPrincipal] = useState<Principal | null>(null);
  const [loading, setLoading] = useState<boolean>(!!getToken());

  useEffect(() => {
    let cancelled = false;
    if (!getToken()) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then((p) => {
        if (!cancelled) setPrincipal(p);
      })
      .catch(() => {
        if (!cancelled) {
          clearToken();
          setPrincipal(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const res = await api.login(username, password);
    setToken(res.access_token);
    const me = await api.me();
    setPrincipal(me);
  }, []);

  const logout = useCallback(() => {
    // Best-effort server logout; token is cleared regardless.
    api.logout().catch(() => undefined);
    clearToken();
    setPrincipal(null);
  }, []);

  const value = useMemo(
    () => ({
      principal,
      isAuthenticated: !!principal,
      loading,
      login,
      logout,
    }),
    [principal, loading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
