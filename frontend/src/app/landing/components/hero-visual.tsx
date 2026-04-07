"use client";

import { Sparkles, Play, ChevronRight } from "lucide-react";

const STYLE_CHIPS = [
  { name: "Cinematic", color: "#3b82f6" },
  { name: "Oil Painting", color: "#d97706" },
  { name: "Anime", color: "#ec4899" },
  { name: "Watercolor", color: "#a78bfa" },
];

export function HeroVisual() {
  return (
    <div className="animate-float gradient-border mx-auto mt-16 w-full max-w-[800px] overflow-hidden rounded-2xl sm:mt-20">
      <div className="bg-[#111111] p-1">
        {/* Title bar */}
        <div className="flex items-center gap-2 rounded-t-xl bg-[#0a0a0a] px-4 py-3">
          <div className="flex gap-1.5">
            <div className="h-2.5 w-2.5 rounded-full bg-[#333]" />
            <div className="h-2.5 w-2.5 rounded-full bg-[#333]" />
            <div className="h-2.5 w-2.5 rounded-full bg-[#333]" />
          </div>
          <div className="ml-3 flex h-6 flex-1 items-center rounded-md bg-[#1a1a1a] px-3">
            <span className="text-[11px] text-[#555]">
              app.aividio.com/create
            </span>
          </div>
        </div>

        {/* Dashboard mockup */}
        <div className="space-y-4 bg-[#0a0a0a] p-5 pb-6 sm:p-6">
          {/* Wizard header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-[#10a37f]" />
              <span className="text-sm font-semibold text-[#e0e0e0]">
                Create New Video
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              {["Topic", "Style", "Voice", "Review"].map((step, i) => (
                <div key={step} className="flex items-center gap-1.5">
                  <div
                    className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${
                      i === 0
                        ? "bg-[#10a37f] text-white"
                        : "bg-[#1a1a1a] text-[#555]"
                    }`}
                  >
                    {i + 1}
                  </div>
                  <span
                    className={`hidden text-[11px] sm:inline ${
                      i === 0
                        ? "font-medium text-[#ccc]"
                        : "text-[#444]"
                    }`}
                  >
                    {step}
                  </span>
                  {i < 3 && (
                    <ChevronRight className="h-3 w-3 text-[#333]" />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Topic input area */}
          <div className="rounded-xl border border-white/[0.06] bg-[#111] p-4">
            <label className="text-xs font-medium text-[#666]">
              Video Topic
            </label>
            <div className="mt-2 flex items-start gap-3">
              <div className="flex-1">
                <div className="text-sm text-[#ccc]">
                  Top 10 AI Tools That Will Replace Your Job in 2025
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <span className="rounded-full bg-[#10a37f]/10 px-2.5 py-0.5 text-[10px] font-medium text-[#10a37f]">
                    Technology
                  </span>
                  <span className="rounded-full bg-white/[0.05] px-2.5 py-0.5 text-[10px] text-[#666]">
                    8-12 min
                  </span>
                  <span className="rounded-full bg-white/[0.05] px-2.5 py-0.5 text-[10px] text-[#666]">
                    Engaging tone
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Style selector preview */}
          <div className="rounded-xl border border-white/[0.06] bg-[#111] p-4">
            <label className="text-xs font-medium text-[#666]">
              Visual Style
            </label>
            <div className="mt-2 flex gap-2">
              {STYLE_CHIPS.map((style, i) => (
                <div
                  key={style.name}
                  className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-[11px] font-medium transition-colors ${
                    i === 0
                      ? "border-[#10a37f]/30 bg-[#10a37f]/10 text-[#10a37f]"
                      : "border-white/[0.06] text-[#555] hover:border-white/[0.1]"
                  }`}
                >
                  <div
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: style.color }}
                  />
                  <span className="hidden sm:inline">{style.name}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Generate button */}
          <div className="flex items-center justify-between pt-1">
            <div className="flex items-center gap-2 text-[11px] text-[#444]">
              <Play className="h-3 w-3" />
              <span>Estimated: 6 min render time</span>
            </div>
            <div className="flex h-9 items-center gap-2 rounded-lg bg-[#10a37f] px-4 text-xs font-semibold text-white">
              <Sparkles className="h-3.5 w-3.5" />
              Generate Video
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
