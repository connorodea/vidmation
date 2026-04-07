"use client";

import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StyleCard } from "@/components/videos/wizard/style-card";
import { cn } from "@/lib/utils";
import {
  Palette,
  Film,
  Sparkles,
  BookOpen,
  ArrowRight,
} from "lucide-react";
import type {
  WizardStepProps,
  VideoStyle,
  VideoNiche,
  VideoDuration,
} from "@/types/wizard";

const STYLES: {
  id: VideoStyle;
  title: string;
  description: string;
  gradient: string;
  icon: React.ReactNode;
}[] = [
  {
    id: "dark-finance",
    title: "Dark Finance",
    description:
      "Oil painting visuals with yellow keyword captions. TheCoinFinancials style.",
    gradient: "bg-gradient-to-br from-[#1a1207] via-[#2a1f0f] to-[#0f0d08]",
    icon: <Palette className="h-8 w-8" />,
  },
  {
    id: "stock-footage",
    title: "Stock Footage",
    description:
      "Traditional B-roll with professional transitions and overlays.",
    gradient: "bg-gradient-to-br from-[#0f1419] via-[#1a2332] to-[#0d1117]",
    icon: <Film className="h-8 w-8" />,
  },
  {
    id: "ai-cinematic",
    title: "AI Cinematic",
    description:
      "AI-generated cinematic clips with Sora/Replicate visual quality.",
    gradient: "bg-gradient-to-br from-[#1a0a2e] via-[#16082a] to-[#0d0519]",
    icon: <Sparkles className="h-8 w-8" />,
  },
  {
    id: "educational",
    title: "Educational",
    description:
      "Clean minimal style with diagrams, annotations, and clear visuals.",
    gradient: "bg-gradient-to-br from-[#071a14] via-[#0a1f18] to-[#040f0b]",
    icon: <BookOpen className="h-8 w-8" />,
  },
];

const NICHES: { value: VideoNiche; label: string }[] = [
  { value: "finance", label: "Finance" },
  { value: "tech", label: "Tech" },
  { value: "self-improvement", label: "Self-Improvement" },
  { value: "business", label: "Business" },
  { value: "crypto", label: "Crypto" },
  { value: "health", label: "Health" },
];

const DURATIONS: {
  value: VideoDuration;
  label: string;
  desc: string;
}[] = [
  { value: "short", label: "Short", desc: "< 60s" },
  { value: "medium", label: "Medium", desc: "3-5 min" },
  { value: "long", label: "Long", desc: "8-15 min" },
];

export function StepTopic({ data, onUpdate, onNext }: WizardStepProps) {
  const canProceed =
    data.topic.trim().length > 0 && data.style !== null && data.niche !== null;

  return (
    <div className="space-y-10">
      {/* Hero input */}
      <div>
        <label
          htmlFor="wizard-topic"
          className="block text-xl font-semibold text-[#ececec] mb-2"
        >
          What is your video about?
        </label>
        <p className="text-sm text-[#666] mb-4">
          Describe the topic, angle, or story you want to tell. The more detail,
          the better the output.
        </p>
        <Textarea
          id="wizard-topic"
          value={data.topic}
          onChange={(e) => onUpdate({ topic: e.target.value })}
          placeholder="e.g., Why 97% of day traders lose money and the psychology behind it..."
          rows={4}
          className="text-base px-5 py-4 min-h-[120px] rounded-2xl bg-[#111] border-white/[0.06] focus-visible:border-[#10a37f]"
          autoFocus
        />
        {data.topic.length > 0 && (
          <p className="text-xs text-[#666] mt-2 text-right">
            {data.topic.length} characters
          </p>
        )}
      </div>

      {/* Style selector */}
      <div>
        <h3 className="text-sm font-medium text-[#ececec] mb-1">
          Visual Style
        </h3>
        <p className="text-xs text-[#666] mb-4">
          Choose how your video will look and feel.
        </p>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {STYLES.map((style) => (
            <StyleCard
              key={style.id}
              title={style.title}
              description={style.description}
              gradient={style.gradient}
              icon={style.icon}
              selected={data.style === style.id}
              onSelect={() => onUpdate({ style: style.id })}
            />
          ))}
        </div>
      </div>

      {/* Niche + Duration row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        {/* Niche selector */}
        <div>
          <label className="block text-sm font-medium text-[#ececec] mb-1">
            Niche
          </label>
          <p className="text-xs text-[#666] mb-3">
            Helps tailor script tone and visuals.
          </p>
          <Select
            value={data.niche ?? undefined}
            onValueChange={(v) => onUpdate({ niche: v as VideoNiche })}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select a niche" />
            </SelectTrigger>
            <SelectContent>
              {NICHES.map((n) => (
                <SelectItem key={n.value} value={n.value}>
                  {n.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Duration */}
        <div>
          <label className="block text-sm font-medium text-[#ececec] mb-1">
            Target Duration
          </label>
          <p className="text-xs text-[#666] mb-3">
            Controls script length and pacing.
          </p>
          <div className="grid grid-cols-3 gap-2">
            {DURATIONS.map((d) => (
              <button
                key={d.value}
                type="button"
                onClick={() => onUpdate({ duration: d.value })}
                className={cn(
                  "h-11 rounded-xl border text-sm transition-all duration-150 flex flex-col items-center justify-center gap-0.5",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#10a37f]",
                  data.duration === d.value
                    ? "border-[#10a37f] bg-[#10a37f]/10 text-[#10a37f]"
                    : "border-white/[0.08] bg-transparent text-[#999] hover:border-white/[0.15] hover:text-[#ececec]"
                )}
              >
                <span className="text-xs font-medium">{d.label}</span>
                <span className="text-[10px] opacity-60">{d.desc}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Next button */}
      <div className="flex justify-end pt-2">
        <Button
          size="lg"
          onClick={onNext}
          disabled={!canProceed}
          className="min-w-[160px] gap-2"
        >
          Generate Script
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
