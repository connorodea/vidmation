"use client"

import { Calendar } from "lucide-react"

export default function ContentPage() {
  return (
    <div className="p-8 lg:p-12">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-[32px] font-semibold tracking-tight">Content Planner</h1>
          <p className="mt-1 text-[15px] text-foreground/60">
            Plan your video content calendar
          </p>
        </div>
      </div>

      {/* Empty State */}
      <div className="mt-10 flex flex-col items-center justify-center rounded-xl border border-foreground/10 py-24">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-foreground/5">
          <Calendar className="h-6 w-6 text-foreground/30" />
        </div>
        <h2 className="mt-4 text-[15px] font-medium text-foreground">
          Content calendar coming soon
        </h2>
        <p className="mt-1.5 max-w-sm text-center text-[13px] text-foreground/50">
          Plan and organize your video topics across weeks, track trending ideas, and let AI suggest content for your channels.
        </p>
      </div>
    </div>
  )
}
