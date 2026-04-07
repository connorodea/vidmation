"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Play, Pause, Check } from "lucide-react";

interface VoicePreviewProps {
  name: string;
  voiceId: string;
  description: string;
  tags: string[];
  selected: boolean;
  onSelect: () => void;
}

export function VoicePreview({
  name,
  voiceId,
  description,
  tags,
  selected,
  onSelect,
}: VoicePreviewProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [waveformBars] = useState(() =>
    Array.from({ length: 24 }, () => 0.2 + Math.random() * 0.8)
  );
  const animationRef = useRef<number | null>(null);
  const [playbackPosition, setPlaybackPosition] = useState(0);

  const simulatePlayback = useCallback(() => {
    let start: number | null = null;
    const duration = 3000; // 3 second simulated playback

    const animate = (timestamp: number) => {
      if (!start) start = timestamp;
      const elapsed = timestamp - start;
      const progress = Math.min(elapsed / duration, 1);
      setPlaybackPosition(progress);

      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate);
      } else {
        setIsPlaying(false);
        setPlaybackPosition(0);
      }
    };

    animationRef.current = requestAnimationFrame(animate);
  }, []);

  const handlePlayPause = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      if (isPlaying) {
        if (animationRef.current) {
          cancelAnimationFrame(animationRef.current);
        }
        setIsPlaying(false);
        setPlaybackPosition(0);
      } else {
        setIsPlaying(true);
        simulatePlayback();
      }
    },
    [isPlaying, simulatePlayback]
  );

  useEffect(() => {
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, []);

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "group relative flex flex-col rounded-2xl border p-5 text-left transition-all duration-200 w-full",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#10a37f] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0d0d0d]",
        selected
          ? "border-[#10a37f] bg-[#10a37f]/[0.04] shadow-[0_0_0_1px_#10a37f]"
          : "border-white/[0.08] bg-[#1a1a1a] hover:border-white/[0.15]"
      )}
    >
      <div className="flex items-start justify-between w-full mb-3">
        <div className="flex items-center gap-3">
          {/* Play button */}
          <div
            role="button"
            tabIndex={0}
            onClick={handlePlayPause}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                handlePlayPause(e as unknown as React.MouseEvent);
              }
            }}
            className={cn(
              "flex h-10 w-10 shrink-0 items-center justify-center rounded-full transition-all duration-200",
              isPlaying
                ? "bg-[#10a37f] text-white"
                : "bg-white/[0.06] text-[#999] hover:bg-white/[0.1] hover:text-[#ececec]"
            )}
            aria-label={isPlaying ? `Pause ${name} preview` : `Play ${name} preview`}
          >
            {isPlaying ? (
              <Pause className="h-4 w-4" />
            ) : (
              <Play className="h-4 w-4 ml-0.5" />
            )}
          </div>

          <div>
            <p className="text-sm font-medium text-[#ececec]">{name}</p>
            <p className="text-xs text-[#666] mt-0.5">{description}</p>
          </div>
        </div>

        {/* Selected indicator */}
        {selected && (
          <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#10a37f]">
            <Check className="h-3.5 w-3.5 text-white" />
          </div>
        )}
      </div>

      {/* Waveform visualization */}
      <div className="flex items-end gap-[2px] h-8 w-full mt-1" aria-hidden="true">
        {waveformBars.map((height, i) => {
          const barProgress = i / waveformBars.length;
          const isActive = isPlaying && barProgress <= playbackPosition;

          return (
            <div
              key={`${voiceId}-bar-${i}`}
              className={cn(
                "flex-1 rounded-full transition-colors duration-100",
                isActive ? "bg-[#10a37f]" : "bg-white/[0.08]"
              )}
              style={{ height: `${height * 100}%` }}
            />
          );
        })}
      </div>

      {/* Tags */}
      <div className="flex flex-wrap gap-1.5 mt-3">
        {tags.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center rounded-full bg-white/[0.04] px-2.5 py-0.5 text-[11px] text-[#999]"
          >
            {tag}
          </span>
        ))}
      </div>
    </button>
  );
}
