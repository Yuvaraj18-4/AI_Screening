const API_BASE = "/api";

export interface ApiError {
  status: number;
  message: string;
  detail?: unknown;
}

/**
 * Fetch wrapper: prepends /api, sends credentials, normalises errors.
 * Redirects to /login on 401 (unless on /login or /auth/me).
 */
export async function apiClient<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE}${path}`;

  const headers: Record<string, string> = {
    "X-Requested-With": "XMLHttpRequest",
  };

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  if (options.headers) {
    Object.assign(headers, options.headers);
  }

  const res = await fetch(url, {
    ...options,
    credentials: "include",
    headers,
  });

  if (res.status === 401) {
    if (!window.location.pathname.startsWith("/login") && path !== "/auth/me") {
      window.location.href = "/login";
    }
    const err: ApiError = {
      status: 401,
      message: "Authentication required",
    };
    throw err;
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const err: ApiError = {
      status: res.status,
      message: (typeof body.detail === "string" ? body.detail : "") || res.statusText,
      detail: body,
    };
    throw err;
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}
