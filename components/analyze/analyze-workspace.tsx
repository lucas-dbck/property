"use client"

import { useEffect, useMemo, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import useSWR from "swr"
import { AlertCircle, CheckCircle2, Save } from "lucide-react"
import { toast } from "sonner"
import { api, ApiError } from "@/lib/api/client"
import type { ImmowebImportResponse, ImportFeedback, Opportunity } from "@/lib/api/types"
import { useRoiInputs } from "@/hooks/use-roi-inputs"
import { useDebouncedValue } from "@/hooks/use-debounced-value"
import { PageHeader } from "@/components/page-header"
import { ImportBar } from "@/components/analyze/import-bar"
import { TextImportBox } from "@/components/analyze/text-import-box"
import { RoiInputForm } from "@/components/analyze/roi-input-form"
import { RoiResultPanel } from "@/components/analyze/roi-result-panel"
import { ReviewBanner } from "@/components/analyze/review-banner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Spinner } from "@/components/ui/spinner"
import { Skeleton } from "@/components/ui/skeleton"

export function AnalyzeWorkspace() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const editId = searchParams.get("id")

  const { data: template, isLoading: templateLoading } = useSWR("input-template", () => api.getInputTemplate())
  const { data: existing, isLoading: existingLoading } = useSWR(
    editId ? ["opportunity", editId] : null,
    () => api.listOpportunities().then((list) => list.find((o) => o.id === editId)),
  )

  const fields = template?.fields ?? []
  const { values, status, setField, applyImport, resetTo, importedPending } = useRoiInputs(fields)

  const [title, setTitle] = useState("")
  const [meta, setMeta] = useState<ImmowebImportResponse["meta"]>()
  const [importFeedback, setImportFeedback] = useState<ImportFeedback | undefined>()
  const [saving, setSaving] = useState(false)
  const [initialized, setInitialized] = useState(false)

  useEffect(() => {
    if (initialized || fields.length === 0) return
    if (editId) {
      if (existingLoading) return
      if (existing) {
        resetTo(existing.values)
        setTitle(existing.title)
        setMeta({ address: existing.address, listingUrl: existing.listingUrl })
      }
    }
    setInitialized(true)
  }, [initialized, fields.length, editId, existing, existingLoading, resetTo])

  function handleImported(result: ImmowebImportResponse) {
    applyImport(result.values)
    setImportFeedback(result.feedback)
    if (result.meta) {
      setMeta(result.meta)
      if (!title && result.meta.title) setTitle(result.meta.title)
    }
  }

  const debouncedValues = useDebouncedValue(values, 400)
  const analyzeKey = useMemo(
    () => (initialized ? ["analyze", JSON.stringify(debouncedValues)] : null),
    [initialized, debouncedValues],
  )
  const { data: analysis, isLoading: analyzing, isValidating } = useSWR(
    analyzeKey,
    () => api.analyze(debouncedValues),
    { keepPreviousData: true },
  )

  async function handleSave() {
    if (!title.trim()) {
      toast.error("Give this opportunity a title before saving.")
      return
    }
    setSaving(true)
    const payload: Partial<Opportunity> = {
      title: title.trim(),
      address: meta?.address,
      listingUrl: meta?.listingUrl,
      values,
      analysis,
    }
    try {
      if (editId) {
        await api.updateOpportunity(editId, payload)
        toast.success("Opportunity updated.")
      } else {
        await api.createOpportunity(payload)
        toast.success("Opportunity saved.")
      }
      router.push("/dashboard")
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not save. Try again.")
    } finally {
      setSaving(false)
    }
  }

  const loading = templateLoading || Boolean(editId && existingLoading)

  return (
    <div>
      <PageHeader
        title={editId ? "Edit opportunity" : "Analyze a property"}
        description="Import a listing to prefill, then refine every assumption. ROI updates live."
        action={
          <Button onClick={handleSave} disabled={saving || loading}>
            {saving ? <Spinner className="size-4" /> : <Save className="size-4" />}
            {editId ? "Save changes" : "Save opportunity"}
          </Button>
        }
      />

      <div className="grid gap-6 p-4 sm:p-6 lg:grid-cols-[1fr_380px] lg:p-8">
        <div className="flex flex-col gap-6">
          {!editId && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Import from Immoweb</CardTitle>
              </CardHeader>
              <CardContent>
                <ImportBar onImported={handleImported} />
              </CardContent>
            </Card>
          )}

          {!editId && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Paste listing text</CardTitle>
              </CardHeader>
              <CardContent>
                <TextImportBox onImported={handleImported} />
              </CardContent>
            </Card>
          )}

          {importFeedback && <ImportFeedbackPanel feedback={importFeedback} />}

          <ReviewBanner pendingCount={importedPending.length} />

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Property & finance inputs</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="opp-title">Opportunity title</Label>
                <Input
                  id="opp-title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. 2-bed apartment, Etterbeek"
                />
              </div>

              {loading ? (
                <div className="grid gap-4 sm:grid-cols-2">
                  {Array.from({ length: 8 }).map((_, i) => (
                    <Skeleton key={i} className="h-16 rounded-md" />
                  ))}
                </div>
              ) : (
                <RoiInputForm fields={fields} values={values} status={status} onChange={setField} />
              )}
            </CardContent>
          </Card>
        </div>

        <div className="lg:sticky lg:top-6 lg:self-start">
          <div className="space-y-3">
            <h2 className="text-sm font-semibold text-muted-foreground">Live ROI analysis</h2>
            <RoiResultPanel analysis={analysis} isLoading={analyzing} isValidating={isValidating} />
          </div>
        </div>
      </div>
    </div>
  )
}

function ImportFeedbackPanel({ feedback }: { feedback: ImportFeedback }) {
  const found = feedback.found.length ? feedback.found : ["No basics found"]
  const missing = feedback.missing
  const goodResult = missing.length === 0 && feedback.found.length > 0

  return (
    <div className="rounded-md border bg-background p-4 shadow-sm">
      <div className="flex items-start gap-3">
        {goodResult ? (
          <CheckCircle2 className="mt-0.5 size-5 text-emerald-600" />
        ) : (
          <AlertCircle className="mt-0.5 size-5 text-amber-600" />
        )}
        <div className="min-w-0 flex-1 space-y-3">
          <div>
            <h3 className="text-sm font-semibold">Import result</h3>
            {feedback.message && <p className="mt-1 text-sm text-muted-foreground">{feedback.message}</p>}
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <ImportFeedbackList title="Found" items={found} tone="found" />
            <ImportFeedbackList title="Still missing" items={missing.length ? missing : ["Nothing critical"]} tone="missing" />
          </div>

          {(feedback.status || feedback.method) && (
            <p className="text-xs text-muted-foreground">
              Status: {feedback.status || "unknown"}{feedback.method ? ` - Method: ${feedback.method}` : ""}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

function ImportFeedbackList({ title, items, tone }: { title: string; items: string[]; tone: "found" | "missing" }) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-medium uppercase text-muted-foreground">{title}</p>
      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <span
            key={item}
            className={
              tone === "found"
                ? "rounded-md bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700"
                : "rounded-md bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700"
            }
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  )
}
