import { cn } from "@/lib/utils"
import { formatMetric } from "@/lib/format"
import type { AnalyzeMetric } from "@/lib/api/types"

export function sentimentColor(sentiment?: AnalyzeMetric["sentiment"]) {
  switch (sentiment) {
    case "positive":
      return "text-positive"
    case "negative":
      return "text-destructive"
    default:
      return "text-foreground"
  }
}

export function MetricValue({
  value,
  format,
  sentiment,
  className,
}: {
  value: number
  format: AnalyzeMetric["format"]
  sentiment?: AnalyzeMetric["sentiment"]
  className?: string
}) {
  return (
    <span className={cn("tabular-nums font-semibold", sentimentColor(sentiment), className)}>
      {formatMetric(value, format)}
    </span>
  )
}
