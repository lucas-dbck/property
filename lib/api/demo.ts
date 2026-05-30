// TEMPORARY demo fallback data.
// Used ONLY when the real backend is unreachable during preview (HTTP 503 from
// the proxy). This entire file can be deleted once the backend is wired up in
// the deployed environment. Keep all mock data isolated here.

import type {
  AnalyzeResponse,
  CompareResponse,
  ImmowebImportResponse,
  InputTemplate,
  InputValues,
  Opportunity,
} from "./types"

export const DEMO_TEMPLATE: InputTemplate = {
  fields: [
    { key: "purchasePrice", label: "Purchase price", type: "currency", group: "Property", unit: "€", defaultValue: 285000, step: 1000, required: true, helpText: "Listing or negotiated price." },
    { key: "livingArea", label: "Living area", type: "number", group: "Property", unit: "m²", defaultValue: 95, step: 1 },
    { key: "bedrooms", label: "Bedrooms", type: "number", group: "Property", unit: "", defaultValue: 2, step: 1 },
    { key: "epcScore", label: "EPC label", type: "select", group: "Property", defaultValue: "C", options: ["A", "B", "C", "D", "E", "F"].map((v) => ({ label: v, value: v })) },
    { key: "registrationTaxRate", label: "Registration tax", type: "percent", group: "Acquisition costs", unit: "%", defaultValue: 12.5, step: 0.5, helpText: "Region-dependent (e.g. 12.5% Wallonia/Brussels)." },
    { key: "notaryFees", label: "Notary & deed fees", type: "currency", group: "Acquisition costs", unit: "€", defaultValue: 4500, step: 100 },
    { key: "renovationBudget", label: "Renovation budget", type: "currency", group: "Acquisition costs", unit: "€", defaultValue: 15000, step: 500 },
    { key: "monthlyRent", label: "Expected monthly rent", type: "currency", group: "Income", unit: "€", defaultValue: 1150, step: 25, required: true },
    { key: "vacancyRate", label: "Vacancy allowance", type: "percent", group: "Income", unit: "%", defaultValue: 5, step: 1 },
    { key: "downPaymentRate", label: "Down payment", type: "percent", group: "Finance", unit: "%", defaultValue: 20, step: 5 },
    { key: "interestRate", label: "Mortgage rate", type: "percent", group: "Finance", unit: "%", defaultValue: 3.4, step: 0.1 },
    { key: "loanTermYears", label: "Loan term", type: "number", group: "Finance", unit: "yrs", defaultValue: 25, step: 1 },
    { key: "annualMaintenance", label: "Annual maintenance", type: "currency", group: "Operating costs", unit: "€", defaultValue: 1200, step: 100 },
    { key: "annualInsurance", label: "Insurance", type: "currency", group: "Operating costs", unit: "€", defaultValue: 350, step: 50 },
    { key: "annualPropertyTax", label: "Property tax (PI)", type: "currency", group: "Operating costs", unit: "€", defaultValue: 900, step: 50 },
    { key: "managementRate", label: "Management fee", type: "percent", group: "Operating costs", unit: "%", defaultValue: 0, step: 1 },
  ],
}

function num(v: string | number | boolean | undefined, fallback = 0): number {
  const n = typeof v === "number" ? v : Number.parseFloat(String(v))
  return Number.isFinite(n) ? n : fallback
}

// A self-contained ROI model so the live panel works in preview without a backend.
export function demoAnalyze(values: InputValues): AnalyzeResponse {
  const price = num(values.purchasePrice)
  const renovation = num(values.renovationBudget)
  const notary = num(values.notaryFees)
  const regTax = (num(values.registrationTaxRate) / 100) * price
  const totalInvestment = price + renovation + notary + regTax

  const monthlyRent = num(values.monthlyRent)
  const vacancy = num(values.vacancyRate) / 100
  const grossAnnualRent = monthlyRent * 12
  const effectiveAnnualRent = grossAnnualRent * (1 - vacancy)

  const maintenance = num(values.annualMaintenance)
  const insurance = num(values.annualInsurance)
  const propertyTax = num(values.annualPropertyTax)
  const management = (num(values.managementRate) / 100) * effectiveAnnualRent
  const operatingCosts = maintenance + insurance + propertyTax + management

  const noi = effectiveAnnualRent - operatingCosts

  const downRate = num(values.downPaymentRate) / 100
  const downPayment = price * downRate
  const loanAmount = price - downPayment
  const rate = num(values.interestRate) / 100 / 12
  const term = num(values.loanTermYears) * 12
  const monthlyMortgage = term > 0 && rate > 0 ? (loanAmount * rate) / (1 - Math.pow(1 + rate, -term)) : loanAmount / Math.max(term, 1)
  const annualDebtService = monthlyMortgage * 12

  const annualCashFlow = noi - annualDebtService
  const monthlyCashFlow = annualCashFlow / 12
  const cashInvested = downPayment + renovation + notary + regTax

  const grossYield = price > 0 ? (grossAnnualRent / price) * 100 : 0
  const netYield = totalInvestment > 0 ? (noi / totalInvestment) * 100 : 0
  const capRate = price > 0 ? (noi / price) * 100 : 0
  const cashOnCash = cashInvested > 0 ? (annualCashFlow / cashInvested) * 100 : 0
  const paybackYears = annualCashFlow > 0 ? cashInvested / annualCashFlow : 0

  const sentimentFor = (v: number): "positive" | "negative" | "neutral" =>
    v > 0 ? "positive" : v < 0 ? "negative" : "neutral"

  return {
    verdict: {
      label: cashOnCash >= 4 && monthlyCashFlow >= 0 ? "Solid opportunity" : monthlyCashFlow < 0 ? "Negative cash flow" : "Marginal",
      sentiment: cashOnCash >= 4 && monthlyCashFlow >= 0 ? "positive" : monthlyCashFlow < 0 ? "negative" : "neutral",
    },
    metrics: [
      { key: "grossYield", label: "Gross yield", value: grossYield, format: "percent", sentiment: "neutral", description: "Annual rent ÷ purchase price." },
      { key: "netYield", label: "Net yield", value: netYield, format: "percent", sentiment: sentimentFor(netYield - 3), description: "NOI ÷ total invested." },
      { key: "capRate", label: "Cap rate", value: capRate, format: "percent", sentiment: "neutral", description: "NOI ÷ property value." },
      { key: "cashOnCash", label: "Cash-on-cash", value: cashOnCash, format: "percent", sentiment: sentimentFor(cashOnCash), description: "Annual cash flow ÷ cash invested." },
      { key: "monthlyCashFlow", label: "Monthly cash flow", value: monthlyCashFlow, format: "currency", sentiment: sentimentFor(monthlyCashFlow), description: "After mortgage & costs." },
      { key: "payback", label: "Payback", value: paybackYears, format: "years", sentiment: paybackYears > 0 && paybackYears < 25 ? "positive" : "negative", description: "Years to recoup cash invested." },
    ],
    breakdown: [
      { label: "Effective annual rent", value: effectiveAnnualRent, format: "currency" },
      { label: "Operating costs", value: -operatingCosts, format: "currency" },
      { label: "Net operating income", value: noi, format: "currency" },
      { label: "Annual debt service", value: -annualDebtService, format: "currency" },
      { label: "Annual cash flow", value: annualCashFlow, format: "currency" },
      { label: "Total cash invested", value: cashInvested, format: "currency" },
    ],
  }
}

// Deterministically derive plausible, *varied* listing values from the pasted
// URL so the preview doesn't always return the same apartment. This is sample
// data only — the real backend returns the actual scraped listing.
function hashString(s: string): number {
  let h = 2166136261
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return Math.abs(h)
}

const DEMO_CITIES = [
  { city: "1040 Etterbeek", streets: ["Rue de la Loi", "Avenue d'Auderghem", "Chaussée de Wavre"] },
  { city: "1000 Brussels", streets: ["Quai aux Briques", "Rue Antoine Dansaert", "Boulevard Anspach"] },
  { city: "2000 Antwerp", streets: ["Nationalestraat", "Mechelsesteenweg", "Kloosterstraat"] },
  { city: "9000 Ghent", streets: ["Veldstraat", "Korenmarkt", "Sint-Pietersnieuwstraat"] },
  { city: "3000 Leuven", streets: ["Naamsestraat", "Bondgenotenlaan", "Tiensestraat"] },
]

export function demoImportFromUrl(listingUrl: string): ImmowebImportResponse {
  const h = hashString(listingUrl || "fallback")
  const loc = DEMO_CITIES[h % DEMO_CITIES.length]
  const street = loc.streets[(h >> 3) % loc.streets.length]
  const houseNumber = (h % 180) + 1

  // Parse the property type from the Immoweb URL path when present, e.g.
  // /en/classified/{type}/for-sale/{locality}/{postal}/{id}
  const segments = listingUrl.split("/").filter(Boolean)
  const classifiedIdx = segments.indexOf("classified")
  const rawType = classifiedIdx >= 0 ? (segments[classifiedIdx + 1] ?? "") : ""
  const propertyType = /^[a-z-]+$/i.test(rawType) ? rawType.replace(/-/g, " ") : ""
  const isHouse = /house|villa|townhouse|mansion|bungalow|chalet/i.test(propertyType)

  // Vary the property within realistic Belgian ranges, keyed off the URL hash.
  // Houses skew larger / more bedrooms than apartments.
  const bedrooms = isHouse ? 3 + (h % 3) : 1 + (h % 3) // houses 3–5, apartments 1–3
  const livingArea = isHouse ? 110 + (h % 120) : 38 + (h % 90) // houses 110–229, apts 38–127 m²
  // Price scales loosely with size, plus per-listing variation.
  const purchasePrice = Math.round((155000 + livingArea * 2300 + (h % 60000)) / 1000) * 1000
  // Rent loosely tracks size; ~0.4–0.5% of price per month with variation.
  const monthlyRent = Math.round((450 + livingArea * 9 + (h % 350)) / 5) * 5
  const epcScore = ["A", "B", "C", "D", "E", "F"][h % 6]
  const renovationBudget = [0, 5000, 12000, 22000, 35000][(h >> 5) % 5]

  return {
    demo: true,
    values: {
      purchasePrice,
      livingArea,
      bedrooms,
      epcScore,
      monthlyRent,
      renovationBudget,
    },
    meta: {
      title: `${bedrooms}-bedroom ${propertyType || (isHouse ? "house" : "apartment")} (sample data)`,
      address: `${street} ${houseNumber}, ${loc.city}`,
      listingUrl,
    },
  }
}

function withDefaults(overrides: InputValues): InputValues {
  const base: InputValues = {}
  for (const f of DEMO_TEMPLATE.fields) {
    if (f.defaultValue !== undefined) base[f.key] = f.defaultValue
  }
  return { ...base, ...overrides }
}

const demoStore: Opportunity[] = [
  {
    id: "demo-1",
    title: "Bright 2-bed with terrace",
    address: "Rue de la Loi 120, 1040 Etterbeek",
    values: withDefaults({ purchasePrice: 269000, monthlyRent: 1095, renovationBudget: 22000 }),
    createdAt: new Date(Date.now() - 86400000 * 6).toISOString(),
  },
  {
    id: "demo-2",
    title: "Renovated townhouse",
    address: "Quai aux Briques 8, 1000 Brussels",
    values: withDefaults({ purchasePrice: 415000, monthlyRent: 1750, renovationBudget: 5000, downPaymentRate: 25 }),
    createdAt: new Date(Date.now() - 86400000 * 3).toISOString(),
  },
  {
    id: "demo-3",
    title: "Studio near campus",
    address: "Naamsestraat 22, 3000 Leuven",
    values: withDefaults({ purchasePrice: 189000, monthlyRent: 780, renovationBudget: 8000, livingArea: 38, bedrooms: 1 }),
    createdAt: new Date(Date.now() - 86400000).toISOString(),
  },
].map((o) => ({ ...o, analysis: demoAnalyze(o.values) }))

export const demoApi = {
  getTemplate: (): InputTemplate => DEMO_TEMPLATE,
  importImmoweb: (listingUrl: string): ImmowebImportResponse => demoImportFromUrl(listingUrl),
  analyze: (values: InputValues): AnalyzeResponse => demoAnalyze(values),
  listOpportunities: (): Opportunity[] => demoStore,
  createOpportunity: (input: Partial<Opportunity>): Opportunity => {
    const op: Opportunity = {
      id: `demo-${Date.now()}`,
      title: input.title ?? "Untitled opportunity",
      address: input.address,
      listingUrl: input.listingUrl,
      values: input.values ?? {},
      analysis: input.values ? demoAnalyze(input.values) : undefined,
      createdAt: new Date().toISOString(),
    }
    demoStore.unshift(op)
    return op
  },
  updateOpportunity: (id: string, patch: Partial<Opportunity>): Opportunity => {
    const idx = demoStore.findIndex((o) => o.id === id)
    const existing = demoStore[idx] ?? demoStore[0]
    const updated: Opportunity = {
      ...existing,
      ...patch,
      values: patch.values ?? existing.values,
      analysis: demoAnalyze(patch.values ?? existing.values),
      updatedAt: new Date().toISOString(),
    }
    if (idx >= 0) demoStore[idx] = updated
    return updated
  },
  compare: (): CompareResponse => {
    const cols = [
      { key: "grossYield", label: "Gross yield", format: "percent" as const },
      { key: "netYield", label: "Net yield", format: "percent" as const },
      { key: "cashOnCash", label: "Cash-on-cash", format: "percent" as const },
      { key: "monthlyCashFlow", label: "Monthly cash flow", format: "currency" as const },
      { key: "payback", label: "Payback", format: "years" as const },
    ]
    return {
      metricColumns: cols,
      rows: demoStore.map((o) => {
        const metrics: CompareResponse["rows"][number]["metrics"] = {}
        for (const m of o.analysis?.metrics ?? []) metrics[m.key] = m
        return { id: o.id, title: o.title, address: o.address, metrics }
      }),
    }
  },
}
