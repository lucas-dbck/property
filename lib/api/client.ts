// Typed API client. All requests go through the local proxy (/api/proxy/...),
// which forwards to the real backend. When the backend is unavailable during
// preview (HTTP 503), we fall back to temporary demo data (see ./demo.ts).

import { demoApi } from "./demo"
import type {
  AnalyzeResponse,
  AuthResponse,
  CompareResponse,
  ImmowebImportResponse,
  InputTemplate,
  InputValues,
  Opportunity,
} from "./types"

const TOKEN_KEY = "roi.token"

export function getToken(): string | null {
  if (typeof window === "undefined") return null
  return window.localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return
  if (token) window.localStorage.setItem(TOKEN_KEY, token)
  else window.localStorage.removeItem(TOKEN_KEY)
}

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

// Thrown internally to signal we should use the demo fallback.
class BackendUnavailable extends Error {}

interface RequestOptions {
  method?: string
  body?: unknown
  // Whether a 503 (backend unavailable) should throw BackendUnavailable so the
  // caller can use demo data. Defaults to true.
  allowDemoFallback?: boolean
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, allowDemoFallback = true } = opts
  const headers: Record<string, string> = { "content-type": "application/json" }
  const token = getToken()
  if (token) headers.authorization = `Bearer ${token}`

  let res: Response
  try {
    res = await fetch(`/api/proxy${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    if (allowDemoFallback) throw new BackendUnavailable()
    throw new ApiError("Network error.", 0)
  }

  if (res.status === 503 && allowDemoFallback) {
    throw new BackendUnavailable()
  }

  const text = await res.text()
  const data = text ? JSON.parse(text) : null

  if (!res.ok) {
    const message = (data && (data.message || data.error)) || `Request failed (${res.status}).`
    throw new ApiError(message, res.status)
  }

  return data as T
}

// Helper: try the real backend, fall back to a demo producer on unavailability.
async function withFallback<T>(real: () => Promise<T>, demo: () => T): Promise<T> {
  try {
    return await real()
  } catch (err) {
    if (err instanceof BackendUnavailable) return demo()
    throw err
  }
}

export const api = {
  // ----- Auth -----
  register: (input: { email: string; password: string; name?: string }) =>
    withFallback(
      () => request<AuthResponse>("/auth/register", { method: "POST", body: input }),
      () => ({ token: `demo-token-${Date.now()}`, user: { id: "demo-user", email: input.email, name: input.name } }),
    ),

  login: (input: { email: string; password: string }) =>
    withFallback(
      () => request<AuthResponse>("/auth/login", { method: "POST", body: input }),
      () => ({ token: `demo-token-${Date.now()}`, user: { id: "demo-user", email: input.email } }),
    ),

  // ----- Template -----
  getInputTemplate: () =>
    withFallback(
      () => request<InputTemplate>("/opportunities/input-template"),
      () => demoApi.getTemplate(),
    ),

  // ----- Immoweb import -----
  importImmoweb: (listingUrl: string) =>
    withFallback(
      () => request<ImmowebImportResponse>("/opportunities/imports/immoweb", { method: "POST", body: { url: listingUrl } }),
      () => demoApi.importImmoweb(),
    ),

  // ----- Analyze -----
  analyze: (values: InputValues) =>
    withFallback(
      () => request<AnalyzeResponse>("/opportunities/analyze", { method: "POST", body: { values } }),
      () => demoApi.analyze(values),
    ),

  // ----- Opportunities -----
  listOpportunities: () =>
    withFallback(
      () => request<Opportunity[]>("/opportunities"),
      () => demoApi.listOpportunities(),
    ),

  createOpportunity: (input: Partial<Opportunity>) =>
    withFallback(
      () => request<Opportunity>("/opportunities", { method: "POST", body: input }),
      () => demoApi.createOpportunity(input),
    ),

  updateOpportunity: (id: string, patch: Partial<Opportunity>) =>
    withFallback(
      () => request<Opportunity>(`/opportunities/${id}`, { method: "PATCH", body: patch }),
      () => demoApi.updateOpportunity(id, patch),
    ),

  compare: (ids?: string[]) =>
    withFallback(
      () => request<CompareResponse>(`/opportunities/compare${ids?.length ? `?ids=${ids.join(",")}` : ""}`),
      () => demoApi.compare(),
    ),
}
