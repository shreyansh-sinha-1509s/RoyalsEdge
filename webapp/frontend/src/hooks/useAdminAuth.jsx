import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { api } from '../services/api.js';

const AdminAuthContext = createContext(null);

export function AdminAuthProvider({ children }) {
  const [admin, setAdmin] = useState(null);
  const [checking, setChecking] = useState(true);

  const refreshSession = useCallback(async () => {
    setChecking(true);
    try {
      const res = await api.adminMe();
      setAdmin(res?.data?.admin ?? null);
    } catch {
      setAdmin(null);
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    refreshSession();
  }, [refreshSession]);

  const login = useCallback(async (email, password) => {
    const res = await api.adminLogin(email, password);
    setAdmin(res?.data?.admin ?? null);
    return res?.data?.admin;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.adminLogout();
    } finally {
      setAdmin(null);
    }
  }, []);

  return (
    <AdminAuthContext.Provider value={{ admin, checking, login, logout, refreshSession }}>
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth() {
  const ctx = useContext(AdminAuthContext);
  if (!ctx) throw new Error('useAdminAuth must be used inside AdminAuthProvider');
  return ctx;
}

