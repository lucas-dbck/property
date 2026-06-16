"use client"

import Link from "next/link"
import useSWR from "swr"
import { Plus } from "lucide-react"
import { api } from "@/lib/api/client"
import { PageHeader } from "@/components/page-header"
import { OpportunitiesMap } from "@/components/map/opportunities-map"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"

export default function MapPage() {
  const { data, isLoading } = useSWR("opportunities", () => api.listOpportunities())

  return (
    <div>
      <PageHeader
        title="Opportunity map"
        description="See saved and monitored Immoweb listings by city or postcode."
        action={
          <Button asChild>
            <Link href="/analyze">
              <Plus className="size-4" />
              Analyze property
            </Link>
          </Button>
        }
      />

      <div className="p-4 sm:p-6 lg:p-8">
        {isLoading ? <Skeleton className="h-[620px] w-full rounded-md" /> : <OpportunitiesMap opportunities={data ?? []} />}
      </div>
    </div>
  )
}
