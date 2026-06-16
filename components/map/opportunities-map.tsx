"use client"

import Link from "next/link"
import { ExternalLink, MapPin } from "lucide-react"
import type { Opportunity } from "@/lib/api/types"
import { formatCurrency, formatPercent } from "@/lib/format"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

type Point = {
  id: string
  title: string
  city: string
  postcode?: string
  price: number
  rent: number
  grossYield: number
  lat: number
  lng: number
  listingUrl?: string
}

const CITY_COORDINATES: Record<string, { lat: number; lng: number }> = {
  aalst: { lat: 50.94, lng: 4.04 },
  anderlecht: { lat: 50.84, lng: 4.31 },
  antwerp: { lat: 51.22, lng: 4.4 },
  antwerpen: { lat: 51.22, lng: 4.4 },
  brussels: { lat: 50.85, lng: 4.35 },
  bruxelles: { lat: 50.85, lng: 4.35 },
  bruges: { lat: 51.21, lng: 3.22 },
  brugge: { lat: 51.21, lng: 3.22 },
  charleroi: { lat: 50.41, lng: 4.44 },
  duffel: { lat: 51.09, lng: 4.51 },
  elsene: { lat: 50.83, lng: 4.37 },
  etterbeek: { lat: 50.84, lng: 4.39 },
  genk: { lat: 50.97, lng: 5.5 },
  gent: { lat: 51.05, lng: 3.72 },
  ghent: { lat: 51.05, lng: 3.72 },
  grimbergen: { lat: 50.93, lng: 4.37 },
  hasselt: { lat: 50.93, lng: 5.34 },
  ixelles: { lat: 50.83, lng: 4.37 },
  kortrijk: { lat: 50.83, lng: 3.27 },
  leuven: { lat: 50.88, lng: 4.7 },
  liege: { lat: 50.63, lng: 5.57 },
  londerzeel: { lat: 51.0, lng: 4.3 },
  luik: { lat: 50.63, lng: 5.57 },
  malderen: { lat: 51.02, lng: 4.24 },
  mechelen: { lat: 51.03, lng: 4.48 },
  mons: { lat: 50.45, lng: 3.95 },
  namur: { lat: 50.47, lng: 4.87 },
  oostende: { lat: 51.23, lng: 2.92 },
  ostend: { lat: 51.23, lng: 2.92 },
  schaerbeek: { lat: 50.87, lng: 4.38 },
  "sint-niklaas": { lat: 51.16, lng: 4.14 },
  turnhout: { lat: 51.32, lng: 4.94 },
  uccle: { lat: 50.8, lng: 4.34 },
  ukkel: { lat: 50.8, lng: 4.34 },
  vilvoorde: { lat: 50.93, lng: 4.43 },
  waterloo: { lat: 50.72, lng: 4.4 },
  zaventem: { lat: 50.88, lng: 4.47 },
  zemst: { lat: 50.99, lng: 4.46 },
}

const POSTCODE_AREAS = [
  { min: 1000, max: 1299, lat: 50.85, lng: 4.35 },
  { min: 1500, max: 1999, lat: 50.92, lng: 4.35 },
  { min: 2000, max: 2999, lat: 51.2, lng: 4.55 },
  { min: 3000, max: 3499, lat: 50.9, lng: 4.75 },
  { min: 3500, max: 3999, lat: 50.95, lng: 5.35 },
  { min: 4000, max: 4999, lat: 50.55, lng: 5.45 },
  { min: 5000, max: 5999, lat: 50.4, lng: 4.9 },
  { min: 6000, max: 6999, lat: 50.2, lng: 4.55 },
  { min: 7000, max: 7999, lat: 50.45, lng: 3.75 },
  { min: 8000, max: 8999, lat: 51.0, lng: 3.05 },
  { min: 9000, max: 9999, lat: 51.0, lng: 3.8 },
]

export function OpportunitiesMap({ opportunities }: { opportunities: Opportunity[] }) {
  const mapped = opportunities.map((opportunity) => ({
    opportunity,
    point: toPoint(opportunity),
  }))
  const points = mapped.flatMap(({ point }) => (point ? [point] : []))
  const unmapped = mapped.filter(({ point }) => !point).map(({ opportunity }) => opportunity)

  if (opportunities.length === 0) {
    return (
      <div className="flex min-h-[420px] items-center justify-center rounded-md border border-dashed bg-muted/20 p-6 text-center">
        <div>
          <MapPin className="mx-auto mb-3 size-8 text-muted-foreground" />
          <h2 className="text-base font-semibold">No listings to map yet</h2>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground">
            Import Immoweb listings first, then this map will show where they are.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
      <div className="relative min-h-[560px] overflow-hidden rounded-md border bg-[#e8f1ee]">
        <BelgiumBackdrop />
        {points.length > 0 ? (
          points.map((point, index) => (
            <MapMarker key={point.id} point={point} index={index} total={points.length} />
          ))
        ) : (
          <div className="absolute inset-x-6 top-6 rounded-md border bg-background/90 p-4 shadow-sm">
            <p className="text-sm font-semibold">No listings have enough location data yet</p>
            <p className="mt-1 text-xs text-muted-foreground">
              The map needs a city, postcode, or an Immoweb URL that contains the city.
            </p>
          </div>
        )}
      </div>

      <aside className="space-y-3">
        <div className="rounded-md border bg-card p-4">
          <p className="text-sm font-semibold">{points.length} listing{points.length === 1 ? "" : "s"} on map</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Markers use city or postcode location, so they are area-level pins rather than exact building coordinates.
          </p>
        </div>

        <div className="space-y-2">
          {points.map((point) => (
            <ListingMapRow key={point.id} point={point} />
          ))}
        </div>

        {unmapped.length > 0 && (
          <div className="rounded-md border bg-card p-4">
            <p className="text-sm font-semibold">{unmapped.length} listings need a city or postcode</p>
            <p className="mt-1 text-xs text-muted-foreground">Add location data to show them on the map.</p>
          </div>
        )}
      </aside>
    </div>
  )
}

function MapMarker({ point, index, total }: { point: Point; index: number; total: number }) {
  const { x, y } = project(point.lat, point.lng)
  const offset = total > 1 ? ((index % 5) - 2) * 3 : 0
  const strong = point.grossYield >= 5

  return (
    <Link
      href={`/analyze?id=${point.id}`}
      className={cn(
        "group absolute z-10 flex -translate-x-1/2 -translate-y-full flex-col items-center",
        strong ? "text-emerald-700" : "text-primary",
      )}
      style={{ left: `${clamp(x + offset, 5, 95)}%`, top: `${clamp(y + offset, 5, 95)}%` }}
      title={`${point.title} - ${formatCurrency(point.price)}`}
    >
      <span className={cn("rounded-md px-2 py-1 text-xs font-semibold shadow-sm", strong ? "bg-emerald-600 text-white" : "bg-primary text-primary-foreground")}>
        {formatPercent(point.grossYield)}
      </span>
      <span className="mt-1 flex size-4 rotate-45 rounded-sm bg-current shadow-md" />
      <span className="pointer-events-none absolute bottom-full mb-8 hidden min-w-52 rounded-md border bg-popover p-3 text-popover-foreground shadow-lg group-hover:block">
        <span className="block truncate text-sm font-semibold">{point.title}</span>
        <span className="mt-1 block text-xs text-muted-foreground">{[point.city, point.postcode].filter(Boolean).join(", ")}</span>
        <span className="mt-2 grid grid-cols-2 gap-2 text-xs">
          <span>Price<br /><strong>{formatCurrency(point.price)}</strong></span>
          <span>Rent<br /><strong>{formatCurrency(point.rent)}</strong></span>
        </span>
      </span>
    </Link>
  )
}

function ListingMapRow({ point }: { point: Point }) {
  return (
    <div className="rounded-md border bg-card p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">{point.title}</p>
          <p className="text-xs text-muted-foreground">{[point.city, point.postcode].filter(Boolean).join(", ")}</p>
        </div>
        <span className="rounded bg-secondary px-2 py-1 text-xs font-medium">{formatPercent(point.grossYield)}</span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-muted-foreground">
        <span>Price<br /><strong className="text-foreground">{formatCurrency(point.price)}</strong></span>
        <span>Rent<br /><strong className="text-foreground">{formatCurrency(point.rent)}</strong></span>
      </div>
      <div className="mt-3 flex gap-2">
        <Button asChild size="sm" variant="outline" className="h-8">
          <Link href={`/analyze?id=${point.id}`}>Open</Link>
        </Button>
        {point.listingUrl && (
          <Button asChild size="sm" variant="ghost" className="h-8">
            <a href={point.listingUrl} target="_blank" rel="noreferrer">
              Immoweb
              <ExternalLink className="size-3" />
            </a>
          </Button>
        )}
      </div>
    </div>
  )
}

function BelgiumBackdrop() {
  return (
    <div className="absolute inset-0">
      <svg viewBox="0 0 100 100" className="h-full w-full" preserveAspectRatio="none" aria-hidden="true">
        <path
          d="M30 16 L47 9 L65 14 L78 28 L84 45 L78 64 L66 82 L45 90 L27 80 L17 61 L16 38 Z"
          fill="#d7e6e1"
          stroke="#a9c5be"
          strokeWidth="0.7"
        />
        <path d="M23 35 C38 39 54 35 76 43" fill="none" stroke="#c0d5cf" strokeWidth="0.5" />
        <path d="M31 16 C38 39 39 61 45 90" fill="none" stroke="#c0d5cf" strokeWidth="0.5" />
        <path d="M16 61 C36 55 57 62 78 64" fill="none" stroke="#c0d5cf" strokeWidth="0.5" />
      </svg>
      <div className="absolute left-[42%] top-[12%] text-xs font-medium text-muted-foreground">Antwerp</div>
      <div className="absolute left-[44%] top-[44%] text-xs font-medium text-muted-foreground">Brussels</div>
      <div className="absolute left-[70%] top-[60%] text-xs font-medium text-muted-foreground">Liege</div>
      <div className="absolute left-[21%] top-[35%] text-xs font-medium text-muted-foreground">Ghent</div>
    </div>
  )
}

function toPoint(opportunity: Opportunity): Point | null {
  const values = opportunity.values ?? {}
  const listingUrl = opportunity.listingUrl || String(values.source_url || "")
  const locationFromUrl = parseLocationFromImmowebUrl(listingUrl)
  const city = String(values.city || locationFromUrl.city || "").trim()
  const postcode = String(values.postcode || values.postal_code || locationFromUrl.postcode || "").trim()
  const coords = coordinatesFor(city, postcode)
  if (!coords) return null

  const price = toNumber(values.purchase_price || values.price)
  const rent = toNumber(values.monthly_rent || values.estimated_rent || values.expected_monthly_rent)
  const grossYield = price > 0 && rent > 0 ? (rent * 12 / price) * 100 : 0

  return {
    id: opportunity.id,
    title: opportunity.title,
    city: city || "Unknown city",
    postcode,
    price,
    rent,
    grossYield,
    lat: coords.lat,
    lng: coords.lng,
    listingUrl,
  }
}

function parseLocationFromImmowebUrl(url: string): { city?: string; postcode?: string } {
  const parts = url
    .split("/")
    .map((part) => decodeURIComponent(part).trim())
    .filter(Boolean)

  const postcode = parts.find((part) => /^\d{4}$/.test(part))
  const postcodeIndex = postcode ? parts.indexOf(postcode) : -1
  const city = postcodeIndex > 0 ? parts[postcodeIndex - 1] : undefined

  return { city, postcode }
}

function coordinatesFor(city: string, postcode: string): { lat: number; lng: number } | null {
  const cityKey = normalizeLocation(city)
  if (CITY_COORDINATES[cityKey]) return CITY_COORDINATES[cityKey]
  const code = Number.parseInt(postcode, 10)
  const area = POSTCODE_AREAS.find((item) => code >= item.min && code <= item.max)
  return area ? { lat: area.lat, lng: area.lng } : null
}

function project(lat: number, lng: number): { x: number; y: number } {
  const minLng = 2.45
  const maxLng = 6.45
  const minLat = 49.45
  const maxLat = 51.65
  return {
    x: clamp(((lng - minLng) / (maxLng - minLng)) * 100, 5, 95),
    y: clamp((1 - (lat - minLat) / (maxLat - minLat)) * 100, 5, 95),
  }
}

function normalizeLocation(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
}

function toNumber(value: unknown): number {
  if (typeof value === "number") return Number.isFinite(value) ? value : 0

  const raw = String(value ?? "").trim()
  const normalized = raw
    .replace(/[^\d,.\-\s]/g, "")
    .replace(/[\s]/g, "")
    .replace(/[.,](?=\d{3}(\D|$))/g, "")
    .replace(",", ".")
  const number = Number.parseFloat(normalized)
  return Number.isFinite(number) ? number : 0
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}
