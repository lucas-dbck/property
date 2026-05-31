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

type BackendUser = { id: number; email: string; full_name?: string }
type BackendToken = { access_token: string; token_type: string }
type BackendOpportunity = {
  id: number
  title: string
  source_url?: string | null
  imported_data?: Record<string, unknown>
  user_overrides?: Record<string, unknown>
  final_data?: Record<string, unknown>
  created_at?: string
  updated_at?: string
}
type BackendAnalysis = { final_data?: Record<string, unknown>; analysis: Record<string, number | string | string[]> }

type BackendCompare = {
  items: Array<{
    opportunity_id: number
    title: string
    roi_score: number
    estimated_monthly_rent: number
    gross_yield: number
    net_yield: number
    monthly_cash_flow: number
    cash_on_cash_return: number
    total_investment: number
  }>
}

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

class BackendUnavailable extends Error {}

let demoMode = false
const demoModeListeners = new Set<() => void>()

export function isDemoMode(): boolean {
  return demoMode
}

export function subscribeDemoMode(listener: () => void): () => void {
  demoModeListeners.add(listener)
  return () => demoModeListeners.delete(listener)
}

function markDemoMode() {
  if (demoMode) return
  demoMode = true
  demoModeListeners.forEach((l) => l())
}

interface RequestOptions {
  method?: string
  body?: unknown
  allowDemoFallback?: boolean
}

async function parseResponse<T>(res: Response, allowDemoFallback: boolean): Promise<T> {
  if (res.status === 503 && allowDemoFallback) {
    throw new BackendUnavailable()
  }

  const text = await res.text()
  const data = text ? JSON.parse(text) : null

  if (!res.ok) {
    const message = (data && (data.detail || data.message || data.error)) || `Request failed (${res.status}).`
    throw new ApiError(message, res.status)
  }

  return data as T
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, allowDemoFallback = true } = opts
  const headers: Record<string, string> = { "content-type": "application/json" }
  const token = getToken()
  if (token) headers.authorization = `Bearer ${token}`

  try {
    const res = await fetch(`/api/proxy${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
    return await parseResponse<T>(res, allowDemoFallback)
  } catch (err) {
    if (err instanceof BackendUnavailable) throw err
    if (allowDemoFallback) throw new BackendUnavailable()
    throw err instanceof ApiError ? err : new ApiError("Network error.", 0)
  }
}

async function requestForm<T>(path: string, body: URLSearchParams, allowDemoFallback = true): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = { "content-type": "application/x-www-form-urlencoded" }
  if (token) headers.authorization = `Bearer ${token}`

  try {
    const res = await fetch(`/api/proxy${path}`, { method: "POST", headers, body })
    return await parseResponse<T>(res, allowDemoFallback)
  } catch (err) {
    if (err instanceof BackendUnavailable) throw err
    if (allowDemoFallback) throw new BackendUnavailable()
    throw err instanceof ApiError ? err : new ApiError("Network error.", 0)
  }
}

async function withFallback<T>(real: () => Promise<T>, demo: () => T): Promise<T> {
  try {
    return await real()
  } catch (err) {
    if (err instanceof BackendUnavailable) {
      markDemoMode()
      return demo()
    }
    throw err
  }
}

function backendUserToAuthUser(user: BackendUser) {
  return { id: String(user.id), email: user.email, name: user.full_name }
}

function toNumber(value: unknown, fallback = 0): number {
  const n = typeof value === "number" ? value : Number.parseFloat(String(value ?? ""))
  return Number.isFinite(n) ? n : fallback
}

function firstValue(source: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = source[key]
    if (value !== undefined && value !== null && value !== "") return value
  }
  return undefined
}

function backendToInputValues(data: Record<string, unknown> = {}): InputValues {
  return {
    purchasePrice: toNumber(firstValue(data, ["purchase_price", "price"])),
    livingArea: toNumber(firstValue(data, ["area_sqm", "living_area", "size_sqm"])),
    bedrooms: toNumber(data.bedrooms),
    epcScore: String(firstValue(data, ["energy_score", "epc_score"]) ?? ""),
    monthlyRent: toNumber(firstValue(data, ["monthly_rent", "estimated_rent", "expected_monthly_rent"])),
    renovationBudget: toNumber(data.renovation_cost),
    vacancyRate: toNumber(data.vacancy_rate, 0.05) * 100,
    downPaymentRate: data.down_payment && data.purchase_price ? (toNumber(data.down_payment) / toNumber(data.purchase_price)) * 100 : 20,
    interestRate: toNumber(data.interest_rate),
    loanTermYears: toNumber(data.loan_years, 25),
    annualInsurance: toNumber(data.annual_insurance, 600),
    annualPropertyTax: toNumber(firstValue(data, ["annual_taxes", "property_tax"])),
    annualMaintenance: toNumber(data.monthly_maintenance) * 12,
    managementRate: toNumber(data.management_fee_rate) * 100,
    registrationTaxRate: toNumber(data.closing_cost_rate, 0.12) * 100,
  }
}

function inputToBackendData(values: InputValues): Record<string, unknown> {
  const purchasePrice = toNumber(values.purchasePrice)
  return {
    purchase_price: purchasePrice,
    city: values.city,
    area_sqm: values.livingArea,
    bedrooms: values.bedrooms,
    energy_score: values.epcScore,
    monthly_rent: values.monthlyRent,
    renovation_cost: values.renovationBudget,
    closing_cost_rate: toNumber(values.registrationTaxRate) / 100,
    vacancy_rate: toNumber(values.vacancyRate) / 100,
    down_payment: purchasePrice * (toNumber(values.downPaymentRate) / 100),
    interest_rate: values.interestRate,
    loan_years: values.loanTermYears,
    annual_insurance: values.annualInsurance,
    annual_taxes: values.annualPropertyTax,
    monthly_maintenance: toNumber(values.annualMaintenance) / 12,
    management_fee_rate: toNumber(values.managementRate) / 100,
    condition: values.condition,
  }
}

function metric(key: string, label: string, value: unknown, format: "currency" | "percent" | "number" | "years", description?: string) {
  const numericValue = toNumber(value)
  return {
    key,
    label,
    value: numericValue,
    format,
    sentiment: numericValue > 0 ? "positive" as const : numericValue < 0 ? "negative" as const : "neutral" as const,
    description,
  }
}

function backendAnalysisToFrontend(response: BackendAnalysis): AnalyzeResponse {
  const a = response.analysis
  return {
    verdict: {
      label: toNumber(a.monthly_cash_flow) >= 0 ? "Positive cash flow" : "Negative cash flow",
      sentiment: toNumber(a.monthly_cash_flow) >= 0 ? "positive" : "negative",
    },
    metrics: [
      metric("roiScore", "ROI score", a.roi_score, "number"),
      metric("estimatedMonthlyRent", "Estimated rent", a.estimated_monthly_rent, "currency"),
      metric("monthlyCashFlow", "Monthly cash flow", a.monthly_cash_flow, "currency"),
      metric("grossYield", "Gross yield", a.gross_yield, "percent"),
      metric("netYield", "Net yield", a.net_yield, "percent"),
      metric("cashOnCash", "Cash-on-cash", a.cash_on_cash_return, "percent"),
    ],
    breakdown: [
      { label: "Annual rent", value: toNumber(a.annual_rent), format: "currency" },
      { label: "Operating costs", value: -toNumber(a.annual_operating_costs), format: "currency" },
      { label: "Net operating income", value: toNumber(a.net_operating_income), format: "currency" },
      { label: "Monthly debt service", value: -toNumber(a.monthly_debt_service), format: "currency" },
      { label: "Total investment", value: toNumber(a.total_investment), format: "currency" },
    ],
  }
}

function backendOpportunityToFrontend(item: BackendOpportunity): Opportunity {
  const values = backendToInputValues(item.final_data || item.imported_data || {})
  return {
    id: String(item.id),
    title: item.title,
    listingUrl: item.source_url || undefined,
    values,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
  }
}

function backendImportToFrontend(item: BackendOpportunity): ImmowebImportResponse {
  const data = item.final_data || item.imported_data || {}
  return {
    values: backendToInputValues(data),
    meta: {
      title: item.title,
      listingUrl: item.source_url || undefined,
      address: String(firstValue(data, ["address", "city", "postcode"]) ?? ""),
      imageUrl: Array.isArray(data.images) ? String(data.images[0] ?? "") : undefined,
    },
  }
}

function backendTemplateToFrontend(template: { fields: Array<Record<string, unknown>> }): InputTemplate {
  return {
    fields: template.fields.map((field) => ({
      key: String(field.key),
      label: String(field.label),
      type: field.value_type === "list" ? "text" : field.value_type === "url" ? "text" : (field.value_type as any),
      group: String(field.group ?? ""),
      defaultValue: field.default as string | number | boolean | undefined,
      helpText: String(field.description ?? ""),
      required: Boolean(field.required_for_roi),
    })),
  }
}

function backendCompareToFrontend(compare: BackendCompare): CompareResponse {
  return {
    metricColumns: [
      { key: "roiScore", label: "ROI score", format: "number" },
      { key: "monthlyCashFlow", label: "Monthly cash flow", format: "currency" },
      { key: "grossYield", label: "Gross yield", format: "percent" },
      { key: "netYield", label: "Net yield", format: "percent" },
      { key: "cashOnCash", label: "Cash-on-cash", format: "percent" },
    ],
    rows: compare.items.map((item) => ({
      id: String(item.opportunity_id),
      title: item.title,
      metrics: {
        roiScore: metric("roiScore", "ROI score", item.roi_score, "number"),
        monthlyCashFlow: metric("monthlyCashFlow", "Monthly cash flow", item.monthly_cash_flow, "currency"),
        grossYield: metric("grossYield", "Gross yield", item.gross_yield, "percent"),
        netYield: metric("netYield", "Net yield", item.net_yield, "percent"),
        cashOnCash: metric("cashOnCash", "Cash-on-cash", item.cash_on_cash_return, "percent"),
      },
    })),
  }
}

export const api = {
  register: (input: { email: string; password: string; name?: string }) =>
    withFallback(
      async () => {
        const user = await request<BackendUser>("/auth/register", {
          method: "POST",
          body: { email: input.email, password: input.password, full_name: input.name || input.email },
        })
        return { token: "", user: backendUserToAuthUser(user) }
      },
      () => ({ token: `demo-token-${Date.now()}`, user: { id: "demo-user", email: input.email, name: input.name } }),
    ),

  login: (input: { email: string; password: string }) =>
    withFallback(
      async () => {
        const token = await requestForm<BackendToken>(
          "/auth/login",
          new URLSearchParams({ username: input.email, password: input.password }),
        )
        setToken(token.access_token)
        const user = await request<BackendUser>("/auth/me", { allowDemoFallback: false })
        return { token: token.access_token, user: backendUserToAuthUser(user) }
      },
      () => ({ token: `demo-token-${Date.now()}`, user: { id: "demo-user", email: input.email } }),
    ),

  getInputTemplate: () =>
    withFallback(
      async () => backendTemplateToFrontend(await request<{ fields: Array<Record<string, unknown>> }>("/opportunities/input-template")),
      () => demoApi.getTemplate(),
    ),

  importImmoweb: (listingUrl: string) =>
    withFallback(
      async () => backendImportToFrontend(await request<BackendOpportunity>("/opportunities/imports/immoweb", { method: "POST", body: { url: listingUrl } })),
      () => demoApi.importImmoweb(listingUrl),
    ),

  analyze: (values: InputValues) =>
    withFallback(
      async () => backendAnalysisToFrontend(await request<BackendAnalysis>("/opportunities/analyze", { method: "POST", body: { data: inputToBackendData(values) } })),
      () => demoApi.analyze(values),
    ),

  listOpportunities: () =>
    withFallback(
      async () => (await request<BackendOpportunity[]>("/opportunities")).map(backendOpportunityToFrontend),
      () => demoApi.listOpportunities(),
    ),

  createOpportunity: (input: Partial<Opportunity>) =>
    withFallback(
      async () => backendOpportunityToFrontend(await request<BackendOpportunity>("/opportunities", {
        method: "POST",
        body: {
          title: input.title || "Investment opportunity",
          source: input.listingUrl ? "immoweb" : "manual",
          source_url: input.listingUrl,
          imported_data: {},
          user_overrides: inputToBackendData(input.values || {}),
        },
      })),
      () => demoApi.createOpportunity(input),
    ),

  updateOpportunity: (id: string, patch: Partial<Opportunity>) =>
    withFallback(
      async () => backendOpportunityToFrontend(await request<BackendOpportunity>(`/opportunities/${id}`, {
        method: "PATCH",
        body: {
          title: patch.title,
          source_url: patch.listingUrl,
          user_overrides: patch.values ? inputToBackendData(patch.values) : undefined,
        },
      })),
      () => demoApi.updateOpportunity(id, patch),
    ),

  compare: (_ids?: string[]) =>
    withFallback(
      async () => backendCompareToFrontend(await request<BackendCompare>("/opportunities/compare")),
      () => demoApi.compare(),
    ),
}
