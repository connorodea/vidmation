"use client";

import { cn } from "@/lib/utils";
import { Check, Music, Sparkles, ArrowRightLeft } from "lucide-react";

export interface VideoTemplate {
  id: string;
  name: string;
  description: string;
  accent: string;
  captionStyle: {
    text: string;
    position: "bottom-center" | "bottom-left" | "center";
    fontWeight: string;
    fontStyle?: string;
    fontSize: string;
    fontFamily?: string;
  };
  tags: {
    transition: string;
    music: string;
    captionAnimation: string;
  };
}

interface TemplateCardProps {
  template: VideoTemplate;
  selected: boolean;
  onSelect: () => void;
}

export function TemplateCard({ template, selected, onSelect }: TemplateCardProps) {
  const { name, description, accent, captionStyle, tags } = template;

  const captionPositionClass = {
    "bottom-center": "bottom-4 left-1/2 -translate-x-1/2 text-center",
    "bottom-left": "bottom-4 left-4 text-left",
    center: "top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-center",
  }[captionStyle.position];

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "group relative flex flex-col rounded-2xl border overflow-hidden text-left transition-all duration-200 cursor-pointer",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#10a37f] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0d0d0d]",
        "hover:-translate-y-1 hover:shadow-lg hover:shadow-black/30",
        selected
          ? "border-[#10a37f] shadow-[0_0_20px_rgba(16,163,127,0.2)]"
          : "border-white/[0.06] hover:border-white/[0.15]"
      )}
    >
      {/* Mini video preview */}
      <div className="relative h-44 w-full bg-zinc-950 overflow-hidden">
        {/* Subtle gradient overlay from accent color */}
        <div
          className="absolute inset-0 opacity-[0.07]"
          style={{
            background: `radial-gradient(ellipse at 50% 80%, ${accent}, transparent 70%)`,
          }}
        />

        {/* Fake video frame lines */}
        <div className="absolute inset-3 rounded-lg border border-white/[0.04]" />

        {/* Scanline / timestamp mock */}
        <div className="absolute top-4 right-4 flex items-center gap-1.5">
          <div
            className="h-1.5 w-1.5 rounded-full animate-pulse-dot"
            style={{ backgroundColor: accent }}
          />
          <span className="text-[10px] font-mono text-white/20">0:00 / 1:00</span>
        </div>

        {/* Scene placeholder bars */}
        <div className="absolute top-4 left-4 space-y-1.5">
          <div className="h-1 w-12 rounded-full bg-white/[0.06]" />
          <div className="h-1 w-8 rounded-full bg-white/[0.04]" />
        </div>

        {/* Caption preview */}
        <div className={cn("absolute max-w-[85%]", captionPositionClass)}>
          <div
            className="rounded-md px-3 py-1.5"
            style={{
              backgroundColor: "rgba(0, 0, 0, 0.6)",
              backdropFilter: "blur(4px)",
            }}
          >
            <span
              className={cn("leading-snug text-white")}
              style={{
                fontWeight: captionStyle.fontWeight,
                fontStyle: captionStyle.fontStyle || "normal",
                fontSize: captionStyle.fontSize,
                fontFamily: captionStyle.fontFamily || "inherit",
              }}
            >
              {captionStyle.text}
            </span>
          </div>
        </div>

        {/* Accent bar at bottom of preview */}
        <div
          className="absolute bottom-0 left-0 right-0 h-[2px]"
          style={{
            background: `linear-gradient(90deg, transparent, ${accent}, transparent)`,
          }}
        />

        {/* Selected check */}
        {selected && (
          <div className="absolute top-3 left-3 flex h-6 w-6 items-center justify-center rounded-full bg-[#10a37f] shadow-md">
            <Check className="h-3.5 w-3.5 text-white" strokeWidth={2.5} />
          </div>
        )}
      </div>

      {/* Card body */}
      <div className="flex flex-1 flex-col gap-3 bg-[#111111] p-4">
        {/* Title + description */}
        <div>
          <div className="flex items-center gap-2">
            <div
              className="h-2 w-2 rounded-full shrink-0"
              style={{ backgroundColor: accent }}
            />
            <h3 className="text-sm font-semibold text-[#ececec] tracking-tight">
              {name}
            </h3>
          </div>
          <p className="text-xs text-[#666] mt-1.5 leading-relaxed pl-4">
            {description}
          </p>
        </div>

        {/* Tags */}
        <div className="flex flex-wrap gap-1.5 pt-1">
          <span
            className="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-medium"
            style={{
              backgroundColor: `${accent}14`,
              color: accent,
            }}
          >
            <ArrowRightLeft className="h-2.5 w-2.5" />
            {tags.transition}
          </span>
          <span
            className="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-medium"
            style={{
              backgroundColor: `${accent}14`,
              color: accent,
            }}
          >
            <Music className="h-2.5 w-2.5" />
            {tags.music}
          </span>
          <span
            className="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-medium"
            style={{
              backgroundColor: `${accent}14`,
              color: accent,
            }}
          >
            <Sparkles className="h-2.5 w-2.5" />
            {tags.captionAnimation}
          </span>
        </div>
      </div>
    </button>
  );
}
