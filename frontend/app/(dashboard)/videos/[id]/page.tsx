"use client"

import { useState } from "react"
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
} from "lucide-react"
import { cn } from "@/lib/utils"

const mockVideo = {
  id: "vid_120",
  title: "The Hidden System Banks Use to Control Money",
  description: "Discover the psychological and financial systems that banks use to maintain control over money supply and how you can protect yourself.",
  tags: ["finance", "banking", "money", "wealth"],
  status: "ready",
  format: "landscape",
  style: "Oil Painting",
  voice: "Onyx",
  duration_seconds: 504,
  created_at: "2026-04-07T08:30:00Z",
  channel: { name: "Wealth Wisdom" },
  script_json: {
    hook: "What if I told you that the money in your bank account isn't really yours?",
    sections: [
      {
        section_number: 1,
        heading: "The Fractional Reserve System",
        narration: "Every time you deposit money into your bank account, something interesting happens. The bank doesn't just keep your money in a vault.",
        visual_query: "oil painting of a Renaissance-era bank vault with gold coins",
      },
      {
        section_number: 2,
        heading: "How Money Is Created",
        narration: "Here's where it gets mind-bending. When banks lend out your money, they're actually creating new money.",
        visual_query: "oil painting of money multiplying through a complex system",
      },
      {
        section_number: 3,
        heading: "The Interest Game",
        narration: "Now, here's the catch. Banks charge interest on the money they lend out, but pay you much less interest on your deposits.",
        visual_query: "oil painting of a balance scale with gold on one side",
      },
    ],
    outro: "Now you understand how banks really work.",
  },
  jobs: [{ id: "job_1", status: "completed", progress_pct: 100 }],
  cost_breakdown: { script: 0.05, voiceover: 0.18, images: 0.42, whisper: 0.02, total: 0.67 },
}

const generatingVideo = {
  ...mockVideo,
  id: "vid_new",
  status: "generating",
  duration_seconds: 0,
  jobs: [{
    id: "job_new",
    status: "running",
    progress_pct: 45,
    stages: [
      { name: "script", status: "completed" },
      { name: "voiceover", status: "completed" },
      { name: "images", status: "running", progress: 12, total: 40 },
      { name: "assembly", status: "pending" },
      { name: "captions", status: "pending" },
      { name: "export", status: "pending" },
    ],
    estimated_seconds_remaining: 120,
  }],
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
  
  const video = params.id === "vid_new" ? generatingVideo : mockVideo
  const isGenerating = video.status === "generating"
  const currentJob = video.jobs[0]

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
                video.status === "generating" && "bg-foreground/10 text-foreground",
                video.status === "failed" && "bg-destructive/10 text-destructive"
              )}>
                {video.status === "ready" ? "Ready" : video.status === "generating" ? "Generating" : "Failed"}
              </span>
            </div>
            <p className="mt-1 text-[12px] text-foreground/50">
              {video.channel.name} · {new Date(video.created_at).toLocaleDateString()}
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
      {isGenerating && "stages" in currentJob && (
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
            <p className="mt-2 text-[11px] text-foreground/40">
              ~{Math.ceil(currentJob.estimated_seconds_remaining / 60)} min remaining
            </p>
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
              <div>
                <h3 className="mb-2 text-[12px] font-medium text-foreground/50 uppercase tracking-wider">Description</h3>
                <p className="text-[13px] leading-relaxed text-foreground/70">{video.description}</p>
              </div>

              {/* Tags */}
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
            </div>
          )}

          {activeTab === "script" && (
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

          {activeTab === "assets" && (
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
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Details */}
          <div>
            <h2 className="mb-3 text-[12px] font-medium text-foreground/50 uppercase tracking-wider">Details</h2>
            <div className="rounded-xl border border-foreground/10 divide-y divide-foreground/10">
              {[
                { label: "Duration", value: formatDuration(video.duration_seconds) },
                { label: "Style", value: video.style },
                { label: "Voice", value: video.voice },
                { label: "Format", value: video.format },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between p-3">
                  <span className="text-[11px] text-foreground/50">{item.label}</span>
                  <span className="text-[11px] font-medium text-foreground capitalize">{item.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Cost */}
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
        </div>
      </div>
    </div>
  )
}
