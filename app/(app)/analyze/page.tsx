import { Suspense } from "react"
import { AnalyzeWorkspace } from "@/components/analyze/analyze-workspace"
import { Spinner } from "@/components/ui/spinner"

export default function AnalyzePage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-svh items-center justify-center">
          <Spinner className="size-6 text-muted-foreground" />
        </div>
      }
    >
      <AnalyzeWorkspace />
    </Suspense>
  )
}
