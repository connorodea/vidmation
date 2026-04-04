"use client";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";
import { Clock, Play, Monitor, Smartphone } from "lucide-react";

type ScheduleStatus = "scheduled" | "publishing" | "published" | "failed";
type Platform = "youtube" | "tiktok" | "instagram";

interface ScheduledItem {
  id: string;
  title: string;
  scheduledAt: string;
  platform: Platform;
  status: ScheduleStatus;
  channel?: string;
}

const STATUS_CONFIG: Record<
  ScheduleStatus,
  { label: string; variant: "default" | "success" | "warning" | "error" }
> = {
  scheduled: { label: "Scheduled", variant: "default" },
  publishing: { label: "Publishing", variant: "warning" },
  published: { label: "Published", variant: "success" },
  failed: { label: "Failed", variant: "error" },
};

const PLATFORM_CONFIG: Record<
  Platform,
  { label: string; icon: typeof Play }
> = {
  youtube: { label: "YouTube", icon: Play },
  tiktok: { label: "TikTok", icon: Smartphone },
  instagram: { label: "Instagram", icon: Monitor },
};

// Realistic sample data
const SAMPLE_ITEMS: ScheduledItem[] = [
  {
    id: "1",
    title: "AI Video Editing in 2026: Complete Guide",
    scheduledAt: "2026-04-05T09:00:00Z",
    platform: "youtube",
    status: "scheduled",
    channel: "Tech Daily",
  },
  {
    id: "2",
    title: "Top 5 Productivity Tools for Developers",
    scheduledAt: "2026-04-05T14:00:00Z",
    platform: "youtube",
    status: "scheduled",
    channel: "Tech Daily",
  },
  {
    id: "3",
    title: "React Server Components Tutorial",
    scheduledAt: "2026-04-06T10:00:00Z",
    platform: "youtube",
    status: "scheduled",
    channel: "Dev Tutorials",
  },
  {
    id: "4",
    title: "Quick Tips: TypeScript 6 Features",
    scheduledAt: "2026-04-06T16:00:00Z",
    platform: "tiktok",
    status: "publishing",
    channel: "Dev Tutorials",
  },
  {
    id: "5",
    title: "The Future of Remote Work",
    scheduledAt: "2026-04-04T08:00:00Z",
    platform: "youtube",
    status: "published",
    channel: "Business Talks",
  },
  {
    id: "6",
    title: "Building with Next.js 16",
    scheduledAt: "2026-04-03T12:00:00Z",
    platform: "youtube",
    status: "failed",
    channel: "Dev Tutorials",
  },
];

interface UpcomingListProps {
  items?: ScheduledItem[];
}

export function UpcomingList({ items = SAMPLE_ITEMS }: UpcomingListProps) {
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-white/[0.08] py-16">
        <Clock className="mb-3 h-8 w-8 text-[#666]" />
        <p className="text-sm text-[#999]">No scheduled videos</p>
        <p className="mt-1 text-xs text-[#666]">
          Schedule a video to see it here
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {items.map((item) => {
        const statusConfig = STATUS_CONFIG[item.status];
        const platformConfig = PLATFORM_CONFIG[item.platform];
        const PlatformIcon = platformConfig.icon;

        return (
          <div
            key={item.id}
            className="group flex items-center gap-4 rounded-xl border border-white/[0.08] bg-[#1a1a1a] px-5 py-4 transition-colors duration-150 hover:border-white/[0.12]"
          >
            {/* Date/time */}
            <div className="w-28 shrink-0">
              <p className="text-xs font-medium tabular-nums text-[#ececec]">
                {formatDate(item.scheduledAt)}
              </p>
            </div>

            {/* Platform icon */}
            <div
              className={cn(
                "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
                "bg-white/[0.06] text-[#999]"
              )}
              aria-label={platformConfig.label}
            >
              <PlatformIcon className="h-4 w-4" />
            </div>

            {/* Title and channel */}
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm text-[#ececec]">{item.title}</p>
              {item.channel && (
                <p className="mt-0.5 text-xs text-[#666]">{item.channel}</p>
              )}
            </div>

            {/* Status */}
            <Badge variant={statusConfig.variant} className="shrink-0">
              {statusConfig.label}
            </Badge>
          </div>
        );
      })}
    </div>
  );
}

export type { ScheduledItem, ScheduleStatus, Platform };
