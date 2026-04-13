"use client"

import { useState } from "react"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

const mockAnalytics = {
  total_cost: 45.20,
  total_calls: 1250,
  videos_generated: 42,
  by_service: [
    { name: "Flux Images", cost: 18.30 },
    { name: "OpenAI TTS", cost: 12.50 },
    { name: "GPT-4o", cost: 10.40 },
    { name: "Whisper", cost: 4.00 },
  ],
  daily_trend: [
    { date: "1", cost: 3.20 },
    { date: "2", cost: 4.80 },
    { date: "3", cost: 2.40 },
    { date: "4", cost: 5.60 },
    { date: "5", cost: 6.20 },
    { date: "6", cost: 4.40 },
    { date: "7", cost: 3.80 },
  ],
}

export default function AnalyticsPage() {
  const [period, setPeriod] = useState("weekly")
  const maxCost = Math.max(...mockAnalytics.daily_trend.map((d) => d.cost))

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

      {/* Stats */}
      <div className="mt-10 grid gap-6 sm:grid-cols-3">
        <div>
          <p className="text-[12px] font-medium text-foreground/50">Total Cost</p>
          <p className="mt-1 text-[40px] font-semibold tracking-tight">${mockAnalytics.total_cost.toFixed(2)}</p>
        </div>
        <div>
          <p className="text-[12px] font-medium text-foreground/50">Videos</p>
          <p className="mt-1 text-[40px] font-semibold tracking-tight">{mockAnalytics.videos_generated}</p>
        </div>
        <div>
          <p className="text-[12px] font-medium text-foreground/50">Avg. Cost</p>
          <p className="mt-1 text-[40px] font-semibold tracking-tight">
            ${(mockAnalytics.total_cost / mockAnalytics.videos_generated).toFixed(2)}
          </p>
        </div>
      </div>

      {/* Chart */}
      <div className="mt-12">
        <h2 className="text-[15px] font-semibold">Daily Trend</h2>
        <div className="mt-6 flex h-48 items-end gap-2">
          {mockAnalytics.daily_trend.map((day, i) => (
            <div key={i} className="flex flex-1 flex-col items-center gap-3">
              <div className="relative w-full flex justify-center">
                <div
                  className="w-full max-w-[40px] rounded-t-lg bg-foreground transition-all hover:bg-foreground/80"
                  style={{ height: `${(day.cost / maxCost) * 160}px`, minHeight: "4px" }}
                />
              </div>
              <div className="text-center">
                <p className="text-[13px] font-medium">${day.cost.toFixed(0)}</p>
                <p className="text-[11px] text-foreground/40">Apr {day.date}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* By Service */}
      <div className="mt-12">
        <h2 className="text-[15px] font-semibold">By Service</h2>
        <div className="mt-4 rounded-xl border border-foreground/10 divide-y divide-foreground/10">
          {mockAnalytics.by_service.map((service, i) => {
            const percentage = (service.cost / mockAnalytics.total_cost) * 100
            return (
              <div key={i} className="flex items-center justify-between p-4">
                <div className="flex items-center gap-4">
                  <span className="text-[14px] font-medium">{service.name}</span>
                  <div className="hidden sm:block h-1.5 w-32 overflow-hidden rounded-full bg-foreground/10">
                    <div className="h-full rounded-full bg-foreground" style={{ width: `${percentage}%` }} />
                  </div>
                </div>
                <span className="text-[14px] font-semibold">${service.cost.toFixed(2)}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
