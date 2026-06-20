"use client"

import { useState } from "react"
import { ArrowDown, ArrowUp, ChevronsUpDown, Trash2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { formatMetric } from "@/lib/format"
import { sentimentColor } from "@/components/metric-value"
import type { CompareResponse } from "@/lib/api/types"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"

export function CompareTable({ data, onDelete }: { data: CompareResponse; onDelete: (id: string) => Promise<void> }) {
  const [sortKey, setSortKey] = useState<string | null>(data.metricColumns[0]?.key ?? null)
  const [dir, setDir] = useState<"asc" | "desc">("desc")
  const [deletingId, setDeletingId] = useState<string | null>(null)

  function toggleSort(key: string) {
    if (sortKey === key) {
      setDir((d) => (d === "desc" ? "asc" : "desc"))
    } else {
      setSortKey(key)
      setDir("desc")
    }
  }

  const rows = [...data.rows].sort((a, b) => {
    if (!sortKey) return 0
    const av = a.metrics[sortKey]?.value ?? Number.NEGATIVE_INFINITY
    const bv = b.metrics[sortKey]?.value ?? Number.NEGATIVE_INFINITY
    return dir === "desc" ? bv - av : av - bv
  })

  // Best value per metric column for subtle highlighting.
  const bestByCol = new Map<string, number>()
  for (const col of data.metricColumns) {
    const vals = data.rows.map((r) => r.metrics[col.key]?.value).filter((v): v is number => typeof v === "number")
    if (vals.length) bestByCol.set(col.key, Math.max(...vals))
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/50">
            <TableHead className="sticky left-0 bg-muted/50">Property</TableHead>
            {data.metricColumns.map((col) => {
              const active = sortKey === col.key
              return (
                <TableHead key={col.key} className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="-mr-2 ml-auto h-8 gap-1 font-medium"
                    onClick={() => toggleSort(col.key)}
                  >
                    {col.label}
                    {active ? (
                      dir === "desc" ? (
                        <ArrowDown className="size-3.5" />
                      ) : (
                        <ArrowUp className="size-3.5" />
                      )
                    ) : (
                      <ChevronsUpDown className="size-3.5 opacity-50" />
                    )}
                  </Button>
                </TableHead>
              )
            })}
            <TableHead className="w-12 text-right">Delete</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={row.id}>
              <TableCell className="sticky left-0 bg-background">
                <div className="min-w-40">
                  <p className="font-medium leading-tight">{row.title}</p>
                  {row.address && <p className="truncate text-xs text-muted-foreground">{row.address}</p>}
                </div>
              </TableCell>
              {data.metricColumns.map((col) => {
                const metric = row.metrics[col.key]
                const isBest =
                  metric && bestByCol.get(col.key) === metric.value && data.rows.length > 1
                return (
                  <TableCell key={col.key} className="text-right">
                    {metric ? (
                      <span
                        className={cn(
                          "tabular-nums font-semibold",
                          sentimentColor(metric.sentiment),
                          isBest && "rounded bg-positive/10 px-1.5 py-0.5",
                        )}
                      >
                        {formatMetric(metric.value, col.format)}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                )
              })}
              <TableCell className="text-right">
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-8 text-muted-foreground hover:text-destructive"
                      aria-label={`Delete ${row.title}`}
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Delete listing?</AlertDialogTitle>
                      <AlertDialogDescription>
                        This removes "{row.title}" from your saved listings and from Compare.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        disabled={deletingId === row.id}
                        onClick={async () => {
                          setDeletingId(row.id)
                          try {
                            await onDelete(row.id)
                          } finally {
                            setDeletingId(null)
                          }
                        }}
                      >
                        Delete
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
