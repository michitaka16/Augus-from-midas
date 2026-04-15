/**
 * API client for Midas backend.
 *
 * Auto-refreshes JWT tokens when they expire so users stay logged in
 * for 7 days (refresh token lifetime). Pages don't need to manage
 * tokens — they just call `account.getProfile()` etc and the client
 * handles auth transparently.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const TOKEN_KEY = "midas_token";
export const REFRESH_KEY = "midas_refresh";

interface ApiOptions {
  method?: string;
  body?: unknown;
  token?: string;
  /** Set to true to skip auto-refresh on 401 (used internally to prevent loops). */
  _noRefresh?: boolean;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

// ── Token helpers ───────────────────────────────────────────

export const tokens = {
  getAccess: (): string =>
    typeof window === "undefined" ? "" : localStorage.getItem(TOKEN_KEY) ?? "",
  getRefresh: (): string =>
    typeof window === "undefined" ? "" : localStorage.getItem(REFRESH_KEY) ?? "",
  set: (access: string, refresh: string) => {
    if (typeof window === "undefined") return;
    localStorage.setItem(TOKEN_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear: () => {
    if (typeof window === "undefined") return;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
  isLoggedIn: (): boolean => {
    if (typeof window === "undefined") return false;
    return !!localStorage.getItem(TOKEN_KEY) && !!localStorage.getItem(REFRESH_KEY);
  },
};

// ── Refresh logic with single-flight to avoid concurrent refreshes ──

let refreshInFlight: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  // Single-flight: if a refresh is already happening, wait for it
  if (refreshInFlight) return refreshInFlight;

  const refresh = tokens.getRefresh();
  if (!refresh) return null;

  refreshInFlight = (async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!res.ok) {
        // Refresh token also expired or invalid — clear all tokens
        tokens.clear();
        return null;
      }
      const data = (await res.json()) as { tokens?: { access_token: string; refresh_token: string } };
      if (data.tokens?.access_token && data.tokens?.refresh_token) {
        tokens.set(data.tokens.access_token, data.tokens.refresh_token);
        return data.tokens.access_token;
      }
      return null;
    } catch {
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

async function request<T>(path: string, opts: ApiOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  // Resolve auth token: explicit override > stored access token (if path needs auth)
  const wantsAuth = opts.token !== undefined || _isAuthedPath(path);
  let useToken = opts.token;
  if (wantsAuth && !useToken) {
    useToken = tokens.getAccess();
  }
  if (useToken) {
    headers["Authorization"] = `Bearer ${useToken}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });

  // 401 → try to refresh once, then retry
  if (res.status === 401 && !opts._noRefresh && wantsAuth) {
    const newAccess = await refreshAccessToken();
    if (newAccess) {
      return request<T>(path, { ...opts, token: newAccess, _noRefresh: true });
    }
    // Refresh failed → propagate 401 so caller can redirect to login
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: res.statusText }));
    throw new ApiError(res.status, error.error ?? "Unknown error");
  }

  return res.json();
}

/** Heuristic: which paths require auth (used to auto-attach stored token). */
function _isAuthedPath(path: string): boolean {
  return (
    path.startsWith("/account") ||
    path.startsWith("/approvals") ||
    path.startsWith("/debate") ||
    path.startsWith("/audit")
  );
}

// ── Signal endpoints (no auth — impersonal publisher) ──

export const signals = {
  getLatest: () => request<{ signals: unknown[] }>("/signals/latest"),
  getPortfolioLatest: (id: string) => request<unknown>(`/signals/${id}/latest`),
  getHistory: (id: string, limit = 52) =>
    request<unknown>(`/signals/${id}/history?limit=${limit}`),
};

// ── Auth endpoints ──

export const auth = {
  signup: (email: string, password: string) =>
    request<unknown>("/auth/signup", {
      method: "POST",
      body: { email, password },
    }),
  login: async (email: string, password: string, mfaToken?: string) => {
    const result = await request<{
      tokens?: { access_token: string; refresh_token: string };
      mfa_required?: boolean;
      error?: string;
    }>("/auth/login", {
      method: "POST",
      body: { email, password, mfa_token: mfaToken },
    });
    if (result.tokens) {
      tokens.set(result.tokens.access_token, result.tokens.refresh_token);
    }
    return result;
  },
  logout: () => {
    tokens.clear();
  },
};

// ── Authenticated endpoints (auto-attach token, auto-refresh on 401) ──

export const account = {
  getProfile: (token?: string) => request<unknown>("/account", { token }),
  updatePortfolio: (token: string | undefined, portfolioId: string) =>
    request<unknown>("/account/portfolio", {
      method: "PUT",
      token,
      body: { model_portfolio_id: portfolioId },
    }),
  updatePreferences: (token: string | undefined, prefs: unknown) =>
    request<unknown>("/account/preferences", {
      method: "PUT",
      token,
      body: prefs,
    }),
};

export const approvals = {
  getPending: (token?: string) =>
    request<{ approvals: unknown[]; count: number }>("/approvals/pending", { token }),
  approve: (token: string | undefined, id: number) =>
    request<unknown>(`/approvals/${id}/approve`, { method: "POST", token }),
  reject: (token: string | undefined, id: number) =>
    request<unknown>(`/approvals/${id}/reject`, { method: "POST", token }),
  hold: (token: string | undefined, id: number) =>
    request<unknown>(`/approvals/${id}/hold`, { method: "POST", token }),
  getHistory: (token?: string) => request<unknown>("/approvals/history", { token }),
};

export const debate = {
  sendMessage: (token: string | undefined, message: string) =>
    request<{ response: unknown }>("/debate/message", {
      method: "POST",
      token,
      body: { message },
    }),
  getHistory: (token?: string) => request<unknown>("/debate/history", { token }),
};

export const backtests = {
  getLatest: (portfolioId: string) =>
    request<unknown>(`/backtests/${portfolioId}/latest`),
  getRun: (runId: number) => request<unknown>(`/backtests/${runId}`),
};

export const regime = {
  getCurrent: () => request<unknown>("/regime/current"),
  getHistory: () => request<unknown>("/regime/history"),
};
