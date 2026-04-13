"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import {
  Plus,
  ArrowUpRight,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from "lucide-react"

const stats = [
  { label: "Videos", value: "12", change: "+3 this week" },
  { label: "Processing", value: "2", change: "active now" },
  { label: "Cost", value: "$8.40", change: "this month" },
  { label: "Success", value: "98%", change: "completion" },
]

const jobs = [
  { id: "1", title: "The Psychology of Wealth Building", stage: "Creating visuals", progress: 65 },
  { id: "2", title: "5 AI Tools That Will Change 2026", stage: "Generating voiceover", progress: 32 },
]

const videos = [
  { id: "1", title: "The Hidden System Banks Use", status: "ready", time: "2h ago" },
  { id: "2", title: "Why 99% of People Fail at Investing", status: "ready", time: "Yesterday" },
  { id: "3", title: "The Dark Truth About Credit Cards", status: "uploaded", time: "2d ago" },
  { id: "4", title: "How The Rich Avoid Taxes Legally", status: "failed", time: "3d ago" },
]

export default function DashboardPage() {
  return (
    <div className="p-8 lg:p-12 max-w-6xl">
      <div className="flex items-start justify-between mb-10">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-foreground/50 mt-1">Overview of your video generation activity.</p>
        </div>
        <Link href="/videos/new">
          <Button className="h-8 gap-1.5 rounded-lg text-[13px]">
            <Plus className="h-3.5 w-3.5" />
            New Video
          </Button>
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-px bg-foreground/[0.06] rounded-xl overflow-hidden mb-10">
        {stats.map((stat) => (
          <div key={stat.label} className="bg-background p-5">
            <p className="text-[13px] text-foreground/40">{stat.label}</p>
            <p className="text-[28px] font-semibold tracking-tight mt-1">{stat.value}</p>
            <p className="text-[12px] text-foreground/40 mt-0.5">{stat.change}</p>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-10">
        {/* Active Jobs */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[15px] font-semibold">Active Jobs</h2>
            <Link href="/jobs" className="text-[13px] text-foreground/40 hover:text-foreground transition-colors">
              View all
            </Link>
          </div>
          
          <div className="space-y-2">
            {jobs.map((job) => (
              <Link
                key={job.id}
                href={`/jobs/${job.id}`}
                className="block rounded-xl border border-foreground/[0.06] p-4 hover:border-foreground/10 transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="text-[14px] font-medium">{job.title}</p>
                    <p className="text-[12px] text-foreground/40 mt-0.5">{job.stage}</p>
                  </div>
                  <Loader2 className="h-4 w-4 animate-spin text-foreground/30" />
                </div>
                <div className="h-1 bg-foreground/[0.06] rounded-full overflow-hidden">
                  <div className="h-full bg-foreground rounded-full transition-all" style={{ width: `${job.progress}%` }} />
                </div>
                <p className="text-[11px] text-foreground/40 mt-2">{job.progress}%</p>
              </Link>
            ))}
          </div>
        </div>

        {/* Recent Videos */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[15px] font-semibold">Recent Videos</h2>
            <Link href="/videos" className="text-[13px] text-foreground/40 hover:text-foreground transition-colors">
              View all
            </Link>
          </div>
          
          <div className="rounded-xl border border-foreground/[0.06] divide-y divide-foreground/[0.06]">
            {videos.map((video) => (
              <Link
                key={video.id}
                href={`/videos/${video.id}`}
                className="flex items-center justify-between p-3.5 hover:bg-foreground/[0.02] transition-colors"
              >
                <div>
                  <p className="text-[13px] font-medium">{video.title}</p>
                  <p className="text-[11px] text-foreground/40 mt-0.5">{video.time}</p>
                </div>
                <span className={`flex items-center gap-1 text-[11px] ${
                  video.status === "ready" ? "text-foreground/60" :
                  video.status === "uploaded" ? "text-foreground" :
                  "text-foreground/30"
                }`}>
                  {video.status === "ready" && <CheckCircle2 className="h-3 w-3" />}
                  {video.status === "uploaded" && <ArrowUpRight className="h-3 w-3" />}
                  {video.status === "failed" && <AlertCircle className="h-3 w-3" />}
                  {video.status === "ready" ? "Ready" : video.status === "uploaded" ? "Live" : "Failed"}
                </span>
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Cost */}
      <div className="mt-10">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[15px] font-semibold">Cost Breakdown</h2>
          <Link href="/analytics" className="text-[13px] text-foreground/40 hover:text-foreground transition-colors">
            View analytics
          </Link>
        </div>
        
        <div className="grid sm:grid-cols-3 gap-px bg-foreground/[0.06] rounded-xl overflow-hidden">
          {[
            { label: "Voice Generation", value: "$3.20", percent: 38 },
            { label: "Image Generation", value: "$2.80", percent: 33 },
            { label: "Script Writing", value: "$2.40", percent: 29 },
          ].map((item) => (
            <div key={item.label} className="bg-background p-4">
              <div className="flex items-center justify-between text-[13px]">
                <span className="text-foreground/50">{item.label}</span>
                <span className="font-medium">{item.value}</span>
              </div>
              <div className="h-1 bg-foreground/[0.06] rounded-full mt-3 overflow-hidden">
                <div className="h-full bg-foreground rounded-full" style={{ width: `${item.percent}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
