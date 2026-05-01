export type CredentialIn = {
  username: string;
  password: string;
  label?: string | null;
};

export type Credential = CredentialIn & { id: number };

export type SitePayload = {
  name: string;
  base_url: string;
  requires_auth: boolean;
  login_url?: string | null;
  notes?: string | null;
  credentials: CredentialIn[];
};

export type SiteSummary = {
  id: number;
  name: string;
  base_url: string;
  requires_auth: boolean;
  login_url: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  credential_count: number;
};

export type SiteDetail = Omit<SiteSummary, "credential_count"> & {
  credentials: Credential[];
};

async function request<T>(url: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init.headers || {}) },
  });
  if (res.status === 204) return null as T;
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const msg = formatError(data) || `${res.status} ${res.statusText}`;
    throw new Error(msg);
  }
  return data as T;
}

function formatError(data: unknown): string | null {
  if (!data || typeof data !== "object") return null;
  const detail = (data as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc || []).join(".")}: ${d.msg}`)
      .join("\n");
  }
  return JSON.stringify(data);
}

export type LLMProvider = "anthropic" | "openai" | "openai_compatible";

export type LLMConfigPayload = {
  provider: LLMProvider;
  api_key: string | null;
  base_url: string | null;
  model: string;
  max_tokens: number;
  temperature: number;
};

export type LLMConfigOut = LLMConfigPayload & { updated_at: string };

export const api = {
  listSites: () => request<SiteSummary[]>("/api/sites"),
  getSite: (id: number) => request<SiteDetail>(`/api/sites/${id}`),
  createSite: (payload: SitePayload) =>
    request<SiteDetail>("/api/sites", { method: "POST", body: JSON.stringify(payload) }),
  updateSite: (id: number, payload: SitePayload) =>
    request<SiteDetail>(`/api/sites/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteSite: (id: number) =>
    request<null>(`/api/sites/${id}`, { method: "DELETE" }),
  getLLMConfig: () =>
    request<LLMConfigOut | null>("/api/settings/llm"),
  upsertLLMConfig: (payload: LLMConfigPayload) =>
    request<LLMConfigOut>("/api/settings/llm", { method: "PUT", body: JSON.stringify(payload) }),
  getDefaultModels: () =>
    request<Record<string, string[]>>("/api/settings/llm/models"),
};
