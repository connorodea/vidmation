"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import {
  ArrowLeft,
  Sparkles,
  Clock,
  FileText,
  Volume2,
  Music,
  Type,
  Paintbrush,
  Move,
  Clapperboard,
  Palette,
  Film,
  BookOpen,
  Zap,
} from "lucide-react";
import type { WizardData, WizardStepProps } from "@/types/wizard";

const STYLE_LABELS: Record<string, string> = {
  "dark-finance": "Dark Finance",
  "stock-footage": "Stock Footage",
  "ai-cinematic": "AI Cinematic",
  educational: "Educational",
};

const NICHE_LABELS: Record<string, string> = {
  finance: "Finance",
  tech: "Tech",
  "self-improvement": "Self-Improvement",
  business: "Business",
  crypto: "Crypto",
  health: "Health",
};

const DURATION_LABELS: Record<string, string> = {
  short: "Short (< 60s)",
  medium: "Medium (3-5 min)",
  long: "Long (8-15 min)",
};

const VOICE_LABELS: Record<string, string> = {
  onyx: "Onyx",
  echo: "Echo",
  nova: "Nova",
  alloy: "Alloy",
};

const MUSIC_LABELS: Record<string, string> = {
  ambient: "Ambient",
  cinematic: "Cinematic",
  upbeat: "Upbeat",
  dark: "Dark",
  none: "None",
};

const CAPTION_LABELS: Record<string, string> = {
  "yellow-keyword": "Yellow Keyword",
  "white-clean": "White Clean",
  "bold-centered": "Bold Centered",
};

const COLOR_LABELS: Record<string, string> = {
  "cinematic-warm": "Cinematic Warm",
  "cool-moody": "Cool & Moody",
  natural: "Natural",
  custom: "Custom (AI-matched)",
};

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins === 0) return `${secs}s`;
  return `${mins}m ${secs}s`;
}

function estimateCostLocal(data: WizardData): string {
  let cost = 0.05; // base
  cost += data.totalWordCount * 0.0001; // per word
  if (data.style === "ai-cinematic") cost += 0.15;
  if (data.musicStyle !== "none") cost += 0.02;
  if (data.duration === "long") cost += 0.1;
  else if (data.duration === "medium") cost += 0.05;
  return cost.toFixed(2);
}

function estimateGenerationTime(data: WizardData): string {
  let minutes = 2; // base
  if (data.duration === "medium") minutes = 5;
  else if (data.duration === "long") minutes = 12;
  if (data.style === "ai-cinematic") minutes += 3;
  return `${minutes}-${minutes + 3} min`;
}

interface StepReviewProps extends WizardStepProps {
  onGenerate: () => void;
  isGenerating: boolean;
  generateError?: string | null;
}

export function StepReview({
  data,
  onBack,
  onGenerate,
  isGenerating,
  generateError,
}: StepReviewProps) {
  const [costEstimate, setCostEstimate] = useState<string | null>(null);
  const [costBreakdown, setCostBreakdown] = useState<Record<string, number> | null>(null);
  const [costLoading, setCostLoading] = useState(false);

  // Fetch real cost estimate from the API
  useEffect(() => {
    if (!data.style || !data.duration) return;

    let cancelled = false;
    setCostLoading(true);

    api
      .getCostEstimate({ style: data.style, duration: data.duration })
      .then((result) => {
        if (cancelled) return;
        setCostEstimate(result.estimated_cost.toFixed(2));
        setCostBreakdown(result.breakdown ?? null);
      })
      .catch(() => {
        if (cancelled) return;
        // Fall back to local estimate on API failure
        setCostEstimate(estimateCostLocal(data));
        setCostBreakdown(null);
      })
      .finally(() => {
        if (!cancelled) setCostLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [data.style, data.duration, data.totalWordCount, data.musicStyle]);

  const styleIcon = () => {
    switch (data.style) {
      case "dark-finance":
        return <Palette className="h-4 w-4" />;
      case "stock-footage":
        return <Film className="h-4 w-4" />;
      case "ai-cinematic":
        return <Sparkles className="h-4 w-4" />;
      case "educational":
        return <BookOpen className="h-4 w-4" />;
      default:
        return <Palette className="h-4 w-4" />;
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold text-[#ececec] mb-1">
          Review & Generate
        </h2>
        <p className="text-sm text-[#666]">
          Everything looks good? Hit generate to start building your video.
        </p>
      </div>

      {/* Summary card */}
      <div className="rounded-2xl border border-white/[0.06] bg-[#1a1a1a] overflow-hidden">
        {/* Topic */}
        <div className="p-6 border-b border-white/[0.04]">
          <p className="text-xs font-medium text-[#666] uppercase tracking-wider mb-2">
            Topic
          </p>
          <p className="text-sm text-[#ececec] leading-relaxed">
            {data.topic}
          </p>
        </div>

        {/* Config grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 divide-x divide-y divide-white/[0.04]">
          <SummaryItem
            icon={styleIcon()}
            label="Style"
            value={data.style ? STYLE_LABELS[data.style] : "Not selected"}
          />
          <SummaryItem
            icon={<Zap className="h-4 w-4" />}
            label="Niche"
            value={data.niche ? NICHE_LABELS[data.niche] : "Not selected"}
          />
          <SummaryItem
            icon={<Clock className="h-4 w-4" />}
            label="Duration"
            value={DURATION_LABELS[data.duration]}
          />
          <SummaryItem
            icon={<Volume2 className="h-4 w-4" />}
            label="Voice"
            value={VOICE_LABELS[data.voiceId]}
          />
          <SummaryItem
            icon={<Music className="h-4 w-4" />}
            label="Music"
            value={
              data.musicStyle !== "none"
                ? `${MUSIC_LABELS[data.musicStyle]} (${data.musicVolume}%)`
                : "None"
            }
          />
          <SummaryItem
            icon={<Type className="h-4 w-4" />}
            label="Captions"
            value={CAPTION_LABELS[data.captionStyle]}
          />
          <SummaryItem
            icon={<Paintbrush className="h-4 w-4" />}
            label="Color Grade"
            value={COLOR_LABELS[data.colorGrade]}
          />
          <SummaryItem
            icon={<Move className="h-4 w-4" />}
            label="Ken Burns"
            value={data.kenBurns ? "On" : "Off"}
          />
          <SummaryItem
            icon={<Clapperboard className="h-4 w-4" />}
            label="Film Grain"
            value={data.filmGrain ? "On" : "Off"}
          />
        </div>

        {/* Script stats */}
        <div className="flex items-center justify-between p-6 border-t border-white/[0.04] bg-white/[0.01]">
          <div className="flex items-center gap-5">
            <div className="flex items-center gap-2 text-xs text-[#999]">
              <FileText className="h-3.5 w-3.5" />
              {data.totalWordCount.toLocaleString()} words
            </div>
            <div className="flex items-center gap-2 text-xs text-[#999]">
              <Clock className="h-3.5 w-3.5" />
              ~{formatTime(data.estimatedDuration)}
            </div>
            <div className="flex items-center gap-2 text-xs text-[#999]">
              <FileText className="h-3.5 w-3.5" />
              {data.script.length} sections
            </div>
          </div>
        </div>
      </div>

      {/* Cost + time estimates */}
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-white/[0.06] bg-[#1a1a1a] p-5">
          <p className="text-xs text-[#666] mb-1">Estimated Cost</p>
          {costLoading ? (
            <div className="h-8 flex items-center">
              <div className="h-4 w-4 border-2 border-[#10a37f]/30 border-t-[#10a37f] rounded-full animate-spin" />
            </div>
          ) : (
            <p className="text-2xl font-semibold text-[#ececec]">
              ${costEstimate ?? estimateCostLocal(data)}
            </p>
          )}
          <p className="text-[11px] text-[#666] mt-1">
            Based on script length and style
          </p>
          {costBreakdown && (
            <div className="mt-2 space-y-0.5">
              {Object.entries(costBreakdown).map(([key, value]) => (
                <div key={key} className="flex justify-between text-[10px] text-[#555]">
                  <span className="capitalize">{key.replace(/_/g, " ")}</span>
                  <span>${value.toFixed(2)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-[#1a1a1a] p-5">
          <p className="text-xs text-[#666] mb-1">Generation Time</p>
          <p className="text-2xl font-semibold text-[#ececec]">
            {estimateGenerationTime(data)}
          </p>
          <p className="text-[11px] text-[#666] mt-1">
            You will be notified when ready
          </p>
        </div>
      </div>

      {/* Generation error */}
      {generateError && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-5 py-4">
          <p className="text-sm text-red-400">{generateError}</p>
        </div>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between pt-2">
        <Button
          variant="ghost"
          onClick={onBack}
          disabled={isGenerating}
          className="gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>

        <Button
          size="lg"
          onClick={onGenerate}
          disabled={isGenerating}
          className="min-w-[200px] gap-2 text-base h-13 px-8"
        >
          {isGenerating ? (
            <span className="flex items-center gap-2.5">
              <span className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Starting...
            </span>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              Generate Video
            </>
          )}
        </Button>
      </div>
    </div>
  );
}

function SummaryItem({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="p-4">
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-[#666]">{icon}</span>
        <span className="text-[11px] font-medium text-[#666] uppercase tracking-wider">
          {label}
        </span>
      </div>
      <p className="text-sm text-[#ececec]">{value}</p>
    </div>
  );
}
