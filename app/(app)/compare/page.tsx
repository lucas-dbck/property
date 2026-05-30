"use client"

import Link from "next/link"
import useSWR from "swr"
import { Plus, Scale } from "lucide-react"
import { api } from "@/lib/api/client"
import { PageHeader } from "@/components/page-header"
import { CompareTable } from "@/components/compare/compare-table"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Empty,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
  EmptyDescription,
  EmptyContent,
} from "@/components/ui/empty"

export default function ComparePage() {
  const { data, isLoading } = useSWR("compare", () => api.compare())

  const hasRows = data && data.rows.length > 0

  return (
    <div>
      <PageHeader
        title="Compare opportunities"
        description="Rank your saved properties side by side. Tap a column header to sort by that metric."
        action={
          <Button asChild variant="outline">
            <Link href="/dashboard">Back to dashboard</Link>
          </Button>
        }
      />

      <div className="p-4 sm:p-6 lg:p-8">
        {isLoading ? (
          <Skeleton className="h-64 w-full rounded-lg" />
        ) : !hasRows ? (
          <Empty className="border border-dashed">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <Scale />
              </EmptyMedia>
              <EmptyTitle>Nothing to compare yet</EmptyTitle>
              <EmptyDescription>Save at least two opportunities to compare their ROI.</EmptyDescription>
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
          <CompareTable data={data} />
        )}
      </div>
    </div>
  )
}
