"use client"

import Link from "next/link"
import useSWR from "swr"
import { Plus, Scale, Building2 } from "lucide-react"
import { api } from "@/lib/api/client"
import { PageHeader } from "@/components/page-header"
import { OpportunityCard } from "@/components/opportunities/opportunity-card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Empty, EmptyHeader, EmptyMedia, EmptyTitle, EmptyDescription, EmptyContent } from "@/components/ui/empty"

export default function DashboardPage() {
  const { data, isLoading } = useSWR("opportunities", () => api.listOpportunities())

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
