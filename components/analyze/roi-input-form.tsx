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
  return Array.from(groups.entries())
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
        <fieldset key={groupName} className="space-y-4">
          <legend className="text-sm font-semibold text-muted-foreground">{groupName}</legend>
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
          <Input
            id={field.key}
            type={isNumeric ? "number" : "text"}
            inputMode={isNumeric ? "decimal" : undefined}
            step={field.step}
            min={field.min}
            max={field.max}
            value={value === undefined ? "" : String(value)}
            onChange={(e) => onChange(isNumeric ? (e.target.value === "" ? "" : Number(e.target.value)) : e.target.value)}
            className={cn(field.unit && "pr-9", imported && "border-chart-4/60 ring-1 ring-chart-4/30")}
          />
        </div>
      )}

      {field.helpText && <p className="text-xs text-muted-foreground">{field.helpText}</p>}
    </div>
  )
}
