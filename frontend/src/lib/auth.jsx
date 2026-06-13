import { createContext, useContext, useEffect, useState } from "react";
import { api, setAuthToken, clearAuthToken } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);   // null = unknown, false = unauthenticated, object = signed in
  const [loading, setLoading] = useState(true);

  const bootstrap = async () => {
    const token = localStorage.getItem("ps_token");
    if (!token) { setUser(false); setLoading(false); return; }
    setAuthToken(token);
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch {
      localStorage.removeItem("ps_token");
      clearAuthToken();
      setUser(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { bootstrap(); }, []);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem("ps_token", data.access_token);
    setAuthToken(data.access_token);
    setUser(data.user);
    return data.user;
  };

  const logout = () => {
    localStorage.removeItem("ps_token");
    clearAuthToken();
    setUser(false);
  };

  const has = (...roles) => user && roles.includes(user.role);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, has }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
