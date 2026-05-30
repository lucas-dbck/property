// Number formatting helpers (EUR / Belgian context).

const eur = new Intl.NumberFormat("nl-BE", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
})

const eurPrecise = new Intl.NumberFormat("nl-BE", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
})

export function formatCurrency(value: number, precise = false): string {
  if (!Number.isFinite(value)) return "—"
  return (precise ? eurPrecise : eur).format(Math.round(value))
}

export function formatPercent(value: number): string {
  if (!Number.isFinite(value)) return "—"
  return `${value.toFixed(1)}%`
}

export function formatYears(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return "—"
  return `${value.toFixed(1)} yrs`
}

export function formatNumber(value: number): string {
  if (!Number.isFinite(value)) return "—"
  return new Intl.NumberFormat("nl-BE").format(value)
}

export function formatMetric(value: number, format: "currency" | "percent" | "number" | "years"): string {
  switch (format) {
    case "currency":
      return formatCurrency(value)
    case "percent":
      return formatPercent(value)
    case "years":
      return formatYears(value)
    default:
      return formatNumber(value)
  }
}
