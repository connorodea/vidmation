"use client";

import { useState, useMemo, useRef, useCallback } from "react";
import { cn } from "@/lib/utils";
import { TimelineRuler } from "./timeline-ruler";
import { TimelineTrack, type TrackBlock } from "./timeline-track";

/* -------------------------------------------------------------------------- */
/*  Types                                                                     */
/* -------------------------------------------------------------------------- */

export interface TimelineSection {
  heading: string;
  start: number;
  end: number;
  mediaCount: number;
}

export interface TimelineCaption {
  text: string;
  start: number;
  end: number;
}

export interface VideoTimelineProps {
  sections: TimelineSection[];
  totalDuration: number;
  captions: TimelineCaption[];
  hasMusic: boolean;
  onSectionClick?: (index: number) => void;
}

/* -------------------------------------------------------------------------- */
/*  Color palette for sections                                                */
/* -------------------------------------------------------------------------- */

const SECTION_COLORS = [
  { bg: "rgba(99,102,241,0.35)", border: "rgba(99,102,241,0.5)" },   // indigo
  { bg: "rgba(16,163,127,0.35)", border: "rgba(16,163,127,0.5)" },   // green (accent)
  { bg: "rgba(245,158,11,0.35)", border: "rgba(245,158,11,0.5)" },   // amber
  { bg: "rgba(236,72,153,0.35)", border: "rgba(236,72,153,0.5)" },   // pink
  { bg: "rgba(59,130,246,0.35)", border: "rgba(59,130,246,0.5)" },   // blue
  { bg: "rgba(168,85,247,0.35)", border: "rgba(168,85,247,0.5)" },   // purple
  { bg: "rgba(20,184,166,0.35)", border: "rgba(20,184,166,0.5)" },   // teal
  { bg: "rgba(251,146,60,0.35)", border: "rgba(251,146,60,0.5)" },   // orange
];

/* -------------------------------------------------------------------------- */
/*  Icons                                                                     */
/* -------------------------------------------------------------------------- */

function VideoIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="23 7 16 12 23 17 23 7" />
      <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
    </svg>
  );
}

function AudioIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  );
}

function MusicIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 18V5l12-2v13" />
      <circle cx="6" cy="18" r="3" />
      <circle cx="18" cy="16" r="3" />
    </svg>
  );
}

function CaptionIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="20" height="18" rx="2" />
      <path d="M7 15h4" />
      <path d="M13 15h4" />
      <path d="M7 11h10" />
    </svg>
  );
}

function ZoomInIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
      <line x1="11" y1="8" x2="11" y2="14" />
      <line x1="8" y1="11" x2="14" y2="11" />
    </svg>
  );
}

function ZoomOutIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
      <line x1="8" y1="11" x2="14" y2="11" />
    </svg>
  );
}

function ZoomResetIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

/* -------------------------------------------------------------------------- */
/*  Helper                                                                    */
/* -------------------------------------------------------------------------- */

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

function truncateCaption(text: string, maxLen: number = 24): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen - 1) + "\u2026";
}

/* -------------------------------------------------------------------------- */
/*  Component                                                                 */
/* -------------------------------------------------------------------------- */

export function VideoTimeline({
  sections,
  totalDuration,
  captions,
  hasMusic,
  onSectionClick,
}: VideoTimelineProps) {
  const [zoom, setZoom] = useState(1);
  const [playbackPosition, setPlaybackPosition] = useState(0);
  const trackAreaRef = useRef<HTMLDivElement>(null);

  const handleZoomIn = useCallback(() => {
    setZoom((z) => Math.min(z + 0.5, 4));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoom((z) => Math.max(z - 0.5, 0.5));
  }, []);

  const handleZoomReset = useCallback(() => {
    setZoom(1);
  }, []);

  // Click on the ruler/track area to set playback position
  const handleTimelineClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const container = trackAreaRef.current;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      // Account for the 96px label column
      const labelWidth = 96;
      const trackWidth = rect.width - labelWidth;
      const clickX = e.clientX - rect.left - labelWidth;
      if (clickX < 0) return;
      const ratio = Math.max(0, Math.min(1, clickX / trackWidth));
      setPlaybackPosition(ratio * totalDuration);
    },
    [totalDuration]
  );

  /* -- Build track blocks -------------------------------------------------- */

  const videoBlocks: TrackBlock[] = useMemo(
    () =>
      sections.map((section, i) => {
        const colors = SECTION_COLORS[i % SECTION_COLORS.length];
        return {
          id: `section-${i}`,
          label: section.heading,
          detail: `${section.mediaCount} clip${section.mediaCount !== 1 ? "s" : ""}`,
          start: section.start,
          end: section.end,
          color: colors.bg,
          borderColor: colors.border,
          onClick: onSectionClick ? () => onSectionClick(i) : undefined,
        };
      }),
    [sections, onSectionClick]
  );

  const audioBlocks: TrackBlock[] = useMemo(
    () =>
      sections.map((section, i) => ({
        id: `audio-${i}`,
        label: "Voiceover",
        detail: `${formatTime(section.end - section.start)}`,
        start: section.start,
        end: section.end,
        color: "rgba(59,130,246,0.25)",
        borderColor: "rgba(59,130,246,0.35)",
      })),
    [sections]
  );

  const musicBlocks: TrackBlock[] = useMemo(() => {
    if (!hasMusic) return [];
    return [
      {
        id: "music-0",
        label: "Background Music",
        detail: formatTime(totalDuration),
        start: 0,
        end: totalDuration,
        color: "rgba(168,85,247,0.2)",
        borderColor: "rgba(168,85,247,0.3)",
      },
    ];
  }, [hasMusic, totalDuration]);

  const captionBlocks: TrackBlock[] = useMemo(
    () =>
      captions.map((cap, i) => ({
        id: `caption-${i}`,
        label: truncateCaption(cap.text),
        detail: cap.text,
        start: cap.start,
        end: cap.end,
        color: "rgba(255,255,255,0.08)",
        borderColor: "rgba(255,255,255,0.12)",
      })),
    [captions]
  );

  const playbackLeft = totalDuration > 0 ? (playbackPosition / totalDuration) * 100 : 0;

  return (
    <div className="rounded-2xl border border-white/[0.08] bg-[#111111] overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.06] bg-zinc-950/60">
        <div className="flex items-center gap-2">
          <h3 className="text-xs font-medium uppercase tracking-wider text-[#666]">
            Timeline
          </h3>
          <span className="text-[10px] tabular-nums text-[#555]">
            {formatTime(totalDuration)}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={handleZoomOut}
            className="p-1.5 rounded-lg text-[#666] hover:text-[#ececec] hover:bg-white/[0.06] transition-colors duration-100"
            title="Zoom out"
          >
            <ZoomOutIcon />
          </button>
          <button
            type="button"
            onClick={handleZoomReset}
            className="px-2 py-1 rounded-lg text-[10px] tabular-nums text-[#666] hover:text-[#ececec] hover:bg-white/[0.06] transition-colors duration-100"
            title="Reset zoom"
          >
            {Math.round(zoom * 100)}%
          </button>
          <button
            type="button"
            onClick={handleZoomIn}
            className="p-1.5 rounded-lg text-[#666] hover:text-[#ececec] hover:bg-white/[0.06] transition-colors duration-100"
            title="Zoom in"
          >
            <ZoomInIcon />
          </button>
        </div>
      </div>

      {/* Scrollable timeline area */}
      <div className="overflow-x-auto">
        <div
          ref={trackAreaRef}
          className="relative cursor-crosshair"
          style={{ minWidth: `${zoom * 100}%` }}
          onClick={handleTimelineClick}
        >
          {/* Ruler */}
          <div className="flex">
            <div className="w-24 shrink-0 border-r border-white/[0.06] bg-zinc-950/50" />
            <div className="flex-1 relative">
              <TimelineRuler
                totalDuration={totalDuration}
                zoom={zoom}
              />
            </div>
          </div>

          {/* Tracks */}
          <div className="divide-y divide-white/[0.04]">
            <TimelineTrack
              label="Video"
              icon={<VideoIcon />}
              blocks={videoBlocks}
              totalDuration={totalDuration}
            />
            <TimelineTrack
              label="Audio"
              icon={<AudioIcon />}
              blocks={audioBlocks}
              totalDuration={totalDuration}
            />
            {hasMusic && (
              <TimelineTrack
                label="Music"
                icon={<MusicIcon />}
                blocks={musicBlocks}
                totalDuration={totalDuration}
              />
            )}
            {captions.length > 0 && (
              <TimelineTrack
                label="Captions"
                icon={<CaptionIcon />}
                blocks={captionBlocks}
                totalDuration={totalDuration}
              />
            )}
          </div>

          {/* Playback position indicator */}
          <div
            className="absolute top-0 bottom-0 w-px bg-red-500 z-20 pointer-events-none"
            style={{ left: `calc(96px + (100% - 96px) * ${playbackLeft / 100})` }}
          >
            {/* Playhead triangle */}
            <div className="absolute -top-0 left-1/2 -translate-x-1/2 w-0 h-0 border-l-[5px] border-l-transparent border-r-[5px] border-r-transparent border-t-[6px] border-t-red-500" />
          </div>
        </div>
      </div>

      {/* Footer with playback time */}
      <div className="flex items-center justify-between px-4 py-2 border-t border-white/[0.06] bg-zinc-950/60">
        <span className="text-[10px] tabular-nums text-[#555]">
          {formatTime(playbackPosition)}
        </span>
        <span className="text-[10px] text-[#555]">
          {sections.length} section{sections.length !== 1 ? "s" : ""}
          {captions.length > 0 && ` \u00B7 ${captions.length} caption${captions.length !== 1 ? "s" : ""}`}
          {hasMusic && " \u00B7 Music"}
        </span>
      </div>
    </div>
  );
}
