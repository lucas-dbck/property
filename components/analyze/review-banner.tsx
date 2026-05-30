"use client"

import { AlertTriangle } from "lucide-react"

// Reinforces the core rule: imported values are STARTING values only.
// The user must review/edit important fields before trusting the ROI.
export function ReviewBanner({ pendingCount }: { pendingCount: number }) {
  if (pendingCount === 0) return null
  return (
    <div className="flex items-start gap-3 rounded-lg border border-chart-4/40 bg-chart-4/10 p-3 text-sm">
      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-chart-4" />
      <p className="text-pretty leading-relaxed">
        <span className="font-medium">{pendingCount}</span> imported{" "}
        {pendingCount === 1 ? "value is" : "values are"} unreviewed. Imported figures are starting points only — confirm
        or adjust each one before relying on this ROI.
      </p>
    </div>
  )
}
