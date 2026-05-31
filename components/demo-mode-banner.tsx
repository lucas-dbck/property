"use client"

import { useEffect, useState, useSyncExternalStore } from "react"
import { TriangleAlert } from "lucide-react"
import { isDemoMode, subscribeDemoMode } from "@/lib/api/client"

export function DemoModeBanner() {
  const demo = useSyncExternalStore(
    subscribeDemoMode,
    () => isDemoMode(),
    () => false,
  )
  const [backendHealthy, setBackendHealthy] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function checkBackend() {
      try {
        const response = await fetch("/api/proxy/health", { cache: "no-store" })
        if (!cancelled) setBackendHealthy(response.ok)
      } catch {
        if (!cancelled) setBackendHealthy(false)
      }
    }

    checkBackend()
    const interval = window.setInterval(checkBackend, 30000)

    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [])

  if (!demo || backendHealthy) return null

  return (
    <div
      role="status"
      className="flex items-start gap-3 border-b border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive md:px-6"
    >
      <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <p className="text-pretty leading-relaxed">
        <span className="font-semibold">Demo data - backend not connected.</span>{" "}
        {
          "Every value on screen is fabricated sample data, not a real import or analysis. Set NEXT_PUBLIC_API_BASE_URL to connect your backend before trusting any numbers."
        }
      </p>
    </div>
  )
}
