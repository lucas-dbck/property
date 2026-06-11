"use client"

import Link from "next/link"
import { useState } from "react"
import useSWR from "swr"
import { Plus, Scale, Building2, RefreshCw, Search } from "lucide-react"
import { toast } from "sonner"
import { api, ApiError } from "@/lib/api/client"
import { PageHeader } from "@/components/page-header"
import { OpportunityCard } from "@/components/opportunities/opportunity-card"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Empty, EmptyHeader, EmptyMedia, EmptyTitle, EmptyDescription, EmptyContent } from "@/components/ui/empty"
import { Spinner } from "@/components/ui/spinner"

export default function DashboardPage() {
  const { data, isLoading, mutate } = useSWR("opportunities", () => api.listOpportunities())
  const { data: searches, mutate: mutateSearches } = useSWR("monitored-searches", () => api.listMonitoredSearches())

  return (
    <div>
      <PageHeader
        title="Your opportunities"
        description="Saved properties with their latest ROI analysis."
        action={
          <>
            <Button asChild variant="outline">
              <Link href="/compare">
                <Scale className="size-4" />
                Compare
              </Link>
            </Button>
            <Button asChild>
              <Link href="/analyze">
                <Plus className="size-4" />
                Analyze property
              </Link>
            </Button>
          </>
        }
      />

      <div className="space-y-6 p-4 sm:p-6 lg:p-8">
        <ImmowebMonitorPanel
          searches={searches ?? []}
          onChanged={() => {
            mutate()
            mutateSearches()
          }}
        />

        {isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-48 w-full rounded-xl" />
            ))}
          </div>
        ) : !data || data.length === 0 ? (
          <Empty className="border border-dashed">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <Building2 />
              </EmptyMedia>
              <EmptyTitle>No opportunities yet</EmptyTitle>
              <EmptyDescription>
                Import an Immoweb listing, refine the numbers, and save your first ROI analysis.
              </EmptyDescription>
            </EmptyHeader>
            <EmptyContent>
              <Button asChild>
                <Link href="/analyze">
                  <Plus className="size-4" />
                  Analyze a property
                </Link>
              </Button>
            </EmptyContent>
          </Empty>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.map((op) => (
              <OpportunityCard key={op.id} opportunity={op} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function ImmowebMonitorPanel({
  searches,
  onChanged,
}: {
  searches: Awaited<ReturnType<typeof api.listMonitoredSearches>>
  onChanged: () => void
}) {
  const [searchUrl, setSearchUrl] = useState("")
  const [loading, setLoading] = useState(false)
  const [scanningId, setScanningId] = useState<string | null>(null)

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!searchUrl.trim()) return
    setLoading(true)
    try {
      await api.createMonitoredSearch({ searchUrl: searchUrl.trim(), scanNow: true })
      toast.success("Monitoring started. New listings found now were loaded.")
      setSearchUrl("")
      onChanged()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not start monitoring that Immoweb search.")
    } finally {
      setLoading(false)
    }
  }

  async function handleScan(id: string) {
    setScanningId(id)
    try {
      const result = await api.scanMonitoredSearch(id)
      toast.success(`Scan complete: ${result.createdCount} new listing${result.createdCount === 1 ? "" : "s"} loaded.`)
      onChanged()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not scan that search.")
    } finally {
      setScanningId(null)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <Search className="size-4" />
          Monitor Immoweb searches
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <form onSubmit={handleCreate} className="flex flex-col gap-2 sm:flex-row">
          <Input
            type="url"
            value={searchUrl}
            onChange={(e) => setSearchUrl(e.target.value)}
            placeholder="Paste an Immoweb search URL"
            aria-label="Immoweb search URL"
          />
          <Button type="submit" disabled={loading || !searchUrl.trim()}>
            {loading ? <Spinner className="size-4" /> : <Plus className="size-4" />}
            Start monitoring
          </Button>
        </form>

        {searches.length > 0 && (
          <div className="divide-y rounded-md border">
            {searches.map((search) => (
              <div key={search.id} className="flex flex-col gap-3 p-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{search.name}</p>
                  <p className="truncate text-xs text-muted-foreground">{search.searchUrl}</p>
                  <p className="text-xs text-muted-foreground">
                    {search.lastCheckedAt ? `Last checked ${new Date(search.lastCheckedAt).toLocaleString()}` : "Not checked yet"}
                  </p>
                </div>
                <Button variant="outline" size="sm" onClick={() => handleScan(search.id)} disabled={scanningId === search.id}>
                  {scanningId === search.id ? <Spinner className="size-4" /> : <RefreshCw className="size-4" />}
                  Scan now
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
