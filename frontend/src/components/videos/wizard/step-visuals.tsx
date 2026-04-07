"use client";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Type,
  Paintbrush,
  Move,
  Clapperboard,
} from "lucide-react";
import type { WizardStepProps, CaptionStyle, ColorGrade } from "@/types/wizard";

const CAPTION_STYLES: {
  id: CaptionStyle;
  label: string;
  description: string;
  preview: React.ReactNode;
}[] = [
  {
    id: "yellow-keyword",
    label: "Yellow Keyword",
    description: "TheCoinFinancials style with highlighted keywords",
    preview: (
      <div className="flex flex-col items-center gap-1 py-3">
        <span className="text-xs text-[#ccc]">The market will</span>
        <span className="text-sm font-bold text-[#f5c542]">CRASH</span>
        <span className="text-xs text-[#ccc]">before recovery</span>
      </div>
    ),
  },
  {
    id: "white-clean",
    label: "White Clean",
    description: "Minimal and modern subtitle look",
    preview: (
      <div className="flex flex-col items-center gap-1 py-3">
        <span className="text-sm text-white/90 font-normal">
          The market will crash
        </span>
        <span className="text-sm text-white/90 font-normal">
          before recovery
        </span>
      </div>
    ),
  },
  {
    id: "bold-centered",
    label: "Bold Centered",
    description: "Submagic style with bold impact text",
    preview: (
      <div className="flex flex-col items-center gap-0.5 py-3">
        <span className="text-base font-black text-white uppercase tracking-wide">
          CRASH
        </span>
        <span className="text-[11px] text-white/60 font-medium uppercase tracking-widest">
          before recovery
        </span>
      </div>
    ),
  },
];

const COLOR_GRADES: {
  id: ColorGrade;
  label: string;
  description: string;
  gradient: string;
}[] = [
  {
    id: "cinematic-warm",
    label: "Cinematic Warm",
    description: "Golden tones, film-like warmth",
    gradient: "bg-gradient-to-r from-[#3d2815] via-[#5a3a1a] to-[#3d2815]",
  },
  {
    id: "cool-moody",
    label: "Cool & Moody",
    description: "Blue-teal tones, modern feel",
    gradient: "bg-gradient-to-r from-[#0f1a2e] via-[#1a2d4a] to-[#0f1a2e]",
  },
  {
    id: "natural",
    label: "Natural",
    description: "True-to-life colors, no grade",
    gradient: "bg-gradient-to-r from-[#1a2218] via-[#2a3525] to-[#1a2218]",
  },
  {
    id: "custom",
    label: "Custom",
    description: "AI-matched to your topic",
    gradient: "bg-gradient-to-r from-[#1a1a2e] via-[#2a1a3a] to-[#1a1a2e]",
  },
];

export function StepVisuals({ data, onUpdate, onNext, onBack }: WizardStepProps) {
  return (
    <div className="space-y-10">
      {/* Caption style */}
      <div>
        <div className="flex items-center gap-2.5 mb-1">
          <Type className="h-5 w-5 text-[#10a37f]" />
          <h2 className="text-xl font-semibold text-[#ececec]">
            Caption Style
          </h2>
        </div>
        <p className="text-sm text-[#666] mb-5">
          Choose how your subtitles and captions will appear on screen.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {CAPTION_STYLES.map((style) => (
            <button
              key={style.id}
              type="button"
              onClick={() => onUpdate({ captionStyle: style.id })}
              className={cn(
                "relative flex flex-col rounded-2xl border overflow-hidden text-left transition-all duration-200",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#10a37f]",
                data.captionStyle === style.id
                  ? "border-[#10a37f] shadow-[0_0_0_1px_#10a37f]"
                  : "border-white/[0.08] hover:border-white/[0.15]"
              )}
            >
              {/* Preview area */}
              <div className="relative bg-[#111] h-24 flex items-center justify-center">
                {style.preview}
                {data.captionStyle === style.id && (
                  <div className="absolute top-2.5 right-2.5 flex h-5 w-5 items-center justify-center rounded-full bg-[#10a37f]">
                    <Check className="h-3 w-3 text-white" />
                  </div>
                )}
              </div>

              {/* Label */}
              <div className="p-3.5 bg-[#1a1a1a]">
                <p className="text-sm font-medium text-[#ececec]">
                  {style.label}
                </p>
                <p className="text-[11px] text-[#666] mt-0.5">
                  {style.description}
                </p>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Color grade */}
      <div>
        <div className="flex items-center gap-2.5 mb-1">
          <Paintbrush className="h-5 w-5 text-[#10a37f]" />
          <h2 className="text-xl font-semibold text-[#ececec]">
            Color Grade
          </h2>
        </div>
        <p className="text-sm text-[#666] mb-5">
          Set the overall color mood for your video.
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {COLOR_GRADES.map((grade) => (
            <button
              key={grade.id}
              type="button"
              onClick={() => onUpdate({ colorGrade: grade.id })}
              className={cn(
                "relative flex flex-col rounded-xl border overflow-hidden text-left transition-all duration-200",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#10a37f]",
                data.colorGrade === grade.id
                  ? "border-[#10a37f] shadow-[0_0_0_1px_#10a37f]"
                  : "border-white/[0.08] hover:border-white/[0.15]"
              )}
            >
              <div
                className={cn(
                  "h-16 w-full flex items-center justify-center",
                  grade.gradient
                )}
              >
                {data.colorGrade === grade.id && (
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-[#10a37f]">
                    <Check className="h-3.5 w-3.5 text-white" />
                  </div>
                )}
              </div>
              <div className="p-3 bg-[#1a1a1a]">
                <p className="text-xs font-medium text-[#ececec]">
                  {grade.label}
                </p>
                <p className="text-[10px] text-[#666] mt-0.5">
                  {grade.description}
                </p>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Toggle options */}
      <div>
        <div className="flex items-center gap-2.5 mb-1">
          <Clapperboard className="h-5 w-5 text-[#10a37f]" />
          <h2 className="text-xl font-semibold text-[#ececec]">
            Effects
          </h2>
        </div>
        <p className="text-sm text-[#666] mb-5">
          Add subtle effects to enhance the cinematic quality.
        </p>

        <div className="space-y-3">
          <ToggleOption
            icon={<Move className="h-4 w-4" />}
            label="Ken Burns Effect"
            description="Slow pan and zoom on still images for a dynamic feel"
            enabled={data.kenBurns}
            onToggle={() => onUpdate({ kenBurns: !data.kenBurns })}
          />

          <ToggleOption
            icon={<Clapperboard className="h-4 w-4" />}
            label="Film Grain"
            description="Subtle grain overlay for a cinematic, analog texture"
            enabled={data.filmGrain}
            onToggle={() => onUpdate({ filmGrain: !data.filmGrain })}
          />
        </div>
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between pt-2">
        <Button variant="ghost" onClick={onBack} className="gap-2">
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>

        <Button size="lg" onClick={onNext} className="min-w-[160px] gap-2">
          Review
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

function ToggleOption({
  icon,
  label,
  description,
  enabled,
  onToggle,
}: {
  icon: React.ReactNode;
  label: string;
  description: string;
  enabled: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={cn(
        "flex items-center gap-4 w-full rounded-xl border p-4 text-left transition-all duration-200",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#10a37f]",
        enabled
          ? "border-[#10a37f]/40 bg-[#10a37f]/[0.04]"
          : "border-white/[0.08] bg-[#1a1a1a] hover:border-white/[0.12]"
      )}
      role="switch"
      aria-checked={enabled}
    >
      <div
        className={cn(
          "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors duration-200",
          enabled ? "bg-[#10a37f]/15 text-[#10a37f]" : "bg-white/[0.04] text-[#666]"
        )}
      >
        {icon}
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[#ececec]">{label}</p>
        <p className="text-xs text-[#666] mt-0.5">{description}</p>
      </div>

      {/* Toggle switch */}
      <div
        className={cn(
          "relative h-6 w-11 shrink-0 rounded-full transition-colors duration-200",
          enabled ? "bg-[#10a37f]" : "bg-white/[0.1]"
        )}
        aria-hidden="true"
      >
        <div
          className={cn(
            "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform duration-200",
            enabled ? "translate-x-[22px]" : "translate-x-0.5"
          )}
        />
      </div>
    </button>
  );
}
