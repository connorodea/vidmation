"use client"

import { SidebarNav } from "@/components/dashboard/sidebar-nav"
import { AuthProvider, useAuth } from "@/lib/auth-context"

function DashboardContent({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()

  const sidebarUser = {
    name: user?.name || "User",
    email: user?.email || "",
    subscription_tier: user?.subscription_tier || "free",
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-foreground/30 text-sm">Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <SidebarNav user={sidebarUser} />
      <main className="pl-[200px]">
        <div className="min-h-screen bg-background">{children}</div>
      </main>
    </div>
  )
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <AuthProvider>
      <DashboardContent>{children}</DashboardContent>
    </AuthProvider>
  )
}
