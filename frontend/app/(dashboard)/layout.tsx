import { SidebarNav } from "@/components/dashboard/sidebar-nav"

// Mock user data - in production, this would come from auth
const mockUser = {
  name: "Demo User",
  email: "demo@aividio.com",
  subscription_tier: "pro",
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-background">
      <SidebarNav user={mockUser} />
      <main className="pl-[200px]">
        <div className="min-h-screen bg-background">{children}</div>
      </main>
    </div>
  )
}
