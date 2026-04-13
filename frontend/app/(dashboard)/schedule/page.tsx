"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Clock,
  Plus,
  Calendar,
  MoreHorizontal,
  Trash2,
  Pause,
  Play,
} from "lucide-react"
import { cn } from "@/lib/utils"

const mockScheduledVideos = [
  {
    id: "sch_1",
    video_id: "vid_120",
    video_title: "The Hidden System Banks Use to Control Money",
    publish_at: "2026-04-08T14:00:00Z",
    channel: "Wealth Wisdom",
    status: "scheduled",
  },
  {
    id: "sch_2",
    video_id: "vid_119",
    video_title: "Why 99% of People Fail at Investing",
    publish_at: "2026-04-10T14:00:00Z",
    channel: "Wealth Wisdom",
    status: "scheduled",
  },
  {
    id: "sch_3",
    video_id: "vid_118",
    video_title: "The Dark Truth About Credit Cards",
    publish_at: "2026-04-12T18:00:00Z",
    channel: "Tech Explained",
    status: "scheduled",
  },
]

const mockRecurringSchedules = [
  {
    id: "rec_1",
    channel_name: "Wealth Wisdom",
    cron_human: "Mon, Wed, Fri at 9:00 AM",
    topic_source: "content_calendar",
    is_active: true,
    next_run_at: "2026-04-08T09:00:00Z",
  },
  {
    id: "rec_2",
    channel_name: "Tech Explained",
    cron_human: "Tue, Thu at 6:00 PM",
    topic_source: "ai",
    is_active: true,
    next_run_at: "2026-04-08T18:00:00Z",
  },
]

const channels = [
  { id: "ch_1", name: "Wealth Wisdom" },
  { id: "ch_2", name: "Tech Explained" },
  { id: "ch_3", name: "Daily Finance" },
]

const videos = [
  { id: "vid_120", title: "The Hidden System Banks Use to Control Money" },
  { id: "vid_119", title: "Why 99% of People Fail at Investing" },
  { id: "vid_118", title: "The Dark Truth About Credit Cards" },
]

function formatDateTime(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  })
}

export default function SchedulePage() {
  const [isScheduleOpen, setIsScheduleOpen] = useState(false)
  const [isRecurringOpen, setIsRecurringOpen] = useState(false)
  const [selectedVideo, setSelectedVideo] = useState("")
  const [publishDate, setPublishDate] = useState("")
  const [publishTime, setPublishTime] = useState("")
  const [recurringChannel, setRecurringChannel] = useState("")
  const [recurringDays, setRecurringDays] = useState<string[]>([])
  const [recurringTime, setRecurringTime] = useState("")

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
        <div className="flex gap-2">
          <Dialog open={isScheduleOpen} onOpenChange={setIsScheduleOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" className="h-8 gap-1.5 rounded-lg border-foreground/10 px-3 text-[12px]">
                <Calendar className="h-3.5 w-3.5" />
                Schedule Video
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle className="text-[15px]">Schedule Video</DialogTitle>
                <DialogDescription className="text-[12px]">
                  Choose when to upload your video to YouTube.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-1.5">
                  <Label className="text-[12px]">Video</Label>
                  <Select value={selectedVideo} onValueChange={setSelectedVideo}>
                    <SelectTrigger className="h-9 rounded-lg text-[12px]">
                      <SelectValue placeholder="Select a video" />
                    </SelectTrigger>
                    <SelectContent>
                      {videos.map((video) => (
                        <SelectItem key={video.id} value={video.id} className="text-[12px]">
                          {video.title}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <Label className="text-[12px]">Date</Label>
                    <Input
                      type="date"
                      value={publishDate}
                      onChange={(e) => setPublishDate(e.target.value)}
                      className="h-9 rounded-lg text-[12px]"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-[12px]">Time</Label>
                    <Input
                      type="time"
                      value={publishTime}
                      onChange={(e) => setPublishTime(e.target.value)}
                      className="h-9 rounded-lg text-[12px]"
                    />
                  </div>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsScheduleOpen(false)} className="h-8 rounded-lg text-[12px]">
                  Cancel
                </Button>
                <Button
                  onClick={() => setIsScheduleOpen(false)}
                  disabled={!selectedVideo || !publishDate || !publishTime}
                  className="h-8 rounded-lg text-[12px]"
                >
                  Schedule
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          <Dialog open={isRecurringOpen} onOpenChange={setIsRecurringOpen}>
            <DialogTrigger asChild>
              <Button className="h-8 gap-1.5 rounded-lg bg-foreground px-3 text-[12px] text-background hover:bg-foreground/90">
                <Plus className="h-3.5 w-3.5" />
                Create Recurring
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle className="text-[15px]">Create Recurring Schedule</DialogTitle>
                <DialogDescription className="text-[12px]">
                  Automatically generate and publish videos.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-1.5">
                  <Label className="text-[12px]">Channel</Label>
                  <Select value={recurringChannel} onValueChange={setRecurringChannel}>
                    <SelectTrigger className="h-9 rounded-lg text-[12px]">
                      <SelectValue placeholder="Select channel" />
                    </SelectTrigger>
                    <SelectContent>
                      {channels.map((ch) => (
                        <SelectItem key={ch.id} value={ch.id} className="text-[12px]">
                          {ch.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-[12px]">Days</Label>
                  <div className="flex flex-wrap gap-1.5">
                    {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day) => (
                      <Button
                        key={day}
                        variant="outline"
                        size="sm"
                        className={cn(
                          "h-7 rounded-lg px-3 text-[11px]",
                          recurringDays.includes(day) && "bg-foreground text-background border-foreground"
                        )}
                        onClick={() => {
                          setRecurringDays((prev) =>
                            prev.includes(day)
                              ? prev.filter((d) => d !== day)
                              : [...prev, day]
                          )
                        }}
                      >
                        {day}
                      </Button>
                    ))}
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-[12px]">Time</Label>
                  <Input
                    type="time"
                    value={recurringTime}
                    onChange={(e) => setRecurringTime(e.target.value)}
                    className="h-9 rounded-lg text-[12px]"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsRecurringOpen(false)} className="h-8 rounded-lg text-[12px]">
                  Cancel
                </Button>
                <Button
                  onClick={() => setIsRecurringOpen(false)}
                  disabled={!recurringChannel || recurringDays.length === 0 || !recurringTime}
                  className="h-8 rounded-lg text-[12px]"
                >
                  Create
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-2">
        {/* Scheduled Videos */}
        <div>
          <h2 className="mb-4 text-[13px] font-medium text-foreground/50 uppercase tracking-wider">
            Scheduled Uploads
          </h2>
          <div className="rounded-xl border border-foreground/10 overflow-hidden">
            {mockScheduledVideos.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <Calendar className="h-8 w-8 text-foreground/20 mb-3" />
                <p className="text-[13px] text-foreground/50">No scheduled uploads</p>
              </div>
            ) : (
              <div className="divide-y divide-foreground/10">
                {mockScheduledVideos.map((schedule) => (
                  <div
                    key={schedule.id}
                    className="flex items-center justify-between p-4 hover:bg-foreground/[0.02] transition-colors"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-[13px] font-medium text-foreground truncate">
                        {schedule.video_title}
                      </p>
                      <div className="mt-1 flex items-center gap-3 text-[11px] text-foreground/50">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatDateTime(schedule.publish_at)}
                        </span>
                        <span>{schedule.channel}</span>
                      </div>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-7 w-7 rounded-lg">
                          <MoreHorizontal className="h-3.5 w-3.5" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem className="text-[12px]">
                          <Calendar className="mr-2 h-3.5 w-3.5" />
                          Reschedule
                        </DropdownMenuItem>
                        <DropdownMenuItem className="text-[12px] text-destructive">
                          <Trash2 className="mr-2 h-3.5 w-3.5" />
                          Cancel
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Recurring Schedules */}
        <div>
          <h2 className="mb-4 text-[13px] font-medium text-foreground/50 uppercase tracking-wider">
            Recurring Schedules
          </h2>
          <div className="rounded-xl border border-foreground/10 overflow-hidden">
            {mockRecurringSchedules.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <Clock className="h-8 w-8 text-foreground/20 mb-3" />
                <p className="text-[13px] text-foreground/50">No recurring schedules</p>
              </div>
            ) : (
              <div className="divide-y divide-foreground/10">
                {mockRecurringSchedules.map((schedule) => (
                  <div key={schedule.id} className="p-4 hover:bg-foreground/[0.02] transition-colors">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="text-[13px] font-medium text-foreground">
                            {schedule.channel_name}
                          </p>
                          <span className={cn(
                            "rounded-md px-1.5 py-0.5 text-[10px] font-medium",
                            schedule.topic_source === "ai" 
                              ? "bg-foreground text-background" 
                              : "bg-foreground/5 text-foreground/60"
                          )}>
                            {schedule.topic_source === "ai" ? "AI" : "Calendar"}
                          </span>
                        </div>
                        <p className="mt-0.5 text-[11px] text-foreground/50">
                          {schedule.cron_human}
                        </p>
                      </div>
                      <Switch checked={schedule.is_active} />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-foreground/40">
                        Next: {formatDateTime(schedule.next_run_at)}
                      </span>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm" className="h-6 w-6 rounded-lg p-0">
                            <MoreHorizontal className="h-3 w-3" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem className="text-[12px]">
                            <Play className="mr-2 h-3.5 w-3.5" />
                            Run Now
                          </DropdownMenuItem>
                          <DropdownMenuItem className="text-[12px]">
                            <Pause className="mr-2 h-3.5 w-3.5" />
                            Pause
                          </DropdownMenuItem>
                          <DropdownMenuItem className="text-[12px] text-destructive">
                            <Trash2 className="mr-2 h-3.5 w-3.5" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
