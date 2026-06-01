"use client"

import { useState } from "react"
import { Download, Link2 } from "lucide-react"
import { toast } from "sonner"
import { api, ApiError } from "@/lib/api/client"
import type { ImmowebImportResponse } from "@/lib/api/types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Spinner } from "@/components/ui/spinner"

export function ImportBar({ onImported }: { onImported: (result: ImmowebImportResponse) => void }) {
  const [url, setUrl] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleImport(e: React.FormEvent) {
    e.preventDefault()
    if (!url.trim()) return
    setLoading(true)
    try {
      const result = await api.importImmoweb(url.trim())
      onImported(result)
      const count = Object.keys(result.values).filter((key) => result.values[key] !== "" && result.values[key] !== 0).length
      if (result.demo) {
        toast.warning(
          `Backend unavailable - prefilled ${count} field${count === 1 ? "" : "s"} with sample data. Edit every value before trusting ROI.`,
        )
      } else if (count === 0) {
        toast.warning("Import finished, but no listing values were found. Enter the key values manually for now.")
      } else {
        toast.success(
          `Imported ${count} field${count === 1 ? "" : "s"} as starting values - review before trusting ROI.`,
        )
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        toast.error("Please log out and sign in again, then retry import.")
      } else if (err instanceof ApiError) {
        toast.error(err.message)
      } else {
        toast.error("Could not import that listing. Check the URL and try again.")
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleImport} className="flex flex-col gap-2 sm:flex-row sm:items-center">
      <div className="relative flex-1">
        <Link2 className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste an Immoweb listing URL"
          className="pl-9"
          aria-label="Immoweb listing URL"
        />
      </div>
      <Button type="submit" disabled={loading || !url.trim()} variant="secondary">
        {loading ? <Spinner className="size-4" /> : <Download className="size-4" />}
        Import listing
      </Button>
    </form>
  )
}
