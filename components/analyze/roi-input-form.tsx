"use client"

import { cn } from "@/lib/utils"
import type { FieldStatus } from "@/hooks/use-roi-inputs"
import type { InputValues, TemplateField } from "@/lib/api/types"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

function groupFields(fields: TemplateField[]) {
  const groups = new Map<string, TemplateField[]>()
  for (const f of fields) {
    const key = f.group ?? "Inputs"
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key)!.push(f)
  }
  const order = ["listing", "property", "rent", "purchase", "financing", "risk"]
  return Array.from(groups.entries()).sort(([a], [b]) => {
    const aIndex = order.indexOf(a)
    const bIndex = order.indexOf(b)
    return (aIndex === -1 ? 99 : aIndex) - (bIndex === -1 ? 99 : bIndex)
  })
}

export function RoiInputForm({
  fields,
  values,
  status,
  onChange,
}: {
  fields: TemplateField[]
  values: InputValues
  status: Record<string, FieldStatus>
  onChange: (key: string, value: string | number | boolean) => void
}) {
  const groups = groupFields(fields)

  return (
    <div className="flex flex-col gap-6">
      {groups.map(([groupName, groupFields]) => (
        <fieldset key={groupName} className="rounded-md border bg-background p-4">
          <legend className="px-1 text-sm font-semibold">{groupLabel(groupName)}</legend>
          <p className="mb-4 mt-1 text-xs text-muted-foreground">{groupHelp(groupName)}</p>
          <div className="grid gap-4 sm:grid-cols-2">
            {groupFields.map((field) => (
              <FieldControl
                key={field.key}
                field={field}
                value={values[field.key]}
                status={status[field.key] ?? "default"}
                onChange={(v) => onChange(field.key, v)}
              />
            ))}
          </div>
        </fieldset>
      ))}
    </div>
  )
}

function FieldControl({
  field,
  value,
  status,
  onChange,
}: {
  field: TemplateField
  value: string | number | boolean | undefined
  status: FieldStatus
  onChange: (value: string | number | boolean) => void
}) {
  const imported = status === "imported"
  const isNumeric = field.type === "number" || field.type === "currency" || field.type === "percent"
  const isMoney = isMoneyField(field)
  const displayValue = formatInputValue(field, value)

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between gap-2">
        <Label htmlFor={field.key} className="text-sm">
          {field.label}
        </Label>
        {imported && (
          <span
            className="rounded bg-chart-4/15 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-chart-4"
            title="Imported from Immoweb — review and edit before trusting ROI"
          >
            Imported
          </span>
        )}
      </div>

      {field.type === "switch" ? (
        <div className="flex h-10 items-center">
          <Switch
            id={field.key}
            checked={Boolean(value)}
            onCheckedChange={(checked) => onChange(checked)}
          />
        </div>
      ) : field.type === "select" ? (
        <Select value={value !== undefined ? String(value) : undefined} onValueChange={(v) => onChange(v)}>
          <SelectTrigger
            id={field.key}
            className={cn("w-full", imported && "border-chart-4/60 ring-1 ring-chart-4/30")}
          >
            <SelectValue placeholder="Select" />
          </SelectTrigger>
          <SelectContent>
            {field.options?.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ) : (
        <div className="relative">
          {field.unit && (
            <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
              {field.unit}
            </span>
          )}
          {isMoney && !field.unit && (
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-xs font-medium text-muted-foreground">
              €
            </span>
          )}
          <Input
            id={field.key}
            type="text"
            inputMode={isNumeric ? "decimal" : undefined}
            step={field.step}
            min={field.min}
            max={field.max}
            value={displayValue}
            onChange={(e) => onChange(isNumeric ? parseNumericInput(e.target.value, field) : e.target.value)}
            className={cn(
              field.unit && "pr-9",
              isMoney && !field.unit && "pl-8",
              imported && "border-chart-4/60 ring-1 ring-chart-4/30",
            )}
          />
        </div>
      )}

      {field.helpText && <p className="text-xs text-muted-foreground">{field.helpText}</p>}
    </div>
  )
}

function groupLabel(group: string): string {
  const labels: Record<string, string> = {
    listing: "Listing source",
    property: "Property details",
    rent: "Rent estimate",
    purchase: "Purchase & costs",
    financing: "Financing",
    risk: "Risk assumptions",
  }
  return labels[group] ?? group
}

function groupHelp(group: string): string {
  const descriptions: Record<string, string> = {
    listing: "Where the property came from.",
    property: "Facts about the home. These drive rent estimates.",
    rent: "Auto-estimated from the listing and local rent data. Edit it if you know the real market rent.",
    purchase: "Price and one-time/yearly cost assumptions. These are editable assumptions, not listing facts.",
    financing: "Loan assumptions used for cash flow and cash-on-cash return.",
    risk: "Vacancy and uncertainty assumptions.",
  }
  return descriptions[group] ?? "Inputs used in the ROI calculation."
}

function isMoneyField(field: TemplateField): boolean {
  const key = field.key.toLowerCase()
  const label = field.label.toLowerCase()
  return field.type === "currency" || /price|rent|cost|payment|budget|fee|cash|investment/.test(`${key} ${label}`)
}

function formatInputValue(field: TemplateField, value: string | number | boolean | undefined): string {
  if (value === undefined || value === "" || typeof value === "boolean") return value === undefined ? "" : String(value)
  if (field.type === "percent") return String(value)
  const number = Number(value)
  if (!Number.isFinite(number)) return String(value)
  if (isMoneyField(field)) return String(Math.round(number))
  return String(value)
}

function parseNumericInput(value: string, field: TemplateField): number | string | "" {
  if (!value.trim()) return ""
  const normalized = value
    .replace(/[€\s\u00a0]/g, "")
    .replace(/\.(?=\d{3}(\D|$))/g, "")
    .replace(/,(?=\d{3}(\D|$))/g, "")
    .replace(",", ".")
    .replace(/[^0-9.-]/g, "")
  if (/^-?\d+\.$/.test(normalized) || normalized === "." || normalized === "-") return value
  const number = Number(normalized)
  if (!Number.isFinite(number)) return ""
  return isMoneyField(field) ? Math.round(number) : number
}
