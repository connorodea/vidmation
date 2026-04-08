"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import {
  PLATFORM_CONFIG,
  PlatformIcon,
  type Platform,
} from "@/components/schedule/schedule-event";
import { CalendarClock, Check, Video } from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Mock videos                                                        */
/* ------------------------------------------------------------------ */

interface MockVideo {
  id: string;
  title: string;
  description: string;
  duration: string;
}

const MOCK_VIDEOS: MockVideo[] = [
  {
    id: "v1",
    title: "AI Video Editing in 2026: Complete Guide",
    description:
      "A comprehensive walkthrough of the latest AI-powered video editing tools and techniques.",
    duration: "12:34",
  },
  {
    id: "v2",
    title: "Top 5 Productivity Tools for Developers",
    description:
      "Discover the five must-have tools that will supercharge your dev workflow in 2026.",
    duration: "8:21",
  },
  {
    id: "v3",
    title: "React Server Components Tutorial",
    description:
      "Learn React Server Components from scratch with practical examples.",
    duration: "15:07",
  },
  {
    id: "v4",
    title: "The Future of Remote Work",
    description:
      "An in-depth look at how remote work is evolving with AI assistants and VR offices.",
    duration: "10:45",
  },
  {
    id: "v5",
    title: "Building a SaaS in One Weekend",
    description:
      "Watch us build and launch a fully functional SaaS product in 48 hours.",
    duration: "18:22",
  },
];

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

const ALL_PLATFORMS: Platform[] = [
  "youtube",
  "tiktok",
  "instagram",
  "facebook",
  "twitter",
];

interface NewScheduleModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Pre-fill the date when clicking on a calendar day. */
  defaultDate?: Date;
}

export function NewScheduleModal({
  open,
  onOpenChange,
  defaultDate,
}: NewScheduleModalProps) {
  const [selectedVideo, setSelectedVideo] = useState<string>("");
  const [selectedPlatforms, setSelectedPlatforms] = useState<Set<Platform>>(
    new Set()
  );
  const [date, setDate] = useState(
    defaultDate
      ? formatDateInput(defaultDate)
      : formatDateInput(new Date())
  );
  const [time, setTime] = useState("09:00");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  // Sync title/description when video is selected
  function handleVideoSelect(videoId: string) {
    setSelectedVideo(videoId);
    const video = MOCK_VIDEOS.find((v) => v.id === videoId);
    if (video) {
      setTitle(video.title);
      setDescription(video.description);
    }
  }

  function togglePlatform(p: Platform) {
    setSelectedPlatforms((prev) => {
      const next = new Set(prev);
      if (next.has(p)) {
        next.delete(p);
      } else {
        next.add(p);
      }
      return next;
    });
  }

  function handleSubmit() {
    // In a real app, this would POST to the API
    // For now, close the modal
    onOpenChange(false);
    // Reset state
    setSelectedVideo("");
    setSelectedPlatforms(new Set());
    setTitle("");
    setDescription("");
  }

  const canSubmit =
    selectedVideo !== "" && selectedPlatforms.size > 0 && title.trim() !== "";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CalendarClock className="h-5 w-5 text-[#10a37f]" />
            Schedule Video
          </DialogTitle>
          <DialogDescription>
            Choose a video and platforms, then pick a date and time.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-2">
          {/* Video selection */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-[#999]">
              Select Video
            </label>
            <div className="max-h-[160px] space-y-1 overflow-y-auto rounded-xl border border-white/[0.06] bg-[#111] p-2">
              {MOCK_VIDEOS.map((video) => (
                <button
                  key={video.id}
                  onClick={() => handleVideoSelect(video.id)}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors duration-100",
                    selectedVideo === video.id
                      ? "bg-[#10a37f]/10 border border-[#10a37f]/30"
                      : "border border-transparent hover:bg-white/[0.04]"
                  )}
                >
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/[0.06]">
                    <Video className="h-4 w-4 text-[#666]" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-medium text-[#ececec]">
                      {video.title}
                    </p>
                    <p className="text-[10px] text-[#666]">
                      {video.duration}
                    </p>
                  </div>
                  {selectedVideo === video.id && (
                    <Check className="h-4 w-4 shrink-0 text-[#10a37f]" />
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Platform selection */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-[#999]">
              Platforms
            </label>
            <div className="flex flex-wrap gap-2">
              {ALL_PLATFORMS.map((p) => {
                const cfg = PLATFORM_CONFIG[p];
                const active = selectedPlatforms.has(p);
                return (
                  <button
                    key={p}
                    onClick={() => togglePlatform(p)}
                    className={cn(
                      "flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-medium transition-all duration-150",
                      active
                        ? "border-[#10a37f]/40 bg-[#10a37f]/10 text-[#ececec]"
                        : "border-white/[0.08] bg-transparent text-[#999] hover:border-white/[0.15]"
                    )}
                  >
                    <PlatformIcon platform={p} size={14} />
                    <span>{cfg.label}</span>
                    {active && <Check className="ml-0.5 h-3 w-3 text-[#10a37f]" />}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Date and Time */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <label className="text-xs font-medium text-[#999]">Date</label>
              <Input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="[color-scheme:dark]"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-medium text-[#999]">Time</label>
              <Input
                type="time"
                value={time}
                onChange={(e) => setTime(e.target.value)}
                className="[color-scheme:dark]"
              />
            </div>
          </div>

          {/* Title */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-[#999]">Title</label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Video title..."
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-[#999]">
              Description
            </label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Video description..."
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="secondary"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit}>
            <CalendarClock className="h-4 w-4" />
            Schedule
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ------------------------------------------------------------------ */
/*  Util                                                               */
/* ------------------------------------------------------------------ */

function formatDateInput(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}
