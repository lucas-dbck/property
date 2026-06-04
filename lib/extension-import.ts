import type { ImmowebImportResponse, ImportFeedback, InputValues } from "@/lib/api/types"

export function decodeExtensionImport(raw: string | null): ImmowebImportResponse | null {
  if (!raw) return null
  try {
    const binary = window.atob(raw)
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0))
    const json = new TextDecoder().decode(bytes)
    const parsed = JSON.parse(json)
    if (!parsed || typeof parsed !== "object") return null
    const payload = parsed as Record<string, unknown>
    const values = isRecord(payload.values) ? payload.values as InputValues : {}
    const meta = isRecord(payload.meta) ? payload.meta as ImmowebImportResponse["meta"] : undefined
    const feedback = isRecord(payload.feedback) ? payload.feedback as ImportFeedback : undefined
    return { values, meta, feedback }
  } catch {
    return null
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value))
}
