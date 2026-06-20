"use client"

import { cn } from "@/lib/utils"
import { formatMetric } from "@/lib/format"
import { sentimentColor } from "@/components/metric-value"
import type { AnalyzeResponse } from "@/lib/api/types"
import { Info } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

export function RoiResultPanel({
  analysis,
  isLoading,
  isValidating,
}: {
  analysis?: AnalyzeResponse
  isLoading: boolean
  isValidating: boolean
}) {
  if (isLoading && !analysis) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-40 rounded-md" />
        <div className="grid grid-cols-2 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-lg" />
          ))}
        </div>
        <Skeleton className="h-40 rounded-lg" />
      </div>
    )
  }

  if (!analysis) return null

  return (
    <div className="space-y-4">
      {/* Verdict + live indicator */}
      <div className="flex items-center justify-between gap-2">
        {analysis.verdict ? (
          <span
            className={cn(
              "inline-flex items-center rounded-full px-3 py-1 text-sm font-medium",
              analysis.verdict.sentiment === "positive" && "bg-positive/10 text-positive",
              analysis.verdict.sentiment === "negative" && "bg-destructive/10 text-destructive",
              analysis.verdict.sentiment === "neutral" && "bg-muted text-muted-foreground",
            )}
          >
            {analysis.verdict.label}
          </span>
        ) : (
          <span />
        )}
        {isValidating && (
          <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Spinner className="size-3" />
            Updating
          </span>
        )}
      </div>

      {/* Metric grid */}
      <div className="grid grid-cols-2 gap-3">
        {analysis.metrics.map((m) => (
          <Card key={m.key} className="gap-0 py-0">
            <CardContent className="space-y-1 p-4">
              <div className="flex items-center justify-between gap-2">
                <p className="truncate text-xs text-muted-foreground">{m.label}</p>
                {m.description && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        className="inline-flex size-5 shrink-0 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        aria-label={`Info about ${m.label}`}
                      >
                        <Info className="size-3.5" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="top" className="max-w-64">
                      {m.description}
                    </TooltipContent>
                  </Tooltip>
                )}
              </div>
              <p className={cn("text-xl font-semibold tabular-nums", sentimentColor(m.sentiment))}>
                {formatMetric(m.value, m.format)}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Breakdown */}
      {analysis.breakdown && analysis.breakdown.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Cash-flow breakdown</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {analysis.breakdown.map((item, i) => (
              <div
                key={`${item.label}-${i}`}
                className="flex items-center justify-between border-b border-border/60 pb-2 text-sm last:border-0 last:pb-0"
              >
                <span className="text-muted-foreground">{item.label}</span>
                <span
                  className={cn(
                    "tabular-nums font-medium",
                    item.value < 0 ? "text-destructive" : "text-foreground",
                  )}
                >
                  {formatMetric(item.value, item.format)}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
