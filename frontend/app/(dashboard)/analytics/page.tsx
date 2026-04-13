"use client"

import { useState, useEffect } from "react"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Loader2 } from "lucide-react"
import { apiFetch } from "@/lib/api"

interface BillingUsage {
  videos_generated: number
  videos_limit: number
  can_generate: boolean
}

export default function AnalyticsPage() {
  const [period, setPeriod] = useState("weekly")
  const [usage, setUsage] = useState<BillingUsage | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchUsage = async () => {
      try {
        setError(null)
        const data = await apiFetch<BillingUsage>("/billing/usage")
        setUsage(data)
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Failed to load analytics"
        setError(message)
      } finally {
        setIsLoading(false)
      }
    }
    fetchUsage()
  }, [])

  if (isLoading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-foreground/40" />
      </div>
    )
  }

  return (
    <div className="p-8 lg:p-12">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-[32px] font-semibold tracking-tight">Analytics</h1>
          <p className="mt-1 text-[15px] text-foreground/60">
            Track costs and usage
          </p>
        </div>
        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="h-8 w-24 rounded-full border-foreground/10 bg-transparent text-[12px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="daily">Daily</SelectItem>
            <SelectItem value="weekly">Weekly</SelectItem>
            <SelectItem value="monthly">Monthly</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Error */}
      {error && (
        <div className="mt-4 rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-[13px] text-destructive">
          {error}
        </div>
      )}

      {/* Stats */}
      <div className="mt-10 grid gap-6 sm:grid-cols-3">
        <div>
          <p className="text-[12px] font-medium text-foreground/50">Videos Generated</p>
          <p className="mt-1 text-[40px] font-semibold tracking-tight">
            {usage?.videos_generated ?? 0}
          </p>
        </div>
        <div>
          <p className="text-[12px] font-medium text-foreground/50">Videos Limit</p>
          <p className="mt-1 text-[40px] font-semibold tracking-tight">
            {usage?.videos_limit ?? 0}
          </p>
        </div>
        <div>
          <p className="text-[12px] font-medium text-foreground/50">Can Generate</p>
          <p className="mt-1 text-[40px] font-semibold tracking-tight">
            {usage?.can_generate ? "Yes" : "No"}
          </p>
        </div>
      </div>

      {/* Usage Bar */}
      {usage && usage.videos_limit > 0 && (
        <div className="mt-8">
          <div className="mb-1.5 flex items-center justify-between text-[12px]">
            <span className="text-foreground/60">Usage</span>
            <span className="font-medium">
              {usage.videos_generated} / {usage.videos_limit}
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-foreground/10">
            <div
              className="h-full rounded-full bg-foreground transition-all"
              style={{
                width: `${Math.min((usage.videos_generated / usage.videos_limit) * 100, 100)}%`,
              }}
            />
          </div>
        </div>
      )}

      {/* Daily Trend - Empty State */}
      <div className="mt-12">
        <h2 className="text-[15px] font-semibold">Daily Trend</h2>
        <div className="mt-6 flex h-48 items-center justify-center rounded-xl border border-foreground/10">
          <p className="text-[13px] text-foreground/40">Analytics data coming soon</p>
        </div>
      </div>

      {/* By Service - Empty State */}
      <div className="mt-12">
        <h2 className="text-[15px] font-semibold">By Service</h2>
        <div className="mt-4 flex items-center justify-center rounded-xl border border-foreground/10 py-12">
          <p className="text-[13px] text-foreground/40">Analytics data coming soon</p>
        </div>
      </div>
    </div>
  )
}
