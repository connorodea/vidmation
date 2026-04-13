"use client"

import { Clock } from "lucide-react"

export default function SchedulePage() {
  return (
    <div className="p-8 lg:p-12">
      {/* Header */}
      <div className="mb-10 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-[32px] font-semibold tracking-tight text-foreground">Schedule</h1>
          <p className="mt-1 text-[13px] text-foreground/50">
            Schedule video uploads and automate publishing.
          </p>
        </div>
      </div>

      {/* Empty State */}
      <div className="flex flex-col items-center justify-center rounded-xl border border-foreground/10 py-24">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-foreground/5">
          <Clock className="h-6 w-6 text-foreground/30" />
        </div>
        <h2 className="mt-4 text-[15px] font-medium text-foreground">
          Scheduling coming soon
        </h2>
        <p className="mt-1.5 max-w-sm text-center text-[13px] text-foreground/50">
          Schedule video uploads to YouTube, set up recurring publishing automations, and manage your content pipeline.
        </p>
      </div>
    </div>
  )
}
