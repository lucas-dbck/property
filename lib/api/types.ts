// Shared API types. Backend shapes that are open-ended are kept flexible
// (Record-based) so the UI can render whatever the backend returns.

export interface AuthUser {
  id: string
  email: string
  name?: string
}

export interface AuthResponse {
  token: string
  user: AuthUser
}

// ----- Input template (GET /opportunities/input-template) -----

export type FieldType = "number" | "text" | "select" | "switch" | "percent" | "currency"

export interface TemplateField {
  key: string
  label: string
  type: FieldType
  group?: string // e.g. "Property" | "Finance" | "Operating costs"
  unit?: string // e.g. "€", "%", "m²"
  defaultValue?: string | number | boolean
  options?: { label: string; value: string }[] // for select
  min?: number
  max?: number
  step?: number
  helpText?: string
  required?: boolean
}

export interface InputTemplate {
  fields: TemplateField[]
}

// ----- Inputs / values -----

export type InputValues = Record<string, string | number | boolean>

// ----- Immoweb import (POST /opportunities/imports/immoweb) -----

export interface ImmowebImportResponse {
  // Values to prefill the form with. Treated as STARTING values only.
  values: InputValues
  // True when this came from the preview demo fallback (backend unreachable),
  // not a real listing import. Lets the UI warn the user the numbers are sample data.
  demo?: boolean
  // Optional metadata about the source listing.
  meta?: {
    title?: string
    address?: string
    listingUrl?: string
    imageUrl?: string
  }
}

// ----- Analyze (POST /opportunities/analyze) -----

export interface AnalyzeMetric {
  key: string
  label: string
  value: number
  format: "currency" | "percent" | "number" | "years"
  // Optional qualitative direction for coloring (good/bad/neutral).
  sentiment?: "positive" | "negative" | "neutral"
  description?: string
}

export interface AnalyzeBreakdownItem {
  label: string
  value: number
  format: "currency" | "percent" | "number"
}

export interface AnalyzeResponse {
  // Headline metrics, rendered dynamically.
  metrics: AnalyzeMetric[]
  // Optional cash-flow / cost breakdown.
  breakdown?: AnalyzeBreakdownItem[]
  // Optional overall verdict.
  verdict?: {
    label: string
    sentiment: "positive" | "negative" | "neutral"
  }
}

// ----- Opportunities -----

export interface Opportunity {
  id: string
  title: string
  address?: string
  listingUrl?: string
  imageUrl?: string
  values: InputValues
  analysis?: AnalyzeResponse
  createdAt?: string
  updatedAt?: string
}

export interface CompareRow {
  id: string
  title: string
  address?: string
  metrics: Record<string, AnalyzeMetric>
}

export interface CompareResponse {
  // Metric keys/labels shared across the compared opportunities.
  metricColumns: { key: string; label: string; format: AnalyzeMetric["format"] }[]
  rows: CompareRow[]
}
