"use client";

import { Button } from "@/components/ui/button";
import { VoicePreview } from "@/components/videos/wizard/voice-preview";
import { cn } from "@/lib/utils";
import {
  ArrowLeft,
  ArrowRight,
  Volume2,
  Music,
  Check,
} from "lucide-react";
import type { WizardStepProps, VoiceId, MusicStyle } from "@/types/wizard";

const VOICES: {
  id: VoiceId;
  name: string;
  description: string;
  tags: string[];
}[] = [
  {
    id: "onyx",
    name: "Onyx",
    description: "Deep, authoritative, and commanding presence",
    tags: ["Deep", "Authoritative", "Male"],
  },
  {
    id: "echo",
    name: "Echo",
    description: "Confident and energetic delivery",
    tags: ["Confident", "Energetic", "Male"],
  },
  {
    id: "nova",
    name: "Nova",
    description: "Warm, engaging, and naturally conversational",
    tags: ["Warm", "Engaging", "Female"],
  },
  {
    id: "alloy",
    name: "Alloy",
    description: "Neutral and balanced for versatile content",
    tags: ["Neutral", "Balanced", "Unisex"],
  },
];

const MUSIC_STYLES: {
  id: MusicStyle;
  label: string;
  description: string;
}[] = [
  {
    id: "ambient",
    label: "Ambient",
    description: "Soft atmospheric background",
  },
  {
    id: "cinematic",
    label: "Cinematic",
    description: "Epic orchestral feel",
  },
  {
    id: "upbeat",
    label: "Upbeat",
    description: "Energetic and motivating",
  },
  {
    id: "dark",
    label: "Dark",
    description: "Moody and suspenseful",
  },
  {
    id: "none",
    label: "None",
    description: "Voice only, no music",
  },
];

export function StepVoice({ data, onUpdate, onNext, onBack }: WizardStepProps) {
  return (
    <div className="space-y-10">
      {/* Voice selection */}
      <div>
        <div className="flex items-center gap-2.5 mb-1">
          <Volume2 className="h-5 w-5 text-[#10a37f]" />
          <h2 className="text-xl font-semibold text-[#ececec]">
            Choose a Voice
          </h2>
        </div>
        <p className="text-sm text-[#666] mb-5">
          Select the AI voice that best fits your content. Click the play button
          to preview.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {VOICES.map((voice) => (
            <VoicePreview
              key={voice.id}
              name={voice.name}
              voiceId={voice.id}
              description={voice.description}
              tags={voice.tags}
              selected={data.voiceId === voice.id}
              onSelect={() => onUpdate({ voiceId: voice.id })}
            />
          ))}
        </div>
      </div>

      {/* Music selection */}
      <div>
        <div className="flex items-center gap-2.5 mb-1">
          <Music className="h-5 w-5 text-[#10a37f]" />
          <h2 className="text-xl font-semibold text-[#ececec]">
            Background Music
          </h2>
        </div>
        <p className="text-sm text-[#666] mb-5">
          Set the mood with background music that complements your video.
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          {MUSIC_STYLES.map((m) => (
            <button
              key={m.id}
              type="button"
              onClick={() => onUpdate({ musicStyle: m.id })}
              className={cn(
                "flex flex-col items-center rounded-xl border p-4 transition-all duration-200",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#10a37f]",
                data.musicStyle === m.id
                  ? "border-[#10a37f] bg-[#10a37f]/[0.06]"
                  : "border-white/[0.08] bg-[#1a1a1a] hover:border-white/[0.15]"
              )}
            >
              <div className="relative mb-2">
                <span
                  className={cn(
                    "text-sm font-medium transition-colors",
                    data.musicStyle === m.id
                      ? "text-[#10a37f]"
                      : "text-[#ececec]"
                  )}
                >
                  {m.label}
                </span>
                {data.musicStyle === m.id && (
                  <Check className="absolute -right-5 top-0.5 h-3.5 w-3.5 text-[#10a37f]" />
                )}
              </div>
              <span className="text-[11px] text-[#666] text-center leading-tight">
                {m.description}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Volume slider */}
      {data.musicStyle !== "none" && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <label
              htmlFor="music-volume"
              className="text-sm font-medium text-[#ececec]"
            >
              Music Volume
            </label>
            <span className="text-xs text-[#666] tabular-nums">
              {data.musicVolume}%
            </span>
          </div>

          <div className="relative">
            <input
              id="music-volume"
              type="range"
              min={0}
              max={100}
              step={5}
              value={data.musicVolume}
              onChange={(e) =>
                onUpdate({ musicVolume: parseInt(e.target.value, 10) })
              }
              className="w-full h-1.5 rounded-full appearance-none cursor-pointer bg-white/[0.06] accent-[#10a37f]
                [&::-webkit-slider-thumb]:appearance-none
                [&::-webkit-slider-thumb]:h-4
                [&::-webkit-slider-thumb]:w-4
                [&::-webkit-slider-thumb]:rounded-full
                [&::-webkit-slider-thumb]:bg-[#10a37f]
                [&::-webkit-slider-thumb]:shadow-[0_0_0_4px_rgba(16,163,127,0.15)]
                [&::-webkit-slider-thumb]:transition-shadow
                [&::-webkit-slider-thumb]:duration-150
                [&::-webkit-slider-thumb]:hover:shadow-[0_0_0_6px_rgba(16,163,127,0.2)]
                [&::-moz-range-thumb]:h-4
                [&::-moz-range-thumb]:w-4
                [&::-moz-range-thumb]:rounded-full
                [&::-moz-range-thumb]:bg-[#10a37f]
                [&::-moz-range-thumb]:border-none
              "
              style={{
                background: `linear-gradient(to right, #10a37f ${data.musicVolume}%, rgba(255,255,255,0.06) ${data.musicVolume}%)`,
              }}
              aria-label="Background music volume"
            />
          </div>

          <div className="flex justify-between mt-1.5">
            <span className="text-[10px] text-[#666]">Subtle</span>
            <span className="text-[10px] text-[#666]">Prominent</span>
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between pt-2">
        <Button variant="ghost" onClick={onBack} className="gap-2">
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>

        <Button size="lg" onClick={onNext} className="min-w-[160px] gap-2">
          Visual Settings
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
