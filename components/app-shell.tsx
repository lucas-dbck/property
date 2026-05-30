"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { Building2, LayoutDashboard, LineChart, LogOut, Scale } from "lucide-react"
import { cn } from "@/lib/utils"
import { useAuth } from "@/lib/auth/context"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { DemoModeBanner } from "@/components/demo-mode-banner"

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/analyze", label: "Analyze", icon: LineChart },
  { href: "/compare", label: "Compare", icon: Scale },
]

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname()
  return (
    <nav className="flex flex-col gap-1">
      {NAV.map((item) => {
        const active = pathname === item.href || pathname.startsWith(item.href + "/")
        const Icon = item.icon
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              active
                ? "bg-sidebar-accent text-sidebar-accent-foreground"
                : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
            )}
          >
            <Icon className="size-4" />
            {item.label}
          </Link>
        )
      })}
    </nav>
  )
}

function UserMenu() {
  const { user, logout } = useAuth()
  const router = useRouter()
  const initials = (user?.name || user?.email || "?").slice(0, 2).toUpperCase()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="h-auto w-full justify-start gap-3 px-2 py-2 text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground">
          <Avatar className="size-7">
            <AvatarFallback className="bg-sidebar-primary text-xs text-sidebar-primary-foreground">
              {initials}
            </AvatarFallback>
          </Avatar>
          <span className="flex-1 truncate text-left text-sm">{user?.name || user?.email}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="truncate">{user?.email}</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={() => {
            logout()
            router.replace("/login")
          }}
        >
          <LogOut className="size-4" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-svh bg-background">
      {/* Sidebar */}
      <aside className="sticky top-0 hidden h-svh w-64 shrink-0 flex-col gap-6 border-r border-sidebar-border bg-sidebar p-4 md:flex">
        <Link href="/dashboard" className="flex items-center gap-2 px-2 font-semibold text-sidebar-foreground">
          <span className="flex size-8 items-center justify-center rounded-md bg-sidebar-primary text-sidebar-primary-foreground">
            <Building2 className="size-4" />
          </span>
          YieldDesk
        </Link>
        <div className="flex-1">
          <NavLinks />
        </div>
        <UserMenu />
      </aside>

      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile top bar */}
        <header className="flex items-center justify-between gap-3 border-b border-border bg-background/80 p-3 backdrop-blur md:hidden">
          <Link href="/dashboard" className="flex items-center gap-2 font-semibold">
            <span className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Building2 className="size-4" />
            </span>
            YieldDesk
          </Link>
        </header>
        {/* Mobile nav */}
        <div className="border-b border-border bg-card p-2 md:hidden">
          <div className="flex gap-1">
            <MobileNav />
          </div>
        </div>
        <DemoModeBanner />
        <main className="flex-1">{children}</main>
      </div>
    </div>
  )
}

function MobileNav() {
  const pathname = usePathname()
  return (
    <>
      {NAV.map((item) => {
        const active = pathname === item.href || pathname.startsWith(item.href + "/")
        const Icon = item.icon
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex flex-1 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium",
              active ? "bg-secondary text-secondary-foreground" : "text-muted-foreground",
            )}
          >
            <Icon className="size-4" />
            {item.label}
          </Link>
        )
      })}
    </>
  )
}
