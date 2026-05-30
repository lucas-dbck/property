"use client"

import { useSyncExternalStore } from "react"
import { TriangleAlert } from "lucide-react"
import { isDemoMode, subscribeDemoMode } from "@/lib/api/client"

export function DemoModeBanner() {
  const demo = useSyncExternalStore(
    subscribeDemoMode,
    () => isDemoMode(),
    () => false,
  )

  if (!demo) return null

  return (
    <div
      role="status"
      className="flex items-start gap-3 border-b border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive md:px-6"
    >
      <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <p className="text-pretty leading-relaxed">
        <span className="font-semibold">Demo data — backend not connected.</span>{" "}
        {
          "Every value on screen is fabricated sample data, not a real import or analysis. Set NEXT_PUBLIC_API_BASE_URL to connect your backend before trusting any numbers."
        }
      </p>
    </div>
  )
}
