export interface CurrentUser {
  id: string;
  username: string;
  email: string;
  role: "admin" | "analyst" | "viewer";
  is_active: boolean;
}

const TOKEN_KEY = "veritasiq_token";
const USER_KEY = "veritasiq_user";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser(): CurrentUser | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as CurrentUser;
  } catch {
    return null;
  }
}

export function setSession(token: string, user: CurrentUser): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function isAdmin(): boolean {
  return getUser()?.role === "admin";
}

export function isAnalyst(): boolean {
  const role = getUser()?.role;
  return role === "admin" || role === "analyst";
}
