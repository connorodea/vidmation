"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import {
  Plus,
  ArrowUpRight,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from "lucide-react"
import { apiFetch } from "@/lib/api"

interface Video {
  id: string
  title: string
  status: string
  created_at?: string
}

interface Job {
  id: string
  video_id?: string
  title: string
  stage: string
  progress: number
  status: string
}

function timeAgo(dateStr?: string): string {
  if (!dateStr) return ""
  const h = Math.floor((Date.now() - new Date(dateStr).getTime()) / 3600000)
  if (h < 1) return "Just now"
  if (h < 24) return `${h}h ago`
  if (h < 48) return "Yesterday"
  const d = Math.floor(h / 24)
  return `${d}d ago`
}

export default function DashboardPage() {
  const [videos, setVideos] = useState<Video[]>([])
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        const [videosRes, jobsRes] = await Promise.allSettled([
          apiFetch<Video[]>("/videos"),
          apiFetch<Job[]>("/jobs?status=running"),
        ])
        if (videosRes.status === "fulfilled") setVideos(videosRes.value ?? [])
        if (jobsRes.status === "fulfilled") setJobs(jobsRes.value ?? [])
      } catch {
        // errors handled via allSettled — defaults remain []
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const totalVideos = videos.length
  const processingCount = jobs.length
  const completedVideos = videos.filter((v) => v.status === "ready" || v.status === "uploaded")
  const failedVideos = videos.filter((v) => v.status === "failed")
  const successRate = totalVideos > 0 ? Math.round(((totalVideos - failedVideos.length) / totalVideos) * 100) : 0

  const stats = [
    { label: "Videos", value: String(totalVideos), change: `${totalVideos} total` },
    { label: "Processing", value: String(processingCount), change: processingCount > 0 ? "active now" : "none active" },
    { label: "Completed", value: String(completedVideos.length), change: "ready or live" },
    { label: "Success", value: `${successRate}%`, change: "completion" },
  ]

  const recentVideos = [...videos]
    .sort((a, b) => new Date(b.created_at ?? 0).getTime() - new Date(a.created_at ?? 0).getTime())
    .slice(0, 4)

  if (loading) {
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
        {/* Stats skeleton */}
        <div className="grid grid-cols-4 gap-px bg-foreground/[0.06] rounded-xl overflow-hidden mb-10">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-background p-5">
              <div className="h-3 w-16 bg-foreground/[0.06] rounded animate-pulse" />
              <div className="h-7 w-12 bg-foreground/[0.06] rounded animate-pulse mt-2" />
              <div className="h-2.5 w-20 bg-foreground/[0.06] rounded animate-pulse mt-2" />
            </div>
          ))}
        </div>
        <div className="grid lg:grid-cols-2 gap-10">
          <div>
            <div className="h-5 w-24 bg-foreground/[0.06] rounded animate-pulse mb-4" />
            <div className="space-y-2">
              {[1, 2].map((i) => (
                <div key={i} className="rounded-xl border border-foreground/[0.06] p-4">
                  <div className="h-4 w-48 bg-foreground/[0.06] rounded animate-pulse mb-3" />
                  <div className="h-1 bg-foreground/[0.06] rounded-full" />
                </div>
              ))}
            </div>
          </div>
          <div>
            <div className="h-5 w-28 bg-foreground/[0.06] rounded animate-pulse mb-4" />
            <div className="rounded-xl border border-foreground/[0.06] divide-y divide-foreground/[0.06]">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="p-3.5">
                  <div className="h-3.5 w-44 bg-foreground/[0.06] rounded animate-pulse" />
                  <div className="h-2.5 w-16 bg-foreground/[0.06] rounded animate-pulse mt-1.5" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

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

          {jobs.length === 0 ? (
            <div className="rounded-xl border border-foreground/[0.06] p-8 text-center">
              <p className="text-[13px] text-foreground/40">No active jobs</p>
            </div>
          ) : (
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
          )}
        </div>

        {/* Recent Videos */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[15px] font-semibold">Recent Videos</h2>
            <Link href="/videos" className="text-[13px] text-foreground/40 hover:text-foreground transition-colors">
              View all
            </Link>
          </div>

          {recentVideos.length === 0 ? (
            <div className="rounded-xl border border-foreground/[0.06] p-8 text-center">
              <p className="text-[13px] text-foreground/40">No videos yet</p>
            </div>
          ) : (
            <div className="rounded-xl border border-foreground/[0.06] divide-y divide-foreground/[0.06]">
              {recentVideos.map((video) => (
                <Link
                  key={video.id}
                  href={`/videos/${video.id}`}
                  className="flex items-center justify-between p-3.5 hover:bg-foreground/[0.02] transition-colors"
                >
                  <div>
                    <p className="text-[13px] font-medium">{video.title}</p>
                    <p className="text-[11px] text-foreground/40 mt-0.5">{timeAgo(video.created_at)}</p>
                  </div>
                  <span className={`flex items-center gap-1 text-[11px] ${
                    video.status === "ready" ? "text-foreground/60" :
                    video.status === "uploaded" ? "text-foreground" :
                    "text-foreground/30"
                  }`}>
                    {video.status === "ready" && <CheckCircle2 className="h-3 w-3" />}
                    {video.status === "uploaded" && <ArrowUpRight className="h-3 w-3" />}
                    {video.status === "failed" && <AlertCircle className="h-3 w-3" />}
                    {video.status === "ready" ? "Ready" : video.status === "uploaded" ? "Live" : video.status === "failed" ? "Failed" : video.status}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
