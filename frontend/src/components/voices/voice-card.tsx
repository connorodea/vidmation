"use client";

import { useState, useCallback } from "react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Play, Pause, Mic } from "lucide-react";

type VoiceProvider = "elevenlabs" | "replicate" | "fal";

interface Voice {
  id: string;
  name: string;
  provider: VoiceProvider;
  isCloned: boolean;
  usageCount: number;
  previewUrl?: string;
}

const PROVIDER_CONFIG: Record<
  VoiceProvider,
  { label: string; className: string }
> = {
  elevenlabs: {
    label: "ElevenLabs",
    className: "bg-[#6366f1]/12 text-[#6366f1]",
  },
  replicate: {
    label: "Replicate",
    className: "bg-[#f59e0b]/12 text-[#f59e0b]",
  },
  fal: {
    label: "fal",
    className: "bg-[#10a37f]/12 text-[#10a37f]",
  },
};

interface VoiceCardProps {
  voice: Voice;
  className?: string;
}

export function VoiceCard({ voice, className }: VoiceCardProps) {
  const [isPlaying, setIsPlaying] = useState(false);

  const handlePlayToggle = useCallback(() => {
    setIsPlaying((prev) => !prev);
    // In a real implementation, this would control audio playback
    if (!isPlaying) {
      setTimeout(() => setIsPlaying(false), 3000);
    }
  }, [isPlaying]);

  const providerConfig = PROVIDER_CONFIG[voice.provider];
  const initial = voice.name.charAt(0).toUpperCase();

  return (
    <div
      className={cn(
        "group rounded-2xl border border-white/[0.08] bg-[#1a1a1a] p-5 transition-all duration-150 hover:border-white/[0.12]",
        className
      )}
    >
      <div className="flex items-start gap-4">
        {/* Avatar */}
        <div className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-white/[0.06] text-sm font-semibold text-[#ececec]">
          {initial}
          {voice.isCloned && (
            <div
              className="absolute -bottom-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-[#10a37f]"
              aria-label="Cloned voice"
            >
              <Mic className="h-2.5 w-2.5 text-white" />
            </div>
          )}
        </div>

        {/* Info */}
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-2">
            <h3 className="truncate text-sm font-medium text-[#ececec]">
              {voice.name}
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <Badge className={cn("text-[10px]", providerConfig.className)}>
              {providerConfig.label}
            </Badge>
            {voice.isCloned && (
              <Badge className="text-[10px] bg-white/[0.06] text-[#999]">
                Cloned
              </Badge>
            )}
          </div>
        </div>

        {/* Play button */}
        <button
          onClick={handlePlayToggle}
          className={cn(
            "flex h-9 w-9 shrink-0 items-center justify-center rounded-full transition-all duration-150",
            isPlaying
              ? "bg-[#10a37f] text-white"
              : "border border-white/[0.08] text-[#999] hover:border-white/[0.15] hover:text-[#ececec]"
          )}
          aria-label={isPlaying ? "Pause preview" : "Play preview"}
        >
          {isPlaying ? (
            <Pause className="h-3.5 w-3.5" />
          ) : (
            <Play className="ml-0.5 h-3.5 w-3.5" />
          )}
        </button>
      </div>

      {/* Usage count */}
      <div className="mt-4 flex items-center justify-between border-t border-white/[0.06] pt-3">
        <span className="text-[11px] text-[#666]">
          {voice.usageCount.toLocaleString()} videos generated
        </span>
        {isPlaying && (
          <div className="flex items-center gap-1">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="h-3 w-0.5 animate-pulse rounded-full bg-[#10a37f]"
                style={{ animationDelay: `${i * 150}ms` }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Re-export the Voice type for use in pages
export type { Voice, VoiceProvider };
