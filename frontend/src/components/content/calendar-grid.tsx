"use client";

import { useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import {
  Plus,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Check,
  X,
  Loader2,
} from "lucide-react";

type ContentStatus = "pending" | "completed" | "skipped" | "generating";

interface ContentItem {
  id: string;
  topic: string;
  status: ContentStatus;
  time?: string;
  channel?: string;
}

interface DayColumn {
  date: Date;
  items: ContentItem[];
}

const STATUS_CONFIG: Record<
  ContentStatus,
  { color: string; label: string; icon: typeof Check }
> = {
  pending: { color: "bg-[#666]", label: "Pending", icon: Loader2 },
  completed: { color: "bg-[#10a37f]", label: "Done", icon: Check },
  skipped: { color: "bg-[#999]", label: "Skipped", icon: X },
  generating: {
    color: "bg-[#f59e0b] animate-pulse-dot",
    label: "Generating",
    icon: Sparkles,
  },
};

function getWeekDates(baseDate: Date): Date[] {
  const start = new Date(baseDate);
  start.setDate(start.getDate() - start.getDay());
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    return d;
  });
}

function formatDayLabel(date: Date): string {
  return date.toLocaleDateString("en-US", { weekday: "short" });
}

function formatDateLabel(date: Date): string {
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function isToday(date: Date): boolean {
  const now = new Date();
  return (
    date.getDate() === now.getDate() &&
    date.getMonth() === now.getMonth() &&
    date.getFullYear() === now.getFullYear()
  );
}

// Sample data for demonstration
const SAMPLE_ITEMS: Record<string, ContentItem[]> = {
  "0": [
    {
      id: "1",
      topic: "AI Video Editing in 2026",
      status: "completed",
      time: "9:00 AM",
      channel: "Tech Daily",
    },
  ],
  "1": [
    {
      id: "2",
      topic: "Top 5 Productivity Tools",
      status: "generating",
      time: "10:00 AM",
      channel: "Tech Daily",
    },
    {
      id: "3",
      topic: "React Server Components Deep Dive",
      status: "pending",
      time: "2:00 PM",
      channel: "Dev Tutorials",
    },
  ],
  "2": [
    {
      id: "4",
      topic: "Building with Next.js 16",
      status: "pending",
      time: "11:00 AM",
      channel: "Dev Tutorials",
    },
  ],
  "3": [
    {
      id: "5",
      topic: "The Future of Remote Work",
      status: "pending",
      time: "9:00 AM",
      channel: "Business Talks",
    },
    {
      id: "6",
      topic: "Cursor vs Claude Code",
      status: "skipped",
      time: "3:00 PM",
      channel: "Tech Daily",
    },
  ],
  "4": [
    {
      id: "7",
      topic: "TypeScript 6.0 New Features",
      status: "pending",
      time: "10:00 AM",
      channel: "Dev Tutorials",
    },
  ],
  "5": [],
  "6": [],
};

interface CalendarGridProps {
  onItemClick?: (item: ContentItem) => void;
  onAddClick?: (date: Date) => void;
}

export function CalendarGrid({ onItemClick, onAddClick }: CalendarGridProps) {
  const [weekOffset, setWeekOffset] = useState(0);

  const baseDate = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() + weekOffset * 7);
    return d;
  }, [weekOffset]);

  const weekDates = useMemo(() => getWeekDates(baseDate), [baseDate]);

  const columns: DayColumn[] = weekDates.map((date, i) => ({
    date,
    items: SAMPLE_ITEMS[String(i)] || [],
  }));

  const weekLabel = `${formatDateLabel(weekDates[0])} - ${formatDateLabel(weekDates[6])}`;

  return (
    <div className="space-y-4">
      {/* Week navigation */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setWeekOffset((w) => w - 1)}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/[0.08] text-[#999] transition-colors duration-150 hover:border-white/[0.15] hover:text-[#ececec]"
            aria-label="Previous week"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="text-sm font-medium text-[#ececec]">
            {weekLabel}
          </span>
          <button
            onClick={() => setWeekOffset((w) => w + 1)}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/[0.08] text-[#999] transition-colors duration-150 hover:border-white/[0.15] hover:text-[#ececec]"
            aria-label="Next week"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
        {weekOffset !== 0 && (
          <button
            onClick={() => setWeekOffset(0)}
            className="text-xs text-[#10a37f] transition-colors duration-150 hover:text-[#1a7f64]"
          >
            Today
          </button>
        )}
      </div>

      {/* Grid */}
      <div className="grid grid-cols-7 gap-2">
        {columns.map((col) => (
          <div
            key={col.date.toISOString()}
            className={cn(
              "min-h-[280px] rounded-xl border border-white/[0.08] bg-[#1a1a1a] p-3 transition-colors duration-150",
              isToday(col.date) && "border-[#10a37f]/30 bg-[#10a37f]/[0.03]"
            )}
          >
            {/* Day header */}
            <div className="mb-3 flex items-center justify-between">
              <div>
                <p
                  className={cn(
                    "text-[11px] font-medium uppercase tracking-wider",
                    isToday(col.date) ? "text-[#10a37f]" : "text-[#666]"
                  )}
                >
                  {formatDayLabel(col.date)}
                </p>
                <p
                  className={cn(
                    "text-lg font-semibold leading-tight",
                    isToday(col.date) ? "text-[#ececec]" : "text-[#999]"
                  )}
                >
                  {col.date.getDate()}
                </p>
              </div>
              <button
                onClick={() => onAddClick?.(col.date)}
                className="flex h-6 w-6 items-center justify-center rounded-md text-[#666] opacity-0 transition-all duration-150 hover:bg-white/[0.06] hover:text-[#999] group-hover:opacity-100 [div:hover>&]:opacity-100"
                aria-label={`Add content for ${formatDateLabel(col.date)}`}
              >
                <Plus className="h-3.5 w-3.5" />
              </button>
            </div>

            {/* Items */}
            <div className="space-y-2">
              {col.items.map((item) => {
                const config = STATUS_CONFIG[item.status];
                return (
                  <button
                    key={item.id}
                    onClick={() => onItemClick?.(item)}
                    className="group/item w-full rounded-lg border border-white/[0.04] bg-white/[0.02] p-2.5 text-left transition-all duration-150 hover:border-white/[0.08] hover:bg-white/[0.04]"
                  >
                    <div className="mb-1.5 flex items-start gap-2">
                      <span
                        className={cn(
                          "mt-1 inline-block h-1.5 w-1.5 shrink-0 rounded-full",
                          config.color
                        )}
                      />
                      <p className="text-xs font-medium leading-snug text-[#ececec] line-clamp-2">
                        {item.topic}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 pl-3.5">
                      {item.time && (
                        <span className="text-[10px] tabular-nums text-[#666]">
                          {item.time}
                        </span>
                      )}
                      {item.channel && (
                        <Badge className="h-4 px-1.5 text-[10px]">
                          {item.channel}
                        </Badge>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Empty state for day */}
            {col.items.length === 0 && (
              <button
                onClick={() => onAddClick?.(col.date)}
                className="flex w-full flex-col items-center justify-center rounded-lg border border-dashed border-white/[0.06] py-6 text-[#666] transition-colors duration-150 hover:border-white/[0.12] hover:text-[#999]"
              >
                <Plus className="mb-1 h-4 w-4" />
                <span className="text-[10px]">Add</span>
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 pt-1">
        {Object.entries(STATUS_CONFIG).map(([key, config]) => (
          <div key={key} className="flex items-center gap-1.5">
            <span
              className={cn(
                "inline-block h-1.5 w-1.5 rounded-full",
                config.color.split(" ")[0]
              )}
            />
            <span className="text-[11px] text-[#666]">{config.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
