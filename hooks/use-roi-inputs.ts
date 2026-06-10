"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import type { InputValues, TemplateField } from "@/lib/api/types"

// "imported" = value came from an Immoweb import and has NOT been reviewed/edited
//              by the user yet (a starting value only).
// "edited"   = user has changed it (confirmed/owned by the user).
// "default"  = template default or saved value.
export type FieldStatus = "default" | "imported" | "edited"

export interface RoiInputsState {
  values: InputValues
  status: Record<string, FieldStatus>
  setField: (key: string, value: string | number | boolean) => void
  setAutoField: (key: string, value: string | number | boolean) => void
  applyImport: (imported: InputValues) => void
  resetTo: (values: InputValues) => void
  importedPending: string[]
}

function defaultsFromTemplate(fields: TemplateField[]): InputValues {
  const out: InputValues = {}
  for (const f of fields) {
    if (f.defaultValue !== undefined) out[f.key] = f.defaultValue
  }
  return out
}

export function useRoiInputs(fields: TemplateField[], initial?: InputValues) {
  const [values, setValues] = useState<InputValues>(() => ({
    ...defaultsFromTemplate(fields),
    ...(initial ?? {}),
  }))
  const [status, setStatus] = useState<Record<string, FieldStatus>>({})

  // The template is fetched async, so on first render `fields` is often empty and
  // the initializer above seeds nothing. When the template arrives, backfill any
  // field defaults that are still missing — without overwriting user edits or
  // imported values that are already present.
  useEffect(() => {
    if (fields.length === 0) return
    setValues((prev) => {
      let changed = false
      const next = { ...prev }
      for (const f of fields) {
        if (f.defaultValue !== undefined && !(f.key in next)) {
          next[f.key] = f.defaultValue
          changed = true
        }
      }
      return changed ? next : prev
    })
  }, [fields])

  const setField = useCallback((key: string, value: string | number | boolean) => {
    setValues((prev) => ({ ...prev, [key]: value }))
    // Any manual change marks the field as user-edited (no longer "imported").
    setStatus((prev) => ({ ...prev, [key]: "edited" }))
  }, [])

  const setAutoField = useCallback((key: string, value: string | number | boolean) => {
    setValues((prev) => (prev[key] === value ? prev : { ...prev, [key]: value }))
    setStatus((prev) => {
      if (prev[key] === "edited") return prev
      return prev[key] === "default" ? prev : { ...prev, [key]: "default" }
    })
  }, [])

  // Imported values are STARTING VALUES ONLY: prefill, but flag every imported
  // field so the UI can prompt the user to review before trusting ROI.
  const applyImport = useCallback((imported: InputValues) => {
    setValues((prev) => ({ ...prev, ...imported }))
    setStatus((prev) => {
      const next = { ...prev }
      for (const key of Object.keys(imported)) next[key] = "imported"
      return next
    })
  }, [])

  const resetTo = useCallback((next: InputValues) => {
    setValues(next)
    setStatus({})
  }, [])

  const importedPending = useMemo(
    () => Object.entries(status).filter(([, s]) => s === "imported").map(([k]) => k),
    [status],
  )

  return { values, status, setField, setAutoField, applyImport, resetTo, importedPending }
}
