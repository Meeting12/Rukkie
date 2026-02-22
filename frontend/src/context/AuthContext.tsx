import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import axios from 'axios';

interface AuthState {
  isAuthenticated: boolean;
  username?: string | null;
  lastError?: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  refreshAuth: (options?: { silent?: boolean }) => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};

const getCookie = (name: string) => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()!.split(';').shift()!;
  return null;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const AUTH_RECHECK_ON_FOCUS_MS = 10 * 60 * 1000;
  const [isAuthenticated, setAuthenticated] = useState(false);
  const [username, setUsername] = useState<string | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const isCheckingRef = useRef(false);
  const lastCheckedAtRef = useRef<number>(0);

  const check = useCallback(async (options?: { silent?: boolean }) => {
    if (isCheckingRef.current) return;
    isCheckingRef.current = true;
    const silent = !!options?.silent;
    if (!silent) setLoading(true);
    try {
      const resp = await axios.get('/api/auth/status/', { withCredentials: true });
      setAuthenticated(!!resp.data.is_authenticated);
      setUsername(resp.data.username || null);
    } catch (e) {
      setAuthenticated(false);
      setUsername(null);
    } finally {
      lastCheckedAtRef.current = Date.now();
      isCheckingRef.current = false;
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void check();
  }, [check]);

  useEffect(() => {
    const maybeRefreshOnReturn = () => {
      if (document.visibilityState === 'hidden') return;
      const now = Date.now();
      if (now - lastCheckedAtRef.current < AUTH_RECHECK_ON_FOCUS_MS) return;
      void check({ silent: true });
    };

    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        maybeRefreshOnReturn();
      }
    };

    window.addEventListener('focus', maybeRefreshOnReturn);
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => {
      window.removeEventListener('focus', maybeRefreshOnReturn);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [check]);

  const login = async (username: string, password: string) => {
    setLastError(null);
    try {
      const csrftoken = getCookie('csrftoken');
      const resp = await axios.post(
        '/api/auth/login/',
        { username, password },
        { withCredentials: true, headers: { 'X-CSRFToken': csrftoken || '' } }
      );
      if (resp.data.ok) {
        setAuthenticated(true);
        setUsername(resp.data.username);
        setLastError(null);
        lastCheckedAtRef.current = Date.now();
        return true;
      }
    } catch (e: any) {
      const apiError = e?.response?.data?.error;
      if (apiError === 'email_not_verified') {
        setLastError('Please verify your email before logging in.');
      } else if (apiError === 'invalid_credentials') {
        setLastError('Invalid credentials');
      } else {
        setLastError(e?.response?.data?.detail || 'Login failed');
      }
    }
    return false;
  };

  const logout = async () => {
    try {
      const csrftoken = getCookie('csrftoken');
      await axios.post('/api/auth/logout/', {}, { withCredentials: true, headers: { 'X-CSRFToken': csrftoken || '' } });
    } catch (e) {
      // ignore
    }
    setAuthenticated(false);
    setUsername(null);
    lastCheckedAtRef.current = Date.now();
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, username, lastError, loading, login, logout, refreshAuth: check }}>
      {children}
    </AuthContext.Provider>
  );
};
