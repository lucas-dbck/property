"use client"

import Link from "next/link"
import { useState } from "react"
import useSWR from "swr"
import { Plus, Scale, Building2 } from "lucide-react"
import { toast } from "sonner"
import { api } from "@/lib/api/client"
import { PageHeader } from "@/components/page-header"
import { OpportunityCard } from "@/components/opportunities/opportunity-card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Empty, EmptyHeader, EmptyMedia, EmptyTitle, EmptyDescription, EmptyContent } from "@/components/ui/empty"

export default function DashboardPage() {
  const { data, isLoading, mutate } = useSWR("opportunities", () => api.listOpportunities())
  const [deletingId, setDeletingId] = useState<string | null>(null)

  async function handleDelete(id: string, title: string) {
    if (!window.confirm(`Delete "${title}" from your dashboard?`)) {
      return
    }

    setDeletingId(id)
    try {
      await api.deleteOpportunity(id)
      await mutate((current) => current?.filter((opportunity) => opportunity.id !== id) ?? [], {
        revalidate: false,
      })
      toast.success("Property deleted.")
    } catch (error) {
      toast.error("Could not delete this property.")
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div>
      <PageHeader
        title="Your opportunities"
        description="Saved properties with their latest leveraged ROI analysis."
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
                Import an Immoweb listing, refine the numbers, and save your first leveraged ROI analysis.
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
              <OpportunityCard
                key={op.id}
                opportunity={op}
                isDeleting={deletingId === op.id}
                onDelete={() => handleDelete(op.id, op.title)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
