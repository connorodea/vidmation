"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  MoreHorizontal,
  Eye,
  XCircle,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Clock,
} from "lucide-react"
import { apiFetch } from "@/lib/api"

interface Job {
  id: string
  video_id: string
  title: string
  status: string
  stage: string | null
  progress: number
  eta?: number
  started?: string | null
  error?: string
}

const statusConfig: Record<string, { icon: typeof Clock; color: string; label: string; animate?: boolean }> = {
  queued: { icon: Clock, color: "text-muted-foreground", label: "Queued" },
  running: { icon: Loader2, color: "text-amber-600", label: "Running", animate: true },
  completed: { icon: CheckCircle2, color: "text-emerald-600", label: "Done" },
  failed: { icon: AlertCircle, color: "text-red-600", label: "Failed" },
}

export default function JobsPage() {
  const [filter, setFilter] = useState("all")
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchJobs() {
      try {
        const data = await apiFetch<Job[]>("/jobs")
        setJobs(data ?? [])
      } catch {
        setJobs([])
      } finally {
        setLoading(false)
      }
    }
    fetchJobs()
  }, [])

  const filtered = jobs.filter((j) => filter === "all" || j.status === filter)
  const running = jobs.filter((j) => j.status === "running").length
  const queued = jobs.filter((j) => j.status === "queued").length

  return (
    <div className="p-8 lg:p-12">
      {/* Header */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-[32px] font-semibold tracking-tight">Jobs</h1>
          <p className="mt-1 text-[15px] text-muted-foreground">Monitor video generation progress.</p>
        </div>
        <div className="flex items-center gap-2 text-[13px]">
          {loading ? (
            <span className="text-muted-foreground">Loading...</span>
          ) : (
            <>
              <span className="text-amber-600">{running} running</span>
              <span className="text-muted-foreground">·</span>
              <span className="text-muted-foreground">{queued} queued</span>
            </>
          )}
        </div>
      </div>

      {/* Filter */}
      <div className="mb-6 flex gap-1 rounded-lg border border-border/60 p-1 w-fit">
        {["all", "running", "completed", "failed"].map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`rounded-md px-3 py-1 text-[12px] font-medium transition-all ${
              filter === s ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {s === "all" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div className="overflow-hidden rounded-xl border border-border/60">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border/60 bg-muted/30">
                <th className="px-4 py-3 text-left text-[12px] font-medium text-muted-foreground">Video</th>
                <th className="px-4 py-3 text-left text-[12px] font-medium text-muted-foreground">Status</th>
                <th className="px-4 py-3 text-left text-[12px] font-medium text-muted-foreground">Progress</th>
                <th className="px-4 py-3 text-left text-[12px] font-medium text-muted-foreground">Stage</th>
                <th className="w-10 px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {[1, 2, 3, 4].map((i) => (
                <tr key={i}>
                  <td className="px-4 py-3"><div className="h-3.5 w-52 bg-muted/50 rounded animate-pulse" /></td>
                  <td className="px-4 py-3"><div className="h-3 w-16 bg-muted/50 rounded animate-pulse" /></td>
                  <td className="px-4 py-3"><div className="h-1 w-24 bg-muted/50 rounded animate-pulse" /></td>
                  <td className="px-4 py-3"><div className="h-3 w-16 bg-muted/50 rounded animate-pulse" /></td>
                  <td className="px-4 py-3"></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Jobs Table */}
      {!loading && filtered.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-border/60">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border/60 bg-muted/30">
                <th className="px-4 py-3 text-left text-[12px] font-medium text-muted-foreground">Video</th>
                <th className="px-4 py-3 text-left text-[12px] font-medium text-muted-foreground">Status</th>
                <th className="px-4 py-3 text-left text-[12px] font-medium text-muted-foreground">Progress</th>
                <th className="px-4 py-3 text-left text-[12px] font-medium text-muted-foreground">Stage</th>
                <th className="w-10 px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {filtered.map((job) => {
                const status = statusConfig[job.status as keyof typeof statusConfig]
                const StatusIcon = status?.icon ?? Clock
                const statusColor = status?.color ?? "text-muted-foreground"
                const statusLabel = status?.label ?? job.status
                const statusAnimate = status?.animate ?? false
                return (
                  <tr key={job.id} className="transition-colors hover:bg-muted/20">
                    <td className="px-4 py-3">
                      <Link href={`/videos/${job.video_id}`} className="text-[13px] font-medium hover:text-primary">
                        {job.title}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1.5 text-[12px] ${statusColor}`}>
                        <StatusIcon className={`h-3.5 w-3.5 ${statusAnimate ? "animate-spin" : ""}`} />
                        {statusLabel}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 w-24">
                        <Progress value={job.progress} className="h-1" />
                        <span className="text-[12px] text-muted-foreground w-8">{job.progress}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-[13px] capitalize text-muted-foreground">
                      {job.stage || "-"}
                    </td>
                    <td className="px-4 py-3">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-7 w-7 rounded-md">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-36">
                          <DropdownMenuItem asChild className="text-[13px]">
                            <Link href={`/videos/${job.video_id}`}>
                              <Eye className="mr-2 h-3.5 w-3.5" /> View
                            </Link>
                          </DropdownMenuItem>
                          {job.status === "running" && (
                            <DropdownMenuItem className="text-[13px] text-destructive">
                              <XCircle className="mr-2 h-3.5 w-3.5" /> Cancel
                            </DropdownMenuItem>
                          )}
                          {job.status === "failed" && (
                            <DropdownMenuItem className="text-[13px]">
                              <RefreshCw className="mr-2 h-3.5 w-3.5" /> Retry
                            </DropdownMenuItem>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {!loading && filtered.length === 0 && (
        <div className="flex flex-col items-center py-16 text-center">
          <Clock className="h-10 w-10 text-muted-foreground/30" strokeWidth={1.5} />
          <p className="mt-4 text-[14px] font-medium">No jobs found</p>
          <p className="mt-1 text-[13px] text-muted-foreground">Jobs appear when you create videos</p>
        </div>
      )}
    </div>
  )
}
