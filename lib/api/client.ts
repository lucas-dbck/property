// Typed API client. All requests go through the local proxy (/api/proxy/...),
// which forwards to the real backend. When the backend is unavailable during
// preview (HTTP 503), we fall back to temporary demo data (see ./demo.ts).

import { demoApi } from "./demo"
import type {
  AnalyzeResponse,
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

function analysisNumber(analysis: Record<string, number | string | string[]>, key: string): number {
  return toNumber(analysis[key])
}

const importBasics = [
  { key: "purchase_price", backendKeys: ["purchase_price", "price"], label: "Price" },
  { key: "city", backendKeys: ["city", "locality"], label: "City" },
  { key: "area_sqm", backendKeys: ["area_sqm", "living_area", "size_sqm"], label: "Living area" },
  { key: "bedrooms", backendKeys: ["bedrooms"], label: "Bedrooms" },
  { key: "energy_score", backendKeys: ["energy_score", "epc_score", "epcScore"], label: "Energy score" },
]

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

function formatApiMessage(value: unknown): string | null {
  if (!value) return null
  if (typeof value === "string") return value
  if (Array.isArray(value)) {
    const messages = value.map(formatApiMessage).filter(Boolean)
    return messages.length ? messages.join(" ") : null
  }
  if (typeof value === "object") {
    const obj = value as Record<string, unknown>
    if (typeof obj.msg === "string") return obj.msg
    return formatApiMessage(obj.detail ?? obj.message ?? obj.error) ?? JSON.stringify(obj)
  }
  return String(value)
}

async function parseResponse<T>(res: Response, allowDemoFallback: boolean): Promise<T> {
  if (res.status === 503 && allowDemoFallback) throw new BackendUnavailable()

  const text = await res.text()
  let data: unknown = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }

  if (!res.ok) {
    const source = data && typeof data === "object" ? (data as Record<string, unknown>) : null
    const message = formatApiMessage(source?.detail ?? source?.message ?? source?.error ?? data) || `Request failed (${res.status}).`
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
    if (err instanceof ApiError) throw err
    if (allowDemoFallback) throw new BackendUnavailable()
    throw new ApiError("Network error.", 0)
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
    if (err instanceof ApiError) throw err
    if (allowDemoFallback) throw new BackendUnavailable()
    throw new ApiError("Network error.", 0)
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

function percentInputToDecimal(value: unknown, fallbackPercent = 0): number {
  return toNumber(value, fallbackPercent) / 100
}

function rateToPercentInput(value: unknown, fallback = 0): number {
  const n = toNumber(value, fallback)
  return n > 0 && n <= 1 ? Number((n * 100).toFixed(2)) : n
}

function firstValue(source: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = source[key]
    if (value !== undefined && value !== null && value !== "") return value
  }
  return undefined
}

function hasUsefulValue(value: unknown): boolean {
  if (value === undefined || value === null || value === "") return false
  if (typeof value === "number") return value !== 0
  if (typeof value === "string") return value.trim() !== "" && value !== "0"
  return true
}

function backendToInputValues(data: Record<string, unknown> = {}): InputValues {
  const price = toNumber(firstValue(data, ["purchase_price", "price", "purchasePrice"]))
  const downPayment = firstValue(data, ["down_payment", "downPayment"])
  return {
    source_url: String(firstValue(data, ["source_url", "listing_url", "listingUrl"]) ?? ""),
    purchase_price: price,
    city: String(firstValue(data, ["city", "locality"]) ?? ""),
    area_sqm: toNumber(firstValue(data, ["area_sqm", "living_area", "size_sqm", "livingArea"])),
    bedrooms: toNumber(data.bedrooms),
    bathrooms: toNumber(data.bathrooms),
    property_type: String(firstValue(data, ["property_type", "propertyType"]) ?? ""),
    energy_score: String(firstValue(data, ["energy_score", "epc_score", "epcScore"]) ?? ""),
    condition: String(firstValue(data, ["condition"]) ?? ""),
    monthly_rent: toNumber(firstValue(data, ["monthly_rent", "estimated_rent", "expected_monthly_rent", "monthlyRent"])),
    renovation_cost: toNumber(firstValue(data, ["renovation_cost", "renovationBudget"])),
    purchase_costs: toNumber(firstValue(data, ["purchase_costs", "closing_costs"])),
    annual_operating_costs: toNumber(firstValue(data, ["annual_operating_costs", "operating_costs"])),
    operating_cost_rate: rateToPercentInput(firstValue(data, ["operating_cost_rate", "operatingCostRate"]), 15),
    vacancy_rate: rateToPercentInput(firstValue(data, ["vacancy_rate", "vacancyRate"]), 5),
    down_payment: downPayment !== undefined ? toNumber(downPayment) : 0,
    interest_rate: toNumber(firstValue(data, ["interest_rate", "interestRate"])),
    loan_years: toNumber(firstValue(data, ["loan_years", "loanTermYears"]), 25),
    monthly_debt_service: toNumber(firstValue(data, ["monthly_debt_service", "monthly_loan_payment", "monthlyLoanPayment"])),
  }
}

function inputToBackendData(values: InputValues): Record<string, unknown> {
  const purchasePrice = toNumber(firstValue(values, ["purchase_price", "purchasePrice", "price"]))
  const downPayment = firstValue(values, ["down_payment", "downPayment"])
  return {
    purchase_price: purchasePrice,
    source_url: firstValue(values, ["source_url", "listingUrl"]),
    city: firstValue(values, ["city"]),
    area_sqm: firstValue(values, ["area_sqm", "livingArea"]),
    bedrooms: firstValue(values, ["bedrooms"]),
    bathrooms: firstValue(values, ["bathrooms"]),
    property_type: firstValue(values, ["property_type", "propertyType"]),
    energy_score: firstValue(values, ["energy_score", "epcScore"]),
    monthly_rent: firstValue(values, ["monthly_rent", "monthlyRent"]),
    renovation_cost: firstValue(values, ["renovation_cost", "renovationBudget"]),
    purchase_costs: firstValue(values, ["purchase_costs", "closing_costs"]),
    annual_operating_costs: firstValue(values, ["annual_operating_costs", "operatingCosts"]),
    operating_cost_rate: percentInputToDecimal(firstValue(values, ["operating_cost_rate", "operatingCostRate"]), 15),
    vacancy_rate: percentInputToDecimal(firstValue(values, ["vacancy_rate", "vacancyRate"]), 5),
    down_payment: downPayment !== undefined ? toNumber(downPayment) : undefined,
    interest_rate: firstValue(values, ["interest_rate", "interestRate"]),
    loan_years: firstValue(values, ["loan_years", "loanTermYears"]),
    monthly_debt_service: firstValue(values, ["monthly_debt_service", "monthly_loan_payment", "monthlyLoanPayment"]),
    condition: firstValue(values, ["condition"]),
  }
}

function buildImportFeedback(data: Record<string, unknown>, values: InputValues): ImmowebImportResponse["feedback"] {
  const extracted = Array.isArray(data.extracted_fields) ? data.extracted_fields.map(String) : []
  const found = importBasics
    .filter((field) => field.backendKeys.some((key) => extracted.includes(key)) || hasUsefulValue(values[field.key]))
    .map((field) => field.label)
  const missing = importBasics.filter((field) => !found.includes(field.label)).map((field) => field.label)
  const status = String(data.extraction_status ?? "") || undefined
  const method = String(data.extraction_method ?? "") || undefined
  const aiStatus = String(data.ai_extraction_status ?? "")
  const aiError = String(data.ai_error ?? "")
  const message = status === "failed"
    ? `Import failed: ${formatApiMessage(data.error) || "the backend could not read this listing."}`
    : aiStatus === "failed"
    ? `AI extraction failed: ${aiError || "check OpenAI API credits or billing."}`
    : aiStatus === "not_configured"
      ? "AI extraction is not active, so the app used the free parser."
      : missing.length > 0
        ? "Some basics still need manual entry."
        : "Review the imported values before trusting ROI."

  return { found, missing, status, method, message }
}

function metric(
  key: string,
  label: string,
  value: unknown,
  format: "currency" | "percent" | "number" | "years",
  description?: string,
  sentiment?: "positive" | "negative" | "neutral",
) {
  const numericValue = toNumber(value)
  return {
    key,
    label,
    value: numericValue,
    format,
    sentiment: sentiment ?? (numericValue > 0 ? "positive" as const : numericValue < 0 ? "negative" as const : "neutral" as const),
    description,
  }
}

function backendAnalysisToFrontend(response: BackendAnalysis): AnalyzeResponse {
  const a = response.analysis
  const totalCashInvested = analysisNumber(a, "total_cash_invested") || analysisNumber(a, "down_payment")
  return {
    verdict: {
      label: toNumber(a.monthly_cash_flow) >= 0 ? "Positive cash flow" : "Negative cash flow",
      sentiment: toNumber(a.monthly_cash_flow) >= 0 ? "positive" : "negative",
    },
    metrics: [
      metric("cashOnCash", "ROI", a.cash_on_cash_return, "percent", "Formula: annual net profit / total cash invested x 100. Annual net profit is rent after operating costs and loan payments. Total cash invested is your own payment."),
      metric("estimatedMonthlyRent", "Estimated rent", a.estimated_monthly_rent, "currency", "The monthly rent used in the ROI calculation. If you leave rent empty, the app estimates it from city, area, bedrooms, energy score, and condition."),
      metric("monthlyLoanPayment", "Monthly loan cost", a.monthly_debt_service, "currency", "Estimated mortgage payment per month based on total project cost, own payment, interest rate, and loan years.", "neutral"),
      metric("monthlyCashFlow", "Monthly cash flow", a.monthly_cash_flow, "currency", "Estimated money left each month after operating costs and monthly loan payment."),
      metric("grossYield", "Gross yield", a.gross_yield, "percent", "Standard formula: annual rent / purchase price. This ignores costs and financing."),
      metric("netYield", "Net yield", a.net_yield, "percent", "Standard formula: net operating income / total investment. Total investment includes purchase price, purchase costs, and renovation cost."),
      metric("roiScore", "Investment score", a.roi_score, "number", "Internal 0-100 ranking helper, not an official ROI formula."),
    ],
    breakdown: [
      { label: "Annual rent", value: toNumber(a.annual_rent), format: "currency" },
      { label: "Operating costs", value: -toNumber(a.annual_operating_costs), format: "currency" },
      { label: "Net operating income", value: toNumber(a.net_operating_income), format: "currency" },
      { label: "Total project cost", value: toNumber(a.total_investment), format: "currency" },
      { label: "Total cash invested", value: totalCashInvested, format: "currency" },
      { label: "Own payment", value: toNumber(a.down_payment), format: "currency" },
      { label: "Loan amount", value: toNumber(a.loan_amount), format: "currency" },
      { label: "Monthly loan payment", value: -toNumber(a.monthly_debt_service), format: "currency" },
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
  const values = backendToInputValues({ ...data, source_url: item.source_url })
  delete values.monthly_rent
  delete values.estimated_rent
  delete values.renovation_cost
  delete values.annual_operating_costs
  return {
    values,
    feedback: buildImportFeedback(data, values),
    meta: {
      title: item.title,
      listingUrl: item.source_url || undefined,
      address: String(firstValue(data, ["address", "city", "postcode"]) ?? ""),
      imageUrl: Array.isArray(data.images) ? String(data.images[0] ?? "") : undefined,
    },
  }
}

function defaultOptionsForField(key: string) {
  if (key === "energy_score") {
    return ["A+", "A", "B", "C", "D", "E", "F", "G"].map((value) => ({ label: value, value }))
  }
  if (key === "condition") {
    return ["poor", "average", "renovated", "new"].map((value) => ({ label: value[0].toUpperCase() + value.slice(1), value }))
  }
  return undefined
}

function backendTemplateToFrontend(template: { fields: Array<Record<string, unknown>> }): InputTemplate {
  const hidden = new Set([
    "amenities",
    "closing_cost_rate",
    "annual_taxes",
    "annual_insurance",
    "monthly_maintenance",
    "management_fee_rate",
  ])
  return {
    fields: template.fields
      .filter((field) => !hidden.has(String(field.key)))
      .map((field) => {
        const key = String(field.key)
        return {
          key,
          label: String(field.label),
          type: field.value_type === "list" ? "text" : field.value_type === "url" ? "text" : (field.value_type as any),
          group: String(field.group ?? ""),
          defaultValue: field.default as string | number | boolean | undefined,
          options: Array.isArray(field.options) ? field.options as { label: string; value: string }[] : defaultOptionsForField(key),
          helpText: String(field.description ?? ""),
          required: Boolean(field.required_for_roi),
        }
      }),
  }
}

function backendCompareToFrontend(compare: BackendCompare): CompareResponse {
  return {
    metricColumns: [
      { key: "cashOnCash", label: "ROI", format: "percent" },
      { key: "monthlyCashFlow", label: "Monthly cash flow", format: "currency" },
      { key: "grossYield", label: "Gross yield", format: "percent" },
      { key: "netYield", label: "Net yield", format: "percent" },
      { key: "roiScore", label: "Investment score", format: "number" },
    ],
    rows: compare.items.map((item) => ({
      id: String(item.opportunity_id),
      title: item.title,
      metrics: {
        roiScore: metric("roiScore", "Investment score", item.roi_score, "number"),
        monthlyCashFlow: metric("monthlyCashFlow", "Monthly cash flow", item.monthly_cash_flow, "currency"),
        grossYield: metric("grossYield", "Gross yield", item.gross_yield, "percent"),
        netYield: metric("netYield", "Net yield", item.net_yield, "percent"),
        cashOnCash: metric("cashOnCash", "ROI", item.cash_on_cash_return, "percent"),
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
          allowDemoFallback: false,
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
          false,
        )
        setToken(token.access_token)
        const user = await request<BackendUser>("/auth/me", { allowDemoFallback: false })
        return { token: token.access_token, user: backendUserToAuthUser(user) }
      },
      () => ({ token: `demo-token-${Date.now()}`, user: { id: "demo-user", email: input.email } }),
    ),

  me: () =>
    withFallback(
      async () => backendUserToAuthUser(await request<BackendUser>("/auth/me", { allowDemoFallback: false })),
      () => {
        throw new ApiError("No saved session.", 401)
      },
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

  importListingText: (input: { text: string; sourceUrl?: string }) =>
    withFallback(
      async () => backendImportToFrontend(await request<BackendOpportunity>("/opportunities/imports/text", {
        method: "POST",
        body: { text: input.text, source_url: input.sourceUrl },
      })),
      () => demoApi.importImmoweb(input.sourceUrl || input.text.slice(0, 80)),
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

  deleteOpportunity: (id: string) =>
    withFallback(
      async () => {
        await request<void>(`/opportunities/${id}`, { method: "DELETE", allowDemoFallback: false })
      },
      () => demoApi.deleteOpportunity(id),
    ),

  compare: (_ids?: string[]) =>
    withFallback(
      async () => backendCompareToFrontend(await request<BackendCompare>("/opportunities/compare")),
      () => demoApi.compare(),
    ),
}
