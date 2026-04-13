"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { cn } from "@/lib/utils"
import { Loader2 } from "lucide-react"
import { useAuth } from "@/lib/auth-context"
import { apiFetch, authFetch } from "@/lib/api"

const tabs = ["Account", "Billing", "Notifications", "API"]

const defaultNotifications = [
  { id: "video_ready", label: "Video ready for download", enabled: true },
  { id: "job_failed", label: "Job failed or error", enabled: true },
  { id: "upload_complete", label: "YouTube upload complete", enabled: true },
  { id: "weekly_summary", label: "Weekly cost summary", enabled: false },
]

interface BillingPlan {
  tier: string
  is_active: boolean
  expires_at: string | null
}

interface BillingUsage {
  videos_generated: number
  videos_limit: number
  can_generate: boolean
}

export default function SettingsPage() {
  const { user, refreshUser } = useAuth()
  const [activeTab, setActiveTab] = useState("Account")
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [notificationSettings, setNotificationSettings] = useState(defaultNotifications)

  // Billing state
  const [billingPlan, setBillingPlan] = useState<BillingPlan | null>(null)
  const [billingUsage, setBillingUsage] = useState<BillingUsage | null>(null)
  const [billingLoading, setBillingLoading] = useState(false)

  // Feedback state
  const [profileSaving, setProfileSaving] = useState(false)
  const [profileMessage, setProfileMessage] = useState<string | null>(null)
  const [passwordSaving, setPasswordSaving] = useState(false)
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Populate fields from auth user
  useEffect(() => {
    if (user) {
      setName(user.name)
      setEmail(user.email)
    }
  }, [user])

  // Fetch billing data when tab becomes Billing
  useEffect(() => {
    if (activeTab === "Billing") {
      const fetchBilling = async () => {
        setBillingLoading(true)
        try {
          const [plan, usage] = await Promise.all([
            apiFetch<BillingPlan>("/billing/current-plan").catch(() => null),
            apiFetch<BillingUsage>("/billing/usage").catch(() => null),
          ])
          setBillingPlan(plan)
          setBillingUsage(usage)
        } catch {
          // Billing endpoints may not be available yet
        } finally {
          setBillingLoading(false)
        }
      }
      fetchBilling()
    }
  }, [activeTab])

  const handleSaveProfile = async () => {
    setProfileSaving(true)
    setProfileMessage(null)
    setError(null)
    try {
      await authFetch("/me", {
        method: "PUT",
        body: JSON.stringify({ name, email }),
      })
      await refreshUser()
      setProfileMessage("Profile updated successfully.")
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to update profile"
      setError(message)
    } finally {
      setProfileSaving(false)
    }
  }

  const handleChangePassword = async () => {
    if (!currentPassword || !newPassword) return
    setPasswordSaving(true)
    setPasswordMessage(null)
    setError(null)
    try {
      await authFetch("/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      })
      setCurrentPassword("")
      setNewPassword("")
      setPasswordMessage("Password changed successfully.")
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to change password"
      setError(message)
    } finally {
      setPasswordSaving(false)
    }
  }

  const handleNotificationToggle = (id: string) => {
    setNotificationSettings((prev) =>
      prev.map((n) => (n.id === id ? { ...n, enabled: !n.enabled } : n))
    )
  }

  if (!user) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-foreground/40" />
      </div>
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

      {/* Error */}
      {error && (
        <div className="mt-4 max-w-xl rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-[13px] text-destructive">
          {error}
        </div>
      )}

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
              {profileMessage && (
                <p className="text-[13px] text-green-600">{profileMessage}</p>
              )}
              <Button
                onClick={handleSaveProfile}
                disabled={profileSaving}
                className="h-9 rounded-full bg-foreground px-5 text-[13px] text-background"
              >
                {profileSaving && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
                Save Changes
              </Button>
            </div>

            <div className="border-t border-foreground/10 pt-8">
              <h2 className="text-[15px] font-semibold">Password</h2>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label className="text-[13px]">Current Password</Label>
                  <Input
                    type="password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="h-10 rounded-xl border-foreground/10"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-[13px]">New Password</Label>
                  <Input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="h-10 rounded-xl border-foreground/10"
                  />
                </div>
              </div>
              {passwordMessage && (
                <p className="mt-2 text-[13px] text-green-600">{passwordMessage}</p>
              )}
              <Button
                variant="outline"
                onClick={handleChangePassword}
                disabled={!currentPassword || !newPassword || passwordSaving}
                className="mt-4 h-9 rounded-full border-foreground/10 px-5 text-[13px]"
              >
                {passwordSaving && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
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
            {billingLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-foreground/40" />
              </div>
            ) : (
              <>
                <div>
                  <h2 className="text-[15px] font-semibold">Current Plan</h2>
                  <div className="mt-4 rounded-xl border border-foreground/10 p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-[17px] font-semibold capitalize">
                            {billingPlan?.tier ?? user.subscription_tier}
                          </span>
                          <span className="rounded-full bg-foreground px-2 py-0.5 text-[10px] font-medium text-background">
                            {billingPlan?.is_active !== false ? "Active" : "Inactive"}
                          </span>
                        </div>
                      </div>
                      <Button variant="outline" className="h-9 rounded-full border-foreground/10 px-4 text-[13px]">
                        Manage
                      </Button>
                    </div>
                    {billingUsage && (
                      <div className="mt-5">
                        <div className="mb-1.5 flex items-center justify-between text-[12px]">
                          <span className="text-foreground/60">Videos used</span>
                          <span className="font-medium">
                            {billingUsage.videos_generated} / {billingUsage.videos_limit}
                          </span>
                        </div>
                        <div className="h-1.5 overflow-hidden rounded-full bg-foreground/10">
                          <div
                            className="h-full rounded-full bg-foreground"
                            style={{
                              width: `${billingUsage.videos_limit > 0 ? Math.min((billingUsage.videos_generated / billingUsage.videos_limit) * 100, 100) : 0}%`,
                            }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="border-t border-foreground/10 pt-8">
                  <h2 className="text-[15px] font-semibold">Payment Method</h2>
                  <div className="mt-4 rounded-xl border border-foreground/10 p-4">
                    <p className="text-[13px] text-foreground/50">Not configured</p>
                  </div>
                </div>

                <div className="border-t border-foreground/10 pt-8">
                  <h2 className="text-[15px] font-semibold">History</h2>
                  <div className="mt-4 rounded-xl border border-foreground/10 p-4">
                    <p className="text-[13px] text-foreground/50">Not configured</p>
                  </div>
                </div>
              </>
            )}
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
            <div className="mt-6 rounded-xl border border-foreground/10 p-4">
              <p className="text-[13px] text-foreground/50">Not configured</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
