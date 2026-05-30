"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Building2, TrendingUp } from "lucide-react"
import { toast } from "sonner"
import { useAuth } from "@/lib/auth/context"
import { ApiError } from "@/lib/api/client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Spinner } from "@/components/ui/spinner"

export default function LoginPage() {
  const { user, isLoading, login, register } = useAuth()
  const router = useRouter()
  const [mode, setMode] = useState<"login" | "register">("login")
  const [submitting, setSubmitting] = useState(false)

  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [name, setName] = useState("")

  useEffect(() => {
    if (!isLoading && user) router.replace("/dashboard")
  }, [isLoading, user, router])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      if (mode === "login") {
        await login(email, password)
        toast.success("Welcome back")
        router.replace("/dashboard")
      } else {
        await register(email, password, name || undefined)
        // Registration does not sign the user in. Send them to the sign-in tab
        // with their email prefilled so they can log in to their own page.
        toast.success("Account created — please sign in to continue")
        setMode("login")
        setPassword("")
        setName("")
      }
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Something went wrong. Please try again."
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="grid min-h-svh lg:grid-cols-2">
      {/* Brand panel */}
      <div className="relative hidden flex-col justify-between bg-sidebar p-10 text-sidebar-foreground lg:flex">
        <div className="flex items-center gap-2 font-semibold">
          <span className="flex size-8 items-center justify-center rounded-md bg-sidebar-primary text-sidebar-primary-foreground">
            <Building2 className="size-4" />
          </span>
          YieldDesk
        </div>
        <div className="space-y-4">
          <TrendingUp className="size-8 text-sidebar-primary" />
          <h1 className="text-pretty text-3xl font-semibold leading-tight">
            Turn Immoweb listings into confident investment decisions.
          </h1>
          <p className="max-w-md text-pretty text-sm leading-relaxed text-sidebar-foreground/70">
            Import a listing, refine every assumption yourself, and watch your ROI update live before you save and
            compare opportunities.
          </p>
        </div>
        <p className="text-xs text-sidebar-foreground/50">
          Imported figures are only a starting point — you stay in control of every number.
        </p>
      </div>

      {/* Form panel */}
      <div className="flex items-center justify-center p-6">
        <Card className="w-full max-w-sm border-border/60">
          <CardHeader>
            <CardTitle className="text-xl">
              {mode === "login" ? "Sign in" : "Create your account"}
            </CardTitle>
            <CardDescription>
              {mode === "login"
                ? "Access your saved opportunities and analysis."
                : "Start analyzing property investments in minutes."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs value={mode} onValueChange={(v) => setMode(v as "login" | "register")}>
              <TabsList className="mb-4 grid w-full grid-cols-2">
                <TabsTrigger value="login">Sign in</TabsTrigger>
                <TabsTrigger value="register">Register</TabsTrigger>
              </TabsList>

              <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                <TabsContent value="register" className="mt-0 p-0">
                  <div className="flex flex-col gap-2">
                    <Label htmlFor="name">Name</Label>
                    <Input
                      id="name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Jane Investor"
                      autoComplete="name"
                    />
                  </div>
                </TabsContent>

                <div className="flex flex-col gap-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    autoComplete="email"
                  />
                </div>

                <div className="flex flex-col gap-2">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    required
                    minLength={6}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    autoComplete={mode === "login" ? "current-password" : "new-password"}
                  />
                </div>

                <Button type="submit" disabled={submitting} className="mt-2">
                  {submitting && <Spinner className="size-4" />}
                  {mode === "login" ? "Sign in" : "Create account"}
                </Button>
              </form>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </main>
  )
}
