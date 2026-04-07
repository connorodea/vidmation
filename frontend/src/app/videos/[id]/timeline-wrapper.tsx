"use client";

import { useMemo, useState } from "react";
import {
  VideoTimeline,
  type TimelineSection,
  type TimelineCaption,
} from "@/components/editor/video-timeline";

interface VideoTimelineWrapperProps {
  scriptJson: Record<string, unknown> | null;
  durationSeconds: number | null;
}

/**
 * Extracts timeline data from a video's script_json.
 *
 * The script JSON may have different shapes depending on the generation
 * pipeline. This wrapper tries common structures:
 *
 *  - { sections: [{ heading, script, search_terms, ... }] }
 *  - { segments: [{ title, text, duration, ... }] }
 *
 * When no script is available it renders a placeholder message.
 */
export function VideoTimelineWrapper({
  scriptJson,
  durationSeconds,
}: VideoTimelineWrapperProps) {
  const [selectedSection, setSelectedSection] = useState<number | null>(null);

  const { sections, captions, totalDuration, hasMusic } = useMemo(() => {
    if (!scriptJson) {
      return { sections: [], captions: [], totalDuration: 0, hasMusic: false };
    }

    const script = scriptJson as Record<string, unknown>;
    const rawSections: TimelineSection[] = [];
    const rawCaptions: TimelineCaption[] = [];

    // Try to extract sections from common script shapes
    const sectionArray =
      (script.sections as unknown[]) ||
      (script.segments as unknown[]) ||
      (script.parts as unknown[]) ||
      [];

    const duration = durationSeconds || 0;

    if (Array.isArray(sectionArray) && sectionArray.length > 0) {
      // Compute equal distribution if no explicit timing
      const sectionCount = sectionArray.length;
      const sectionDuration = duration > 0 ? duration / sectionCount : 30;

      sectionArray.forEach((raw: unknown, i: number) => {
        const s = raw as Record<string, unknown>;
        const heading =
          (s.heading as string) ||
          (s.title as string) ||
          (s.name as string) ||
          `Section ${i + 1}`;

        const start =
          typeof s.start === "number"
            ? s.start
            : i * sectionDuration;
        const end =
          typeof s.end === "number"
            ? s.end
            : (i + 1) * sectionDuration;

        // Count media items (images, clips, search_terms)
        let mediaCount = 0;
        if (Array.isArray(s.search_terms)) mediaCount = s.search_terms.length;
        else if (Array.isArray(s.images)) mediaCount = s.images.length;
        else if (Array.isArray(s.clips)) mediaCount = s.clips.length;
        else if (typeof s.media_count === "number") mediaCount = s.media_count;
        else mediaCount = 1;

        rawSections.push({ heading, start, end, mediaCount });

        // Generate caption blocks from the section's script/text
        const text =
          (s.script as string) || (s.text as string) || (s.narration as string);
        if (text) {
          // Split into ~5-second caption chunks
          const sectionLen = end - start;
          const words = text.split(/\s+/);
          const chunkSize = Math.max(6, Math.ceil(words.length / Math.ceil(sectionLen / 5)));
          let wordIdx = 0;
          let captionStart = start;
          const captionDuration = sectionLen / Math.ceil(words.length / chunkSize);

          while (wordIdx < words.length) {
            const chunk = words.slice(wordIdx, wordIdx + chunkSize).join(" ");
            const captionEnd = Math.min(captionStart + captionDuration, end);
            rawCaptions.push({
              text: chunk,
              start: captionStart,
              end: captionEnd,
            });
            captionStart = captionEnd;
            wordIdx += chunkSize;
          }
        }
      });
    }

    // Determine total duration
    const computedDuration =
      duration > 0
        ? duration
        : rawSections.length > 0
          ? rawSections[rawSections.length - 1].end
          : 0;

    // Check for background music
    const hasMusic =
      !!script.music ||
      !!script.background_music ||
      !!script.music_url ||
      false;

    return {
      sections: rawSections,
      captions: rawCaptions,
      totalDuration: computedDuration,
      hasMusic,
    };
  }, [scriptJson, durationSeconds]);

  if (sections.length === 0) {
    return (
      <div className="rounded-2xl border border-white/[0.08] bg-[#111111] px-6 py-8 text-center">
        <p className="text-sm text-[#555]">
          No timeline data available. Generate a script to see the video
          timeline.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <VideoTimeline
        sections={sections}
        totalDuration={totalDuration}
        captions={captions}
        hasMusic={hasMusic}
        onSectionClick={(index) => setSelectedSection(index)}
      />

      {/* Selected section detail */}
      {selectedSection !== null && sections[selectedSection] && (
        <div className="rounded-xl border border-[#10a37f]/20 bg-[#10a37f]/5 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xs font-medium text-[#10a37f]">
              Section {selectedSection + 1}
            </span>
            <span className="text-xs text-[#999]">
              {sections[selectedSection].heading}
            </span>
          </div>
          <button
            type="button"
            onClick={() => setSelectedSection(null)}
            className="text-[#666] hover:text-[#999] transition-colors duration-100"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 14 14"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M10 4L4 10M4 4l6 6" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}
