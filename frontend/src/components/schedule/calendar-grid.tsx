"use client";

import { useMemo } from "react";
import { cn } from "@/lib/utils";
import { Plus } from "lucide-react";
import {
  ScheduleEventPill,
  type ScheduledEvent,
} from "@/components/schedule/schedule-event";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function isSameDay(a: Date, b: Date) {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function isToday(d: Date) {
  return isSameDay(d, new Date());
}

function isCurrentMonth(d: Date, month: number, year: number) {
  return d.getMonth() === month && d.getFullYear() === year;
}

/** Return the grid of dates for a given month (Sun-start, 6 rows max). */
function getMonthGrid(year: number, month: number): Date[][] {
  const firstDay = new Date(year, month, 1);
  const startOffset = firstDay.getDay(); // 0=Sun
  const start = new Date(year, month, 1 - startOffset);

  const weeks: Date[][] = [];
  const cursor = new Date(start);
  for (let w = 0; w < 6; w++) {
    const week: Date[] = [];
    for (let d = 0; d < 7; d++) {
      week.push(new Date(cursor));
      cursor.setDate(cursor.getDate() + 1);
    }
    // Skip the 6th row if it's entirely the next month
    if (w === 5 && week[0].getMonth() !== month) break;
    weeks.push(week);
  }
  return weeks;
}

/** Return the grid of dates for a week that contains `anchorDate`. */
function getWeekGrid(anchorDate: Date): Date[][] {
  const start = new Date(anchorDate);
  start.setDate(start.getDate() - start.getDay());
  const week: Date[] = [];
  for (let d = 0; d < 7; d++) {
    const day = new Date(start);
    day.setDate(day.getDate() + d);
    week.push(day);
  }
  return [week];
}

function dateKey(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export type CalendarView = "month" | "week";

interface CalendarGridProps {
  year: number;
  month: number; // 0-indexed
  view: CalendarView;
  events: ScheduledEvent[];
  visiblePlatforms: Set<string>;
  onEventClick?: (event: ScheduledEvent) => void;
  onDayClick?: (date: Date) => void;
  selectedDate?: Date | null;
}

export function CalendarGrid({
  year,
  month,
  view,
  events,
  visiblePlatforms,
  onEventClick,
  onDayClick,
  selectedDate,
}: CalendarGridProps) {
  // Bucket events by date key
  const eventsByDate = useMemo(() => {
    const map = new Map<string, ScheduledEvent[]>();
    for (const ev of events) {
      if (!visiblePlatforms.has(ev.platform)) continue;
      const d = new Date(ev.scheduledAt);
      const key = dateKey(d);
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(ev);
    }
    // Sort each bucket by time
    for (const [, bucket] of map) {
      bucket.sort(
        (a, b) =>
          new Date(a.scheduledAt).getTime() - new Date(b.scheduledAt).getTime()
      );
    }
    return map;
  }, [events, visiblePlatforms]);

  const weeks = useMemo(() => {
    if (view === "week") {
      // Use the selectedDate or the 15th of the month as anchor
      const anchor = selectedDate ?? new Date(year, month, 15);
      return getWeekGrid(anchor);
    }
    return getMonthGrid(year, month);
  }, [year, month, view, selectedDate]);

  return (
    <div className="space-y-0">
      {/* Day-of-week headers */}
      <div className="grid grid-cols-7 gap-px border-b border-white/[0.06] pb-2 mb-px">
        {DAY_LABELS.map((label) => (
          <div
            key={label}
            className="text-center text-[11px] font-medium uppercase tracking-wider text-[#666]"
          >
            {label}
          </div>
        ))}
      </div>

      {/* Weeks */}
      <div className="grid grid-cols-7 gap-px">
        {weeks.flat().map((day) => {
          const key = dateKey(day);
          const dayEvents = eventsByDate.get(key) ?? [];
          const inMonth = isCurrentMonth(day, month, year);
          const today = isToday(day);
          const isSelected =
            selectedDate != null && isSameDay(day, selectedDate);

          return (
            <button
              key={key}
              onClick={() => onDayClick?.(day)}
              className={cn(
                "group relative flex flex-col items-stretch gap-1 rounded-lg border p-2 text-left transition-all duration-150",
                view === "month" ? "min-h-[120px]" : "min-h-[240px]",
                inMonth
                  ? "border-white/[0.06] bg-[#141414]"
                  : "border-white/[0.03] bg-[#0f0f0f]",
                today && "border-[#10a37f]/30 bg-[#10a37f]/[0.04]",
                isSelected &&
                  !today &&
                  "border-[#10a37f]/20 bg-[#10a37f]/[0.02]",
                "hover:border-white/[0.12] hover:bg-white/[0.02]"
              )}
            >
              {/* Day number */}
              <div className="flex items-center justify-between">
                <span
                  className={cn(
                    "flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium",
                    today
                      ? "bg-[#10a37f] text-white"
                      : inMonth
                        ? "text-[#ececec]"
                        : "text-[#555]"
                  )}
                >
                  {day.getDate()}
                </span>
                {/* Add icon on hover */}
                <span className="flex h-5 w-5 items-center justify-center rounded text-[#666] opacity-0 transition-opacity group-hover:opacity-100 hover:text-[#999]">
                  <Plus className="h-3 w-3" />
                </span>
              </div>

              {/* Event pills */}
              <div className="flex flex-1 flex-col gap-0.5 overflow-hidden">
                {dayEvents.slice(0, view === "month" ? 3 : 8).map((ev) => (
                  <ScheduleEventPill
                    key={ev.id}
                    event={ev}
                    onClick={() => {
                      // Stop day click propagation so the modal shows the event
                      onEventClick?.(ev);
                    }}
                  />
                ))}
                {dayEvents.length > (view === "month" ? 3 : 8) && (
                  <span className="mt-0.5 text-center text-[10px] text-[#666]">
                    +{dayEvents.length - (view === "month" ? 3 : 8)} more
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
