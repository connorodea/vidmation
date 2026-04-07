"use client";

import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from "@/components/ui/tooltip";

export interface TrackBlock {
  id: string;
  label: string;
  detail?: string;
  start: number;
  end: number;
  color: string;
  borderColor?: string;
  onClick?: () => void;
}

interface TimelineTrackProps {
  label: string;
  icon: React.ReactNode;
  blocks: TrackBlock[];
  totalDuration: number;
  className?: string;
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export function TimelineTrack({
  label,
  icon,
  blocks,
  totalDuration,
  className,
}: TimelineTrackProps) {
  return (
    <div className={cn("flex items-stretch", className)}>
      {/* Fixed left label */}
      <div className="w-24 shrink-0 flex items-center gap-1.5 px-3 border-r border-white/[0.06] bg-zinc-950/50">
        <span className="text-[#555]">{icon}</span>
        <span className="text-[11px] font-medium text-[#777] uppercase tracking-wider truncate">
          {label}
        </span>
      </div>

      {/* Track body */}
      <div className="flex-1 relative h-10 bg-white/[0.01]">
        <TooltipProvider delayDuration={200}>
          {blocks.map((block) => {
            const leftPct = (block.start / totalDuration) * 100;
            const widthPct =
              ((block.end - block.start) / totalDuration) * 100;

            return (
              <Tooltip key={block.id}>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    className={cn(
                      "absolute top-1 bottom-1 rounded-md border px-1.5 flex items-center overflow-hidden transition-all duration-100",
                      "hover:brightness-125 hover:shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#10a37f]",
                      block.onClick
                        ? "cursor-pointer"
                        : "cursor-default pointer-events-auto"
                    )}
                    style={{
                      left: `${leftPct}%`,
                      width: `${widthPct}%`,
                      backgroundColor: block.color,
                      borderColor: block.borderColor || "transparent",
                    }}
                    onClick={block.onClick}
                  >
                    <span className="text-[10px] font-medium text-white/90 truncate leading-none">
                      {block.label}
                    </span>
                  </button>
                </TooltipTrigger>
                <TooltipContent side="top">
                  <div className="space-y-0.5">
                    <div className="font-medium">{block.label}</div>
                    {block.detail && (
                      <div className="text-[#999]">{block.detail}</div>
                    )}
                    <div className="text-[#666] tabular-nums">
                      {formatTime(block.start)} - {formatTime(block.end)}
                    </div>
                  </div>
                </TooltipContent>
              </Tooltip>
            );
          })}
        </TooltipProvider>
      </div>
    </div>
  );
}
