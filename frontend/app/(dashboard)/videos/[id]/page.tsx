"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { useParams } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import {
  ArrowLeft,
  Download,
  Play,
  Clock,
  DollarSign,
  CheckCircle2,
  Loader2,
  Upload,
  RefreshCw,
  Copy,
  Share2,
  AlertCircle,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { apiFetch } from "@/lib/api"

interface VideoJob {
  id: string
  status: string
  progress_pct: number
  stages?: {
    name: string
    status: string
    progress?: number
    total?: number
  }[]
  estimated_seconds_remaining?: number
}

interface Video {
  id: string
  title: string
  description: string
  tags: string[]
  status: string
  format: string
  style: string
  voice: string
  duration_seconds: number
  created_at: string
  channel: { name: string }
  script_json: {
    hook: string
    sections: {
      section_number: number
      heading: string
      narration: string
      visual_query: string
    }[]
    outro: string
  }
  jobs: VideoJob[]
  cost_breakdown: {
    script: number
    voiceover: number
    images: number
    whisper: number
    total: number
  }
}

function formatDuration(seconds: number): string {
  if (!seconds) return "-"
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, "0")}`
}

export default function VideoDetailPage() {
  const params = useParams()
  const [activeTab, setActiveTab] = useState<"overview" | "script" | "assets">("overview")
  const [video, setVideo] = useState<Video | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!params.id) return

    let cancelled = false
    let pollTimer: ReturnType<typeof setTimeout> | null = null

    async function fetchVideo() {
      try {
        const data = await apiFetch<Video>(`/videos/${params.id}`)
        if (cancelled) return
        setVideo(data)
        setError(null)

        // If video has active jobs, fetch job details and poll
        const hasActiveJobs = data.status === "generating" || data.status === "processing"
        if (hasActiveJobs) {
          try {
            const jobs = await apiFetch<VideoJob[]>(`/jobs?video_id=${params.id}`)
            if (cancelled) return
            setVideo((prev) => prev ? { ...prev, jobs } : prev)
          } catch {
            // Jobs fetch is optional; keep the video data we have
          }
          // Poll every 5 seconds while generating
          pollTimer = setTimeout(fetchVideo, 5000)
        }
      } catch (err: unknown) {
        if (cancelled) return
        const message = err instanceof Error ? err.message : "Failed to load video"
        setError(message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchVideo()

    return () => {
      cancelled = true
      if (pollTimer) clearTimeout(pollTimer)
    }
  }, [params.id])

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center p-8">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-6 w-6 animate-spin text-foreground/40" />
          <p className="text-[13px] text-foreground/50">Loading video...</p>
        </div>
      </div>
    )
  }

  if (error || !video) {
    return (
      <div className="p-8 lg:p-12">
        <Button
          variant="ghost"
          size="sm"
          className="mb-4 h-7 gap-1.5 rounded-lg px-2 text-[11px] text-foreground/50 hover:text-foreground"
          asChild
        >
          <Link href="/videos">
            <ArrowLeft className="h-3.5 w-3.5" />
            Back
          </Link>
        </Button>
        <div className="flex flex-col items-center justify-center py-20">
          <AlertCircle className="h-8 w-8 text-foreground/20 mb-3" />
          <h2 className="text-[15px] font-medium text-foreground">Video not found</h2>
          <p className="mt-1 text-[13px] text-foreground/50">
            {error || "The requested video could not be found."}
          </p>
          <Button
            variant="outline"
            className="mt-6 h-8 rounded-lg border-foreground/10 px-4 text-[12px]"
            asChild
          >
            <Link href="/videos">Back to Videos</Link>
          </Button>
        </div>
      </div>
    )
  }

  const isGenerating = video.status === "generating" || video.status === "processing"
  const currentJob = video.jobs?.[0]

  return (
    <div className="p-8 lg:p-12">
      {/* Header */}
      <div className="mb-8">
        <Button
          variant="ghost"
          size="sm"
          className="mb-4 h-7 gap-1.5 rounded-lg px-2 text-[11px] text-foreground/50 hover:text-foreground"
          asChild
        >
          <Link href="/videos">
            <ArrowLeft className="h-3.5 w-3.5" />
            Back
          </Link>
        </Button>

        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h1 className="text-[24px] font-semibold tracking-tight text-foreground">
                {video.title}
              </h1>
              <span className={cn(
                "rounded-md px-2 py-0.5 text-[10px] font-medium",
                video.status === "ready" && "bg-foreground text-background",
                (video.status === "generating" || video.status === "processing") && "bg-foreground/10 text-foreground",
                video.status === "failed" && "bg-destructive/10 text-destructive"
              )}>
                {video.status === "ready" ? "Ready" : (video.status === "generating" || video.status === "processing") ? "Generating" : video.status === "failed" ? "Failed" : video.status}
              </span>
            </div>
            <p className="mt-1 text-[12px] text-foreground/50">
              {video.channel?.name} · {new Date(video.created_at).toLocaleDateString()}
            </p>
          </div>

          <div className="flex gap-2">
            {video.status === "ready" && (
              <>
                <Button variant="outline" className="h-8 gap-1.5 rounded-lg border-foreground/10 px-3 text-[11px]">
                  <Share2 className="h-3.5 w-3.5" />
                  Share
                </Button>
                <Button variant="outline" className="h-8 gap-1.5 rounded-lg border-foreground/10 px-3 text-[11px]">
                  <Download className="h-3.5 w-3.5" />
                  Download
                </Button>
                <Button className="h-8 gap-1.5 rounded-lg bg-foreground px-3 text-[11px] text-background hover:bg-foreground/90">
                  <Upload className="h-3.5 w-3.5" />
                  Upload to YouTube
                </Button>
              </>
            )}
            {video.status === "failed" && (
              <Button className="h-8 gap-1.5 rounded-lg bg-foreground px-3 text-[11px] text-background hover:bg-foreground/90">
                <RefreshCw className="h-3.5 w-3.5" />
                Retry
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Generating Progress */}
      {isGenerating && currentJob && "stages" in currentJob && currentJob.stages && (
        <div className="mb-8 rounded-xl border border-foreground/10 p-6">
          <div className="mb-4 flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-foreground" />
            <h2 className="text-[14px] font-medium text-foreground">Generating Video</h2>
          </div>
          <div className="mb-4">
            <div className="mb-2 flex items-center justify-between text-[12px]">
              <span className="text-foreground/50">Progress</span>
              <span className="font-medium text-foreground">{currentJob.progress_pct}%</span>
            </div>
            <Progress value={currentJob.progress_pct} className="h-1" />
            {currentJob.estimated_seconds_remaining != null && (
              <p className="mt-2 text-[11px] text-foreground/40">
                ~{Math.ceil(currentJob.estimated_seconds_remaining / 60)} min remaining
              </p>
            )}
          </div>

          <div className="flex gap-2">
            {currentJob.stages.map((stage) => (
              <div
                key={stage.name}
                className={cn(
                  "flex-1 rounded-lg p-3 text-center",
                  stage.status === "completed" && "bg-foreground text-background",
                  stage.status === "running" && "bg-foreground/10 text-foreground",
                  stage.status === "pending" && "bg-foreground/[0.03] text-foreground/40"
                )}
              >
                <div className="flex items-center justify-center gap-1.5">
                  {stage.status === "completed" && <CheckCircle2 className="h-3 w-3" />}
                  {stage.status === "running" && <Loader2 className="h-3 w-3 animate-spin" />}
                  <span className="text-[10px] font-medium capitalize">{stage.name}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2">
          {/* Tabs */}
          <div className="mb-6 flex gap-1 border-b border-foreground/10">
            {(["overview", "script", "assets"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={cn(
                  "px-4 py-2 text-[12px] font-medium capitalize transition-colors border-b-2 -mb-px",
                  activeTab === tab
                    ? "border-foreground text-foreground"
                    : "border-transparent text-foreground/50 hover:text-foreground"
                )}
              >
                {tab}
              </button>
            ))}
          </div>

          {activeTab === "overview" && (
            <div className="space-y-6">
              {/* Video Preview */}
              <div className="aspect-video overflow-hidden rounded-xl bg-foreground">
                {video.status === "ready" ? (
                  <div className="relative flex h-full items-center justify-center">
                    <Button size="lg" className="h-12 gap-2 rounded-full bg-background/20 px-6 text-[12px] text-background backdrop-blur-sm hover:bg-background/30">
                      <Play className="h-5 w-5" />
                      Play
                    </Button>
                    <div className="absolute bottom-3 right-3 rounded-md bg-black/60 px-2 py-0.5 text-[10px] text-white">
                      {formatDuration(video.duration_seconds)}
                    </div>
                  </div>
                ) : (
                  <div className="flex h-full items-center justify-center">
                    <Loader2 className="h-8 w-8 animate-spin text-background/30" />
                  </div>
                )}
              </div>

              {/* Description */}
              {video.description && (
                <div>
                  <h3 className="mb-2 text-[12px] font-medium text-foreground/50 uppercase tracking-wider">Description</h3>
                  <p className="text-[13px] leading-relaxed text-foreground/70">{video.description}</p>
                </div>
              )}

              {/* Tags */}
              {video.tags && video.tags.length > 0 && (
                <div>
                  <h3 className="mb-2 text-[12px] font-medium text-foreground/50 uppercase tracking-wider">Tags</h3>
                  <div className="flex flex-wrap gap-1.5">
                    {video.tags.map((tag) => (
                      <span key={tag} className="rounded-md bg-foreground/5 px-2 py-0.5 text-[11px] text-foreground/70">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === "script" && video.script_json && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-[14px] font-medium text-foreground">Script</h2>
                <Button variant="ghost" size="sm" className="h-7 gap-1.5 rounded-lg text-[11px]">
                  <Copy className="h-3.5 w-3.5" />
                  Copy
                </Button>
              </div>

              <div className="rounded-xl border border-foreground/10 divide-y divide-foreground/10">
                <div className="p-4">
                  <p className="text-[10px] font-medium text-foreground/40 uppercase tracking-wider mb-1">Hook</p>
                  <p className="text-[13px] text-foreground">{video.script_json.hook}</p>
                </div>

                {video.script_json.sections.map((section) => (
                  <div key={section.section_number} className="p-4">
                    <p className="text-[12px] font-medium text-foreground mb-1">{section.heading}</p>
                    <p className="text-[12px] text-foreground/60 leading-relaxed mb-3">{section.narration}</p>
                    <div className="rounded-lg bg-foreground/[0.03] p-3">
                      <p className="text-[10px] font-medium text-foreground/40 uppercase tracking-wider">Visual</p>
                      <p className="mt-0.5 text-[11px] italic text-foreground/50">{section.visual_query}</p>
                    </div>
                  </div>
                ))}

                <div className="p-4">
                  <p className="text-[10px] font-medium text-foreground/40 uppercase tracking-wider mb-1">Outro</p>
                  <p className="text-[13px] text-foreground">{video.script_json.outro}</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "script" && !video.script_json && (
            <div className="flex flex-col items-center justify-center py-16">
              <p className="text-[13px] text-foreground/50">Script not available yet.</p>
            </div>
          )}

          {activeTab === "assets" && video.script_json && (
            <div>
              <h2 className="mb-4 text-[14px] font-medium text-foreground">Generated Assets</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {video.script_json.sections.map((section, i) => (
                  <div key={i} className="overflow-hidden rounded-xl border border-foreground/10">
                    <div className="aspect-video bg-foreground/5" />
                    <div className="p-3">
                      <p className="text-[12px] font-medium text-foreground">{section.heading}</p>
                      <p className="mt-0.5 text-[10px] text-foreground/50">Section {section.section_number}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === "assets" && !video.script_json && (
            <div className="flex flex-col items-center justify-center py-16">
              <p className="text-[13px] text-foreground/50">Assets not available yet.</p>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Details */}
          <div>
            <h2 className="mb-3 text-[12px] font-medium text-foreground/50 uppercase tracking-wider">Details</h2>
            <div className="rounded-xl border border-foreground/10 divide-y divide-foreground/10">
              {[
                { label: "Duration", value: formatDuration(video.duration_seconds) },
                { label: "Style", value: video.style || "-" },
                { label: "Voice", value: video.voice || "-" },
                { label: "Format", value: video.format || "-" },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between p-3">
                  <span className="text-[11px] text-foreground/50">{item.label}</span>
                  <span className="text-[11px] font-medium text-foreground capitalize">{item.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Cost */}
          {video.cost_breakdown && (
            <div>
              <h2 className="mb-3 text-[12px] font-medium text-foreground/50 uppercase tracking-wider flex items-center gap-1.5">
                <DollarSign className="h-3.5 w-3.5" />
                Cost Breakdown
              </h2>
              <div className="rounded-xl border border-foreground/10 divide-y divide-foreground/10">
                {[
                  { label: "Script", value: video.cost_breakdown.script },
                  { label: "Voiceover", value: video.cost_breakdown.voiceover },
                  { label: "Images", value: video.cost_breakdown.images },
                  { label: "Whisper", value: video.cost_breakdown.whisper },
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between p-3">
                    <span className="text-[11px] text-foreground/50">{item.label}</span>
                    <span className="text-[11px] text-foreground">${item.value.toFixed(2)}</span>
                  </div>
                ))}
                <div className="flex items-center justify-between p-3 bg-foreground/[0.02]">
                  <span className="text-[11px] font-medium text-foreground">Total</span>
                  <span className="text-[13px] font-semibold text-foreground">${video.cost_breakdown.total.toFixed(2)}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
