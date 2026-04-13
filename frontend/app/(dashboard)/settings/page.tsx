"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { cn } from "@/lib/utils"
import { Eye, EyeOff, Copy, Check } from "lucide-react"

const tabs = ["Account", "Billing", "Notifications", "API"]

const mockUser = {
  name: "Demo User",
  email: "demo@aividio.com",
  subscription_tier: "pro",
}

const notifications = [
  { id: "video_ready", label: "Video ready for download", enabled: true },
  { id: "job_failed", label: "Job failed or error", enabled: true },
  { id: "upload_complete", label: "YouTube upload complete", enabled: true },
  { id: "weekly_summary", label: "Weekly cost summary", enabled: false },
]

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("Account")
  const [name, setName] = useState(mockUser.name)
  const [email, setEmail] = useState(mockUser.email)
  const [showApiKey, setShowApiKey] = useState(false)
  const [notificationSettings, setNotificationSettings] = useState(notifications)

  const handleNotificationToggle = (id: string) => {
    setNotificationSettings((prev) =>
      prev.map((n) => (n.id === id ? { ...n, enabled: !n.enabled } : n))
    )
  }

  return (
    <div className="p-8 lg:p-12">
      {/* Header */}
      <h1 className="text-[32px] font-semibold tracking-tight">Settings</h1>
      <p className="mt-1 text-[15px] text-foreground/60">
        Manage your account and preferences
      </p>

      {/* Tabs */}
      <div className="mt-8 flex gap-1 border-b border-foreground/10">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "px-4 py-2.5 text-[13px] font-medium transition-colors",
              activeTab === tab
                ? "border-b-2 border-foreground text-foreground"
                : "text-foreground/50 hover:text-foreground"
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="mt-8 max-w-xl">
        {activeTab === "Account" && (
          <div className="space-y-8">
            <div className="space-y-4">
              <h2 className="text-[15px] font-semibold">Profile</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label className="text-[13px]">Name</Label>
                  <Input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="h-10 rounded-xl border-foreground/10"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-[13px]">Email</Label>
                  <Input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="h-10 rounded-xl border-foreground/10"
                  />
                </div>
              </div>
              <Button className="h-9 rounded-full bg-foreground px-5 text-[13px] text-background">
                Save Changes
              </Button>
            </div>

            <div className="border-t border-foreground/10 pt-8">
              <h2 className="text-[15px] font-semibold">Password</h2>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label className="text-[13px]">Current Password</Label>
                  <Input type="password" className="h-10 rounded-xl border-foreground/10" />
                </div>
                <div className="space-y-2">
                  <Label className="text-[13px]">New Password</Label>
                  <Input type="password" className="h-10 rounded-xl border-foreground/10" />
                </div>
              </div>
              <Button variant="outline" className="mt-4 h-9 rounded-full border-foreground/10 px-5 text-[13px]">
                Change Password
              </Button>
            </div>

            <div className="border-t border-foreground/10 pt-8">
              <h2 className="text-[15px] font-semibold text-destructive">Danger Zone</h2>
              <p className="mt-1 text-[13px] text-foreground/60">
                Permanently delete your account and all data.
              </p>
              <Button variant="destructive" className="mt-4 h-9 rounded-full px-5 text-[13px]">
                Delete Account
              </Button>
            </div>
          </div>
        )}

        {activeTab === "Billing" && (
          <div className="space-y-8">
            <div>
              <h2 className="text-[15px] font-semibold">Current Plan</h2>
              <div className="mt-4 rounded-xl border border-foreground/10 p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-[17px] font-semibold capitalize">{mockUser.subscription_tier}</span>
                      <span className="rounded-full bg-foreground px-2 py-0.5 text-[10px] font-medium text-background">
                        Active
                      </span>
                    </div>
                    <p className="mt-1 text-[13px] text-foreground/60">$29/month · 30 videos · 1080p</p>
                  </div>
                  <Button variant="outline" className="h-9 rounded-full border-foreground/10 px-4 text-[13px]">
                    Manage
                  </Button>
                </div>
                <div className="mt-5">
                  <div className="mb-1.5 flex items-center justify-between text-[12px]">
                    <span className="text-foreground/60">Videos used</span>
                    <span className="font-medium">12 / 30</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-foreground/10">
                    <div className="h-full w-2/5 rounded-full bg-foreground" />
                  </div>
                </div>
              </div>
            </div>

            <div className="border-t border-foreground/10 pt-8">
              <h2 className="text-[15px] font-semibold">Payment Method</h2>
              <div className="mt-4 flex items-center justify-between rounded-xl border border-foreground/10 p-4">
                <div className="flex items-center gap-3">
                  <div className="rounded bg-foreground/5 px-2 py-1 text-[10px] font-bold">VISA</div>
                  <div>
                    <p className="text-[13px] font-medium">•••• 4242</p>
                    <p className="text-[11px] text-foreground/50">Expires 12/28</p>
                  </div>
                </div>
                <Button variant="ghost" className="h-8 rounded-full px-3 text-[12px]">Update</Button>
              </div>
            </div>

            <div className="border-t border-foreground/10 pt-8">
              <h2 className="text-[15px] font-semibold">History</h2>
              <div className="mt-4 rounded-xl border border-foreground/10 divide-y divide-foreground/10">
                {["Apr 1, 2026", "Mar 1, 2026", "Feb 1, 2026"].map((date, i) => (
                  <div key={i} className="flex items-center justify-between p-4">
                    <div className="flex items-center gap-3">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-foreground">
                        <Check className="h-3 w-3 text-background" />
                      </div>
                      <div>
                        <p className="text-[13px] font-medium">{date}</p>
                        <p className="text-[11px] text-foreground/50">Pro subscription</p>
                      </div>
                    </div>
                    <span className="text-[13px] font-semibold">$29.00</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === "Notifications" && (
          <div>
            <h2 className="text-[15px] font-semibold">Preferences</h2>
            <p className="mt-1 text-[13px] text-foreground/60">
              Choose what notifications you want to receive.
            </p>
            <div className="mt-6 rounded-xl border border-foreground/10 divide-y divide-foreground/10">
              {notificationSettings.map((notification) => (
                <div key={notification.id} className="flex items-center justify-between p-4">
                  <span className="text-[14px]">{notification.label}</span>
                  <Switch
                    checked={notification.enabled}
                    onCheckedChange={() => handleNotificationToggle(notification.id)}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "API" && (
          <div>
            <h2 className="text-[15px] font-semibold">API Key</h2>
            <p className="mt-1 text-[13px] text-foreground/60">
              Use this key to access the AIVidio API.
            </p>
            <div className="mt-6 flex items-center gap-2">
              <div className="flex-1 rounded-xl border border-foreground/10 px-4 py-3 font-mono text-[13px]">
                {showApiKey ? "sk_live_abc123xyz789def456" : "sk_live_••••••••••••••••"}
              </div>
              <Button
                variant="outline"
                size="icon"
                className="h-10 w-10 rounded-xl border-foreground/10"
                onClick={() => setShowApiKey(!showApiKey)}
              >
                {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
              <Button variant="outline" size="icon" className="h-10 w-10 rounded-xl border-foreground/10">
                <Copy className="h-4 w-4" />
              </Button>
            </div>
            <div className="mt-4 flex gap-2">
              <Button variant="outline" className="h-9 rounded-full border-foreground/10 px-4 text-[13px]">
                Regenerate Key
              </Button>
              <Button variant="outline" className="h-9 rounded-full border-foreground/10 px-4 text-[13px]">
                View Docs
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
