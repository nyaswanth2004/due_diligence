import * as React from "react";
import {
  clearSession,
  getToken,
  getUser,
  setSession,
} from "../auth";
import {
  fetchMe,
  login as apiLogin,
  type CurrentUser,
} from "../api";

interface AuthContextValue {
  user: CurrentUser | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<CurrentUser | null>(() => getUser());
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    async function bootstrap() {
      if (!getToken()) {
        setLoading(false);
        return;
      }
      try {
        const me = await fetchMe();
        setUser(me);
        setSession(getToken()!, me);
      } catch {
        clearSession();
        setUser(null);
      } finally {
        setLoading(false);
      }
    }
    void bootstrap();
  }, []);

  React.useEffect(() => {
    const handler = () => setUser(null);
    window.addEventListener("veritasiq:unauthorized", handler);
    return () => window.removeEventListener("veritasiq:unauthorized", handler);
  }, []);

  const value = React.useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      login: async (username, password) => {
        const res = await apiLogin(username, password);
        setSession(res.access_token, res.user);
        setUser(res.user);
      },
      logout: () => {
        clearSession();
        setUser(null);
      },
      refresh: async () => {
        if (!getToken()) return;
        const me = await fetchMe();
        setUser(me);
        setSession(getToken()!, me);
      },
    }),
    [user, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
