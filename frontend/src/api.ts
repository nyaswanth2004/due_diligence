export type DocumentStatus = "pending" | "processing" | "ready" | "failed";

export interface DocumentItem {
  id: string;
  filename: string;
  doc_type: string;
  page_count: number;
  status: DocumentStatus;
  error_message: string | null;
  chunk_count: number;
  created_at: string;
}

export interface EvidenceChunk {
  chunk_id: string;
  document_id: string;
  filename: string;
  doc_type: string;
  page_number: number;
  section: string;
  content: string;
  score: number;
}

export interface QAResponse {
  answer: string;
  context: EvidenceChunk[];
  citations: EvidenceChunk[];
  dropped_citations: string[];
  unanswerable: boolean;
}

export interface SearchResponse {
  query: string;
  total: number;
  results: EvidenceChunk[];
  search_time_ms: number;
}

export interface RatioRow {
  name: string;
  value: number;
  formula: string;
  interpretation: string;
  risk_level: "low" | "medium" | "high" | "info";
  source_chunk_ids: string[];
}

export interface TrendRow {
  metric: string;
  current: number;
  prior: number | null;
  direction: string;
  note: string;
  chunk_id: string;
}

export interface RedFlagRow {
  severity: string;
  finding: string;
  evidence: string;
  chunk_id: string;
  page: number;
}

export interface ChecklistRow {
  item: string;
  status: "present" | "missing";
  note: string;
}

export interface ReportPayload {
  title: string;
  generated_on: string;
  document_count: number;
  summary: string;
  executive_summary: string;
  sections: {
    financial_analysis?: (RatioRow | TrendRow)[];
    risk?: RedFlagRow[];
    compliance?: (ChecklistRow | { completion_pct: number })[];
  };
  financial_metrics: Record<string, { label: string; value: number; prior_value: number | null; filename: string; page: number }>;
  source_chunk_ids: string[];
}

export interface ReportItem {
  id: string;
  document_ids: string[];
  title: string;
  summary: string;
  executive_summary: string;
  data: ReportPayload;
  created_at: string;
}

export interface CurrentUser {
  id: string;
  username: string;
  email: string;
  role: "admin" | "analyst" | "viewer";
  is_active: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: CurrentUser;
}

export interface AuditEntry {
  id: string;
  user_id: string | null;
  username: string;
  action: string;
  resource_type: string;
  resource_id: string;
  details: Record<string, unknown>;
  ip_address: string;
  created_at: string;
}

async function request<T>(path: string, init?: RequestInit, timeoutMs = 45000): Promise<T> {
  const token = localStorage.getItem("veritasiq_token");
  const headers = new Headers(init?.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let response: Response;
  try {
    response = await fetch(path, { ...init, headers, signal: controller.signal });
  } catch (err) {
    const aborted = err instanceof Error && err.name === "AbortError";
    throw new Error(
      aborted
        ? "The server did not respond in time. Please try again."
        : "Could not reach the server. Is it running?"
    );
  } finally {
    clearTimeout(timer);
  }
  if (response.status === 401) {
    localStorage.removeItem("veritasiq_token");
    localStorage.removeItem("veritasiq_user");
    window.dispatchEvent(new Event("veritasiq:unauthorized"));
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (body.detail) detail = body.detail;
    } catch {
      /* ignore non-JSON error bodies */
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export function login(username: string, password: string): Promise<LoginResponse> {
  return request("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
}

export function fetchMe(): Promise<CurrentUser> {
  return request("/api/v1/auth/me");
}

export function listAudit(action?: string, limit = 100): Promise<{ total: number; items: AuditEntry[] }> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (action) params.set("action", action);
  return request(`/api/v1/audit?${params.toString()}`);
}

export interface UserOut {
  id: string;
  username: string;
  email: string;
  role: "admin" | "analyst" | "viewer";
  is_active: boolean;
  created_at: string;
}

export function listUsers(search?: string): Promise<{ total: number; items: UserOut[] }> {
  const params = new URLSearchParams({ limit: "200" });
  if (search) params.set("search", search);
  return request(`/api/v1/users?${params.toString()}`);
}

export function createUser(input: {
  username: string;
  email: string;
  password: string;
  role: string;
}): Promise<UserOut> {
  return request("/api/v1/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function updateUser(
  id: string,
  input: { role?: string; is_active?: boolean }
): Promise<UserOut> {
  return request(`/api/v1/users/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function deleteUser(id: string): Promise<void> {
  return request(`/api/v1/users/${id}`, { method: "DELETE" });
}

export function listDocuments(status?: string): Promise<{ total: number; items: DocumentItem[] }> {
  const query = status ? `?status_filter=${encodeURIComponent(status)}` : "";
  return request(`/api/v1/documents${query}`);
}

export function uploadDocument(file: File): Promise<DocumentItem> {
  const form = new FormData();
  form.append("file", file);
  return request("/api/v1/documents", { method: "POST", body: form });
}

export function deleteDocument(id: string): Promise<void> {
  return request(`/api/v1/documents/${id}`, { method: "DELETE" });
}

export function search(q: string, topK = 8, documentId?: string): Promise<SearchResponse> {
  const params = new URLSearchParams({ q, top_k: String(topK) });
  if (documentId) params.set("document_id", documentId);
  return request(`/api/v1/search?${params.toString()}`);
}

export function askQuestion(
  question: string,
  documentIds?: string[],
  history: { role: "user" | "assistant"; content: string }[] = []
): Promise<QAResponse> {
  return request(
    "/api/v1/qa",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, document_ids: documentIds, history }),
    },
    180000
  );
}

export function generateReport(documentIds: string[]): Promise<ReportPayload> {
  return request(
    "/api/v1/reports/generate",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_ids: documentIds }),
    },
    600000
  );
}

export function listReports(): Promise<{ total: number; items: ReportItem[] }> {
  return request("/api/v1/reports");
}

export function getReport(id: string): Promise<ReportItem> {
  return request(`/api/v1/reports/${id}`);
}
