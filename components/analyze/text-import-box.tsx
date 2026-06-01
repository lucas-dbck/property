"use client"

import { useState } from "react"
import { ClipboardPaste, Wand2 } from "lucide-react"
import { toast } from "sonner"
import { api, ApiError } from "@/lib/api/client"
import type { ImmowebImportResponse } from "@/lib/api/types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Spinner } from "@/components/ui/spinner"

export function TextImportBox({ onImported }: { onImported: (result: ImmowebImportResponse) => void }) {
  const [sourceUrl, setSourceUrl] = useState("")
  const [text, setText] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleImport(e: React.FormEvent) {
    e.preventDefault()
    if (text.trim().length < 20) {
      toast.error("Paste more listing text first.")
      return
    }
    setLoading(true)
    try {
      const result = await api.importListingText({ text: text.trim(), sourceUrl: sourceUrl.trim() || undefined })
      onImported(result)
      const count = Object.keys(result.values).filter((key) => result.values[key] !== "" && result.values[key] !== 0).length
      toast.success(`Extracted ${count} field${count === 1 ? "" : "s"} from pasted text.`)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not extract listing text.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleImport} className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-[1fr_180px]">
        <div className="space-y-1.5">
          <Label htmlFor="listing-text">Paste listing text</Label>
          <textarea
            id="listing-text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Copy the visible listing details from Immoweb and paste them here."
            className="min-h-32 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus-visible:ring-1 focus-visible:ring-ring"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="listing-source-url">URL</Label>
          <Input
            id="listing-source-url"
            type="url"
            value={sourceUrl}
            onChange={(e) => setSourceUrl(e.target.value)}
            placeholder="Optional"
          />
          <Button type="submit" disabled={loading || text.trim().length < 20} className="mt-3 w-full" variant="secondary">
            {loading ? <Spinner className="size-4" /> : <Wand2 className="size-4" />}
            Extract text
          </Button>
        </div>
      </div>
      <p className="flex items-center gap-2 text-xs text-muted-foreground">
        <ClipboardPaste className="size-3.5" />
        Use this when direct Immoweb import misses price, rooms, area, or EPC.
      </p>
    </form>
  )
}
