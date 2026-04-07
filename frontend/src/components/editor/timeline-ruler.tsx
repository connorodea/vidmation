"use client";

import { useMemo } from "react";
import { cn } from "@/lib/utils";

interface TimelineRulerProps {
  totalDuration: number;
  zoom: number;
  className?: string;
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export function TimelineRuler({
  totalDuration,
  zoom,
  className,
}: TimelineRulerProps) {
  const markers = useMemo(() => {
    // Determine interval based on zoom level
    let interval: number;
    if (zoom >= 3) {
      interval = 5;
    } else if (zoom >= 2) {
      interval = 10;
    } else if (zoom >= 1) {
      interval = 15;
    } else {
      interval = 30;
    }

    const result: { time: number; label: string }[] = [];
    for (let t = 0; t <= totalDuration; t += interval) {
      result.push({ time: t, label: formatTime(t) });
    }
    // Always include the end marker if it doesn't align
    if (totalDuration % interval !== 0) {
      result.push({ time: totalDuration, label: formatTime(totalDuration) });
    }
    return result;
  }, [totalDuration, zoom]);

  return (
    <div
      className={cn(
        "relative h-6 border-b border-white/[0.06] select-none",
        className
      )}
    >
      {markers.map((marker) => {
        const left = (marker.time / totalDuration) * 100;
        return (
          <div
            key={marker.time}
            className="absolute top-0 flex flex-col items-center"
            style={{ left: `${left}%` }}
          >
            <div className="w-px h-2 bg-white/[0.15]" />
            <span className="text-[10px] tabular-nums text-[#555] mt-0.5 -translate-x-1/2 whitespace-nowrap">
              {marker.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}
