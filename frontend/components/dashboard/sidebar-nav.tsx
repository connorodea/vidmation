"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { Logo } from "@/components/logo"
import {
  LayoutDashboard,
  Video,
  Radio,
  ListTodo,
  BarChart3,
  Calendar,
  Mic2,
  Clock,
  Settings,
  LogOut,
  ChevronDown,
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

const nav = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Videos", href: "/videos", icon: Video },
  { name: "Channels", href: "/channels", icon: Radio },
  { name: "Jobs", href: "/jobs", icon: ListTodo, badge: 2 },
  { name: "Analytics", href: "/analytics", icon: BarChart3 },
  { name: "Content", href: "/content", icon: Calendar },
  { name: "Voices", href: "/voices", icon: Mic2 },
  { name: "Schedule", href: "/schedule", icon: Clock },
]

export function SidebarNav() {
  const pathname = usePathname()

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-[200px] flex-col border-r border-foreground/[0.06] bg-background">
      <div className="flex h-14 items-center px-5">
        <Link href="/dashboard">
          <Logo size="sm" />
        </Link>
      </div>

      <nav className="flex-1 px-3 py-1">
        {nav.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/")
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] transition-colors mb-0.5",
                active
                  ? "bg-foreground text-background font-medium"
                  : "text-foreground/50 hover:text-foreground hover:bg-foreground/[0.03]"
              )}
            >
              <item.icon className="h-4 w-4" strokeWidth={1.5} />
              {item.name}
              {item.badge && (
                <span className={cn(
                  "ml-auto text-[10px] font-medium rounded-full px-1.5 py-0.5 min-w-[18px] text-center",
                  active ? "bg-background/20 text-background" : "bg-foreground/10 text-foreground/60"
                )}>
                  {item.badge}
                </span>
              )}
            </Link>
          )
        })}
      </nav>

      <div className="border-t border-foreground/[0.06] px-3 py-2">
        <Link
          href="/settings"
          className={cn(
            "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] transition-colors",
            pathname === "/settings"
              ? "bg-foreground text-background font-medium"
              : "text-foreground/50 hover:text-foreground hover:bg-foreground/[0.03]"
          )}
        >
          <Settings className="h-4 w-4" strokeWidth={1.5} />
          Settings
        </Link>
      </div>

      <div className="border-t border-foreground/[0.06] p-3">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 hover:bg-foreground/[0.03] transition-colors">
              <div className="h-7 w-7 rounded-full bg-foreground text-background flex items-center justify-center text-[11px] font-medium">
                U
              </div>
              <span className="flex-1 text-left text-[13px] font-medium truncate">User</span>
              <ChevronDown className="h-3.5 w-3.5 text-foreground/30" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-48 rounded-xl p-1">
            <DropdownMenuItem asChild className="rounded-lg text-[13px] cursor-pointer">
              <Link href="/settings">Account</Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild className="rounded-lg text-[13px] cursor-pointer">
              <Link href="/settings">Billing</Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator className="my-1" />
            <DropdownMenuItem asChild className="rounded-lg text-[13px] cursor-pointer">
              <Link href="/login" className="text-destructive">
                <LogOut className="mr-2 h-4 w-4" />
                Sign out
              </Link>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </aside>
  )
}
