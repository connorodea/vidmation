"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { VoiceCard } from "@/components/voices/voice-card";
import type { Voice, VoiceProvider } from "@/components/voices/voice-card";
import { Mic, Plus, AudioLines } from "lucide-react";

const SAMPLE_VOICES: Voice[] = [
  {
    id: "1",
    name: "Alex Narrator",
    provider: "elevenlabs",
    isCloned: false,
    usageCount: 342,
  },
  {
    id: "2",
    name: "Sarah Tech",
    provider: "elevenlabs",
    isCloned: true,
    usageCount: 187,
  },
  {
    id: "3",
    name: "Deep Baritone",
    provider: "replicate",
    isCloned: false,
    usageCount: 95,
  },
  {
    id: "4",
    name: "Connor Custom",
    provider: "fal",
    isCloned: true,
    usageCount: 28,
  },
  {
    id: "5",
    name: "Studio Pro",
    provider: "elevenlabs",
    isCloned: false,
    usageCount: 451,
  },
  {
    id: "6",
    name: "Warm Storyteller",
    provider: "replicate",
    isCloned: true,
    usageCount: 63,
  },
];

type FilterOption = "all" | VoiceProvider;

const FILTER_OPTIONS: { value: FilterOption; label: string }[] = [
  { value: "all", label: "All" },
  { value: "elevenlabs", label: "ElevenLabs" },
  { value: "replicate", label: "Replicate" },
  { value: "fal", label: "fal" },
];

export default function VoicesPage() {
  const [filter, setFilter] = useState<FilterOption>("all");
  const [voices] = useState<Voice[]>(SAMPLE_VOICES);

  const filteredVoices = useMemo(() => {
    if (filter === "all") return voices;
    return voices.filter((v) => v.provider === filter);
  }, [voices, filter]);

  return (
    <div className="min-h-screen bg-[#0d0d0d]">
      <div className="mx-auto max-w-[1440px] px-6 py-8">
        {/* Page header */}
        <div className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AudioLines className="h-5 w-5 text-[#666]" />
            <h1 className="text-2xl font-semibold text-[#ececec]">Voices</h1>
          </div>
          <Link href="/voices/clone">
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              Clone Voice
            </Button>
          </Link>
        </div>

        {/* Filters */}
        <div className="mb-6 flex items-center gap-1.5">
          {FILTER_OPTIONS.map((option) => (
            <button
              key={option.value}
              onClick={() => setFilter(option.value)}
              className={`rounded-lg px-3.5 py-1.5 text-xs font-medium transition-all duration-150 ${
                filter === option.value
                  ? "bg-white/[0.08] text-[#ececec]"
                  : "text-[#666] hover:bg-white/[0.04] hover:text-[#999]"
              }`}
            >
              {option.label}
            </button>
          ))}
          <span className="ml-2 text-xs tabular-nums text-[#666]">
            {filteredVoices.length} voice{filteredVoices.length !== 1 ? "s" : ""}
          </span>
        </div>

        {/* Voice grid */}
        {filteredVoices.length > 0 ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filteredVoices.map((voice) => (
              <VoiceCard key={voice.id} voice={voice} />
            ))}
          </div>
        ) : (
          /* Empty state */
          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-white/[0.08] py-24">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-white/[0.04]">
              <Mic className="h-6 w-6 text-[#666]" />
            </div>
            <p className="text-sm font-medium text-[#999]">No voices found</p>
            <p className="mt-1 text-xs text-[#666]">
              {filter === "all"
                ? "Clone a voice or add one from a provider to get started"
                : `No voices from ${FILTER_OPTIONS.find((o) => o.value === filter)?.label}`}
            </p>
            <Link href="/voices/clone" className="mt-5">
              <Button variant="secondary" size="sm" className="gap-2">
                <Plus className="h-3.5 w-3.5" />
                Clone Voice
              </Button>
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
