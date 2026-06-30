import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchMe, login as loginRequest, logout as logoutRequest, register as registerRequest, refreshAccessToken } from "@/api/auth";
import { setAccessToken } from "@/api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState("idle");

  const bootstrap = useCallback(async () => {
    setStatus("loading");
    try {
      const tokenPayload = await refreshAccessToken();
      const access = tokenPayload?.access;
      if (!access) {
        throw new Error("Missing access token");
      }
      setAccessToken(access);
      const me = await fetchMe();
      setUser(me);
      setStatus("ready");
    } catch {
      setAccessToken(null);
      setUser(null);
      setStatus("ready");
    }
  }, []);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  const login = useCallback(
    async (credentials) => {
      const data = await loginRequest(credentials);
      const access = data?.access;
      if (!access) {
        throw new Error("Missing access token");
      }
      setAccessToken(access);
      const me = await fetchMe();
      setUser(me);
      return me;
    },
    []
  );

  const register = useCallback(async (payload) => {
    return registerRequest(payload);
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutRequest();
    } catch {
      setAccessToken(null);
    }
    setUser(null);
    navigate("/login", { replace: true });
  }, [navigate]);

  const refreshUserProfile = useCallback(async (nextUser) => {
    if (nextUser) {
      setUser(nextUser);
      return nextUser;
    }
    const me = await fetchMe();
    setUser(me);
    return me;
  }, []);

  const value = useMemo(
    () => ({
      user,
      isBootstrapping: status === "loading",
      login,
      register,
      logout,
      refreshSession: bootstrap,
      refreshUserProfile,
    }),
    [user, status, login, register, logout, bootstrap, refreshUserProfile]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
