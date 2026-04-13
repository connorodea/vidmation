"use client"

import { useState, useEffect, useCallback } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Plus,
  Search,
  Video,
  MoreHorizontal,
  ExternalLink,
  Download,
  Trash2,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Play,
} from "lucide-react"
import { apiFetch } from "@/lib/api"

interface VideoItem {
  id: string
  title: string
  status: string
  duration: number
  style?: string
  channel?: string
  created_at?: string
  created?: string
  youtube?: boolean
}

const statusConfig: Record<string, { icon: typeof CheckCircle2; color: string; label: string; animate?: boolean }> = {
  ready: { icon: CheckCircle2, color: "text-emerald-600", label: "Ready" },
  uploaded: { icon: Play, color: "text-primary", label: "Live" },
  generating: { icon: Loader2, color: "text-amber-600", label: "Processing", animate: true },
  failed: { icon: AlertCircle, color: "text-red-600", label: "Failed" },
}

function formatDuration(s: number) {
  if (!s) return "-"
  return `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, "0")}`
}

function formatDate(d?: string) {
  if (!d) return "-"
  const h = Math.floor((Date.now() - new Date(d).getTime()) / 3600000)
  if (h < 1) return "Just now"
  if (h < 24) return `${h}h ago`
  if (h < 48) return "Yesterday"
  return new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" })
}

export default function VideosPage() {
  const [filter, setFilter] = useState("all")
  const [search, setSearch] = useState("")
  const [videos, setVideos] = useState<VideoItem[]>([])
  const [loading, setLoading] = useState(true)

  const fetchVideos = useCallback(async () => {
    setLoading(true)
    try {
      const data = await apiFetch<VideoItem[]>("/videos")
      setVideos(data ?? [])
    } catch {
      setVideos([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchVideos()
  }, [fetchVideos])

  const filtered = videos.filter((v) => {
    const matchStatus = filter === "all" || v.status === filter
    const matchSearch = v.title.toLowerCase().includes(search.toLowerCase())
    return matchStatus && matchSearch
  })

  return (
    <div className="p-8 lg:p-12">
      {/* Header */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-[32px] font-semibold tracking-tight">Videos</h1>
          <p className="mt-1 text-[15px] text-muted-foreground">Manage all your generated videos.</p>
        </div>
        <Link href="/videos/new">
          <Button className="h-9 gap-1.5 rounded-lg px-4 text-[13px] font-medium">
            <Plus className="h-4 w-4" strokeWidth={2} />
            New Video
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <div className="mb-6 flex items-center gap-3">
        <div className="relative max-w-xs flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/50" />
          <Input
            placeholder="Search..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-9 rounded-lg border-border/60 pl-9 text-[13px]"
          />
        </div>
        <div className="flex gap-1 rounded-lg border border-border/60 p-1">
          {["all", "ready", "uploaded", "generating", "failed"].map((s) => (
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
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div className="overflow-hidden rounded-xl border border-border/60">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border/60 bg-muted/30">
                <th className="px-4 py-3 text-left text-[12px] font-medium text-muted-foreground">Title</th>
                <th className="px-4 py-3 text-left text-[12px] font-medium text-muted-foreground">Status</th>
                <th className="px-4 py-3 text-left text-[12px] font-medium text-muted-foreground">Duration</th>
                <th className="px-4 py-3 text-left text-[12px] font-medium text-muted-foreground">Channel</th>
                <th className="px-4 py-3 text-left text-[12px] font-medium text-muted-foreground">Created</th>
                <th className="w-10 px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {[1, 2, 3, 4, 5].map((i) => (
                <tr key={i}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="h-9 w-14 rounded-md bg-muted/50 animate-pulse" />
                      <div className="h-3.5 w-48 bg-muted/50 rounded animate-pulse" />
                    </div>
                  </td>
                  <td className="px-4 py-3"><div className="h-3 w-16 bg-muted/50 rounded animate-pulse" /></td>
                  <td className="px-4 py-3"><div className="h-3 w-10 bg-muted/50 rounded animate-pulse" /></td>
                  <td className="px-4 py-3"><div className="h-3 w-24 bg-muted/50 rounded animate-pulse" /></td>
                  <td className="px-4 py-3"><div className="h-3 w-16 bg-muted/50 rounded animate-pulse" /></td>
                  <td className="px-4 py-3"></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Table */}
      {!loading && filtered.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-border/60">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border/60 bg-muted/30">
                <th className="px-4 py-3 text-left text-[12px] font-medium text-muted-foreground">Title</th>
                <th className="px-4 py-3 text-left text-[12px] font-medium text-muted-foreground">Status</th>
                <th className="px-4 py-3 text-left text-[12px] font-medium text-muted-foreground">Duration</th>
                <th className="px-4 py-3 text-left text-[12px] font-medium text-muted-foreground">Channel</th>
                <th className="px-4 py-3 text-left text-[12px] font-medium text-muted-foreground">Created</th>
                <th className="w-10 px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {filtered.map((video) => {
                const status = statusConfig[video.status as keyof typeof statusConfig]
                const StatusIcon = status?.icon ?? AlertCircle
                const statusColor = status?.color ?? "text-muted-foreground"
                const statusLabel = status?.label ?? video.status
                const statusAnimate = status?.animate ?? false
                const dateStr = video.created_at || video.created
                return (
                  <tr key={video.id} className="transition-colors hover:bg-muted/20">
                    <td className="px-4 py-3">
                      <Link href={`/videos/${video.id}`} className="group flex items-center gap-3">
                        <div className="flex h-9 w-14 items-center justify-center rounded-md bg-muted/50">
                          <Video className="h-4 w-4 text-muted-foreground/40" />
                        </div>
                        <span className="text-[13px] font-medium transition-colors group-hover:text-primary">{video.title}</span>
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1.5 text-[12px] ${statusColor}`}>
                        <StatusIcon className={`h-3.5 w-3.5 ${statusAnimate ? "animate-spin" : ""}`} />
                        {statusLabel}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[13px] text-muted-foreground">{formatDuration(video.duration)}</td>
                    <td className="px-4 py-3 text-[13px] text-muted-foreground">{video.channel || "-"}</td>
                    <td className="px-4 py-3 text-[13px] text-muted-foreground">{formatDate(dateStr)}</td>
                    <td className="px-4 py-3">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-7 w-7 rounded-md">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-40">
                          {video.status === "ready" && (
                            <DropdownMenuItem className="text-[13px]">
                              <Download className="mr-2 h-3.5 w-3.5" /> Download
                            </DropdownMenuItem>
                          )}
                          {video.youtube && (
                            <DropdownMenuItem className="text-[13px]">
                              <ExternalLink className="mr-2 h-3.5 w-3.5" /> YouTube
                            </DropdownMenuItem>
                          )}
                          {video.status === "failed" && (
                            <DropdownMenuItem className="text-[13px]">
                              <RefreshCw className="mr-2 h-3.5 w-3.5" /> Retry
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuSeparator />
                          <DropdownMenuItem className="text-[13px] text-destructive">
                            <Trash2 className="mr-2 h-3.5 w-3.5" /> Delete
                          </DropdownMenuItem>
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
          <Video className="h-10 w-10 text-muted-foreground/30" strokeWidth={1.5} />
          <p className="mt-4 text-[14px] font-medium">No videos found</p>
          <p className="mt-1 text-[13px] text-muted-foreground">
            {search ? "Try a different search" : "Create your first video"}
          </p>
        </div>
      )}
    </div>
  )
}
