import { createContext, useContext, useEffect, useState } from 'react';
import { authService } from '../services/authService.js';

const AuthContext = createContext(null);
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [connectionError, setConnectionError] = useState('');
  useEffect(() => {
    let active = true;
    authService.me().then(value => { if (active) setUser(value); })
      .catch(error => { if (active && error.status !== 401) setConnectionError(error.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  async function login(data) {
    await authService.login(data);
    setUser(await authService.me());
    setConnectionError('');
  }
  async function logout() {
    try { await authService.logout(); } finally { setUser(null); }
  }
  return <AuthContext.Provider value={{ user, loading, login, logout, connectionError }}>{children}</AuthContext.Provider>;
}
export const useAuth = () => useContext(AuthContext);
