"use client"

import Link from "next/link"
import { MapPin } from "lucide-react"
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { MetricValue } from "@/components/metric-value"
import { formatCurrency } from "@/lib/format"
import type { Opportunity } from "@/lib/api/types"

// Metric keys we like to surface on the card, in priority order.
const PREFERRED = ["cashOnCash", "netYield", "grossYield", "monthlyCashFlow"]

export function OpportunityCard({ opportunity }: { opportunity: Opportunity }) {
  const metrics = opportunity.analysis?.metrics ?? []
  const highlight = PREFERRED.map((k) => metrics.find((m) => m.key === k))
    .filter((m): m is NonNullable<typeof m> => Boolean(m))
    .slice(0, 2)

  const price = opportunity.values.purchasePrice
  const verdict = opportunity.analysis?.verdict

  return (
    <Card className="flex flex-col">
      <CardHeader className="gap-1">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-pretty font-semibold leading-tight">{opportunity.title}</h3>
          {verdict && (
            <span
              className={
                verdict.sentiment === "positive"
                  ? "shrink-0 rounded-full bg-positive/10 px-2 py-0.5 text-xs font-medium text-positive"
                  : verdict.sentiment === "negative"
                    ? "shrink-0 rounded-full bg-destructive/10 px-2 py-0.5 text-xs font-medium text-destructive"
                    : "shrink-0 rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground"
              }
            >
              {verdict.label}
            </span>
          )}
        </div>
        {opportunity.address && (
          <p className="flex items-center gap-1 text-sm text-muted-foreground">
            <MapPin className="size-3.5 shrink-0" />
            <span className="truncate">{opportunity.address}</span>
          </p>
        )}
      </CardHeader>
      <CardContent className="flex-1">
        <div className="grid grid-cols-3 gap-3">
          <div className="space-y-0.5">
            <p className="text-xs text-muted-foreground">Price</p>
            <p className="font-semibold tabular-nums">
              {typeof price === "number" ? formatCurrency(price) : "—"}
            </p>
          </div>
          {highlight.map((m) => (
            <div key={m.key} className="space-y-0.5">
              <p className="truncate text-xs text-muted-foreground">{m.label}</p>
              <MetricValue value={m.value} format={m.format} sentiment={m.sentiment} />
            </div>
          ))}
        </div>
      </CardContent>
      <CardFooter className="gap-2">
        <Button asChild variant="secondary" size="sm" className="flex-1">
          <Link href={`/analyze?id=${opportunity.id}`}>Open & edit</Link>
        </Button>
      </CardFooter>
    </Card>
  )
}
