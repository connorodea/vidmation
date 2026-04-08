"use client";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export type Platform = "youtube" | "tiktok" | "instagram" | "facebook" | "twitter";
export type ScheduleStatus = "scheduled" | "published" | "failed";

export interface ScheduledEvent {
  id: string;
  title: string;
  description?: string;
  platform: Platform;
  scheduledAt: string; // ISO date string
  status: ScheduleStatus;
  channel?: string;
  thumbnailUrl?: string;
}

/* ------------------------------------------------------------------ */
/*  Platform config                                                    */
/* ------------------------------------------------------------------ */

export const PLATFORM_CONFIG: Record<
  Platform,
  { label: string; color: string; bgClass: string; textClass: string }
> = {
  youtube: {
    label: "YouTube",
    color: "#FF0000",
    bgClass: "bg-[#FF0000]/15",
    textClass: "text-[#FF0000]",
  },
  tiktok: {
    label: "TikTok",
    color: "#000000",
    bgClass: "bg-white/10",
    textClass: "text-[#ececec]",
  },
  instagram: {
    label: "Instagram",
    color: "#E4405F",
    bgClass: "bg-[#E4405F]/15",
    textClass: "text-[#E4405F]",
  },
  facebook: {
    label: "Facebook",
    color: "#1877F2",
    bgClass: "bg-[#1877F2]/15",
    textClass: "text-[#1877F2]",
  },
  twitter: {
    label: "X",
    color: "#000000",
    bgClass: "bg-white/10",
    textClass: "text-[#ececec]",
  },
};

const STATUS_MAP: Record<
  ScheduleStatus,
  { label: string; variant: "default" | "success" | "error" }
> = {
  scheduled: { label: "Scheduled", variant: "default" },
  published: { label: "Published", variant: "success" },
  failed: { label: "Failed", variant: "error" },
};

/* ------------------------------------------------------------------ */
/*  Platform icon (inline SVG for pixel-perfect colors)                */
/* ------------------------------------------------------------------ */

export function PlatformIcon({
  platform,
  size = 14,
}: {
  platform: Platform;
  size?: number;
}) {
  const cfg = PLATFORM_CONFIG[platform];

  switch (platform) {
    case "youtube":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill={cfg.color}>
          <path d="M23.5 6.19a3.02 3.02 0 0 0-2.12-2.14C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.38.55A3.02 3.02 0 0 0 .5 6.19 31.6 31.6 0 0 0 0 12a31.6 31.6 0 0 0 .5 5.81 3.02 3.02 0 0 0 2.12 2.14c1.88.55 9.38.55 9.38.55s7.5 0 9.38-.55a3.02 3.02 0 0 0 2.12-2.14A31.6 31.6 0 0 0 24 12a31.6 31.6 0 0 0-.5-5.81zM9.75 15.02V8.98L15.5 12l-5.75 3.02z" />
        </svg>
      );
    case "tiktok":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="#ececec">
          <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.8.1V9.01a6.27 6.27 0 0 0-.8-.05 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.34-6.34V9.4a8.16 8.16 0 0 0 4.77 1.53V7.48a4.85 4.85 0 0 1-1.01-.79z" />
        </svg>
      );
    case "instagram":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill={cfg.color}>
          <path d="M12 2.16c3.2 0 3.58.01 4.85.07 1.17.05 1.97.25 2.43.41.61.24 1.05.52 1.51.98.46.46.74.9.98 1.51.17.46.36 1.26.41 2.43.06 1.27.07 1.65.07 4.85s-.01 3.58-.07 4.85c-.05 1.17-.25 1.97-.41 2.43a4.07 4.07 0 0 1-.98 1.51c-.46.46-.9.74-1.51.98-.46.17-1.26.36-2.43.41-1.27.06-1.65.07-4.85.07s-3.58-.01-4.85-.07c-1.17-.05-1.97-.25-2.43-.41a4.07 4.07 0 0 1-1.51-.98 4.07 4.07 0 0 1-.98-1.51c-.17-.46-.36-1.26-.41-2.43C2.17 15.58 2.16 15.2 2.16 12s.01-3.58.07-4.85c.05-1.17.25-1.97.41-2.43.24-.61.52-1.05.98-1.51a4.07 4.07 0 0 1 1.51-.98c.46-.17 1.26-.36 2.43-.41C8.42 2.17 8.8 2.16 12 2.16zM12 0C8.74 0 8.33.01 7.05.07 5.78.13 4.9.33 4.14.63a5.92 5.92 0 0 0-2.16 1.35A5.92 5.92 0 0 0 .63 4.14C.33 4.9.13 5.78.07 7.05.01 8.33 0 8.74 0 12s.01 3.67.07 4.95c.06 1.27.26 2.15.56 2.91.31.79.72 1.47 1.35 2.16a5.92 5.92 0 0 0 2.16 1.35c.76.3 1.64.5 2.91.56C8.33 23.99 8.74 24 12 24s3.67-.01 4.95-.07c1.27-.06 2.15-.26 2.91-.56a5.92 5.92 0 0 0 2.16-1.35 5.92 5.92 0 0 0 1.35-2.16c.3-.76.5-1.64.56-2.91.06-1.28.07-1.69.07-4.95s-.01-3.67-.07-4.95c-.06-1.27-.26-2.15-.56-2.91a5.92 5.92 0 0 0-1.35-2.16A5.92 5.92 0 0 0 19.86.63C19.1.33 18.22.13 16.95.07 15.67.01 15.26 0 12 0zm0 5.84a6.16 6.16 0 1 0 0 12.32 6.16 6.16 0 0 0 0-12.32zM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm7.85-10.4a1.44 1.44 0 1 0-2.88 0 1.44 1.44 0 0 0 2.88 0z" />
        </svg>
      );
    case "facebook":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill={cfg.color}>
          <path d="M24 12.07C24 5.41 18.63 0 12 0S0 5.41 0 12.07c0 6.02 4.39 11.01 10.13 11.93v-8.44H7.08v-3.49h3.04V9.41c0-3.02 1.79-4.7 4.53-4.7 1.31 0 2.68.24 2.68.24v2.97h-1.51c-1.49 0-1.95.93-1.95 1.89v2.26h3.33l-.53 3.49h-2.8v8.44C19.61 23.08 24 18.09 24 12.07z" />
        </svg>
      );
    case "twitter":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="#ececec">
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
        </svg>
      );
  }
}

/* ------------------------------------------------------------------ */
/*  Pill (compact view for calendar cells)                             */
/* ------------------------------------------------------------------ */

interface ScheduleEventPillProps {
  event: ScheduledEvent;
  onClick?: () => void;
}

export function ScheduleEventPill({ event, onClick }: ScheduleEventPillProps) {
  const cfg = PLATFORM_CONFIG[event.platform];
  const time = new Date(event.scheduledAt).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });

  return (
    <button
      onClick={onClick}
      className={cn(
        "group/pill flex w-full items-center gap-1.5 rounded-md px-2 py-1 text-left transition-all duration-150",
        "border border-transparent hover:border-white/[0.1]",
        cfg.bgClass
      )}
    >
      <PlatformIcon platform={event.platform} size={12} />
      <span className="truncate text-[11px] font-medium text-[#ececec]">
        {event.title}
      </span>
      <span className="ml-auto shrink-0 text-[10px] tabular-nums text-[#666]">
        {time}
      </span>
    </button>
  );
}

/* ------------------------------------------------------------------ */
/*  Expanded card (for detail view / modal)                            */
/* ------------------------------------------------------------------ */

interface ScheduleEventCardProps {
  event: ScheduledEvent;
  onClick?: () => void;
  className?: string;
}

export function ScheduleEventCard({ event, onClick, className }: ScheduleEventCardProps) {
  const cfg = PLATFORM_CONFIG[event.platform];
  const statusCfg = STATUS_MAP[event.status];

  const dateStr = new Date(event.scheduledAt).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
  const timeStr = new Date(event.scheduledAt).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });

  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full rounded-xl border border-white/[0.08] bg-[#1a1a1a] p-4 text-left transition-all duration-150 hover:border-white/[0.14]",
        className
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div
            className={cn(
              "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
              cfg.bgClass
            )}
          >
            <PlatformIcon platform={event.platform} size={16} />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-[#ececec]">
              {event.title}
            </p>
            <p className="mt-0.5 text-xs text-[#666]">
              {cfg.label}
              {event.channel && <> &middot; {event.channel}</>}
            </p>
          </div>
        </div>
        <Badge variant={statusCfg.variant} className="shrink-0">
          {statusCfg.label}
        </Badge>
      </div>
      <div className="mt-3 flex items-center gap-3 text-xs text-[#999]">
        <span className="tabular-nums">{dateStr}</span>
        <span className="text-[#666]">&middot;</span>
        <span className="tabular-nums">{timeStr}</span>
      </div>
      {event.description && (
        <p className="mt-2 text-xs leading-relaxed text-[#666] line-clamp-2">
          {event.description}
        </p>
      )}
    </button>
  );
}
