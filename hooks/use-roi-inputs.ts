"use client"

import { useCallback, useMemo, useState } from "react"
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

  const setField = useCallback((key: string, value: string | number | boolean) => {
    setValues((prev) => ({ ...prev, [key]: value }))
    // Any manual change marks the field as user-edited (no longer "imported").
    setStatus((prev) => ({ ...prev, [key]: "edited" }))
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

  return { values, status, setField, applyImport, resetTo, importedPending }
}
