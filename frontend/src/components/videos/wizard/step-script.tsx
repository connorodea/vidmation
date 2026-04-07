"use client";

import { useCallback } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  ArrowLeft,
  ArrowRight,
  RotateCcw,
  Clock,
  FileText,
  GripVertical,
} from "lucide-react";
import type { WizardStepProps, ScriptSection } from "@/types/wizard";

function countWords(text: string): number {
  return text
    .trim()
    .split(/\s+/)
    .filter((w) => w.length > 0).length;
}

function estimateDuration(wordCount: number): number {
  // Average speaking rate: ~150 words per minute
  return Math.round((wordCount / 150) * 60);
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins === 0) return `${secs}s`;
  return `${mins}m ${secs}s`;
}

export function StepScript({ data, onUpdate, onNext, onBack }: WizardStepProps) {
  const updateSection = useCallback(
    (sectionId: string, field: "heading" | "content", value: string) => {
      const updated = data.script.map((s) => {
        if (s.id !== sectionId) return s;
        const newSection = { ...s, [field]: value };
        if (field === "content") {
          newSection.wordCount = countWords(value);
        }
        return newSection;
      });

      const totalWordCount = updated.reduce((acc, s) => acc + s.wordCount, 0);
      const estimatedDurationValue = estimateDuration(totalWordCount);

      onUpdate({
        script: updated,
        totalWordCount,
        estimatedDuration: estimatedDurationValue,
      });
    },
    [data.script, onUpdate]
  );

  const regenerateSection = useCallback(
    (sectionId: string) => {
      // Simulate regeneration with placeholder content
      const section = data.script.find((s) => s.id === sectionId);
      if (!section) return;

      const newContent =
        "Regenerated content will appear here when connected to the AI backend. " +
        "This section covers " +
        section.heading.toLowerCase() +
        " in detail with fresh perspective and updated insights.";

      updateSection(sectionId, "content", newContent);
    },
    [data.script, updateSection]
  );

  const canProceed = data.script.length > 0 && data.totalWordCount > 20;

  return (
    <div className="space-y-8">
      {/* Header with stats */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-semibold text-[#ececec] mb-1">
            Review Your Script
          </h2>
          <p className="text-sm text-[#666]">
            Edit any section or regenerate parts you want to change.
          </p>
        </div>

        <div className="flex items-center gap-5 shrink-0">
          <div className="flex items-center gap-2 text-xs text-[#999]">
            <FileText className="h-3.5 w-3.5" />
            <span>
              {data.totalWordCount.toLocaleString()} words
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-[#999]">
            <Clock className="h-3.5 w-3.5" />
            <span>~{formatTime(data.estimatedDuration)}</span>
          </div>
        </div>
      </div>

      {/* Script sections */}
      <div className="space-y-4">
        {data.script.map((section, index) => (
          <ScriptSectionEditor
            key={section.id}
            section={section}
            index={index}
            onUpdateHeading={(value) =>
              updateSection(section.id, "heading", value)
            }
            onUpdateContent={(value) =>
              updateSection(section.id, "content", value)
            }
            onRegenerate={() => regenerateSection(section.id)}
          />
        ))}
      </div>

      {/* Empty state */}
      {data.script.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 rounded-2xl border border-dashed border-white/[0.06]">
          <FileText className="h-10 w-10 text-[#666] mb-4" />
          <p className="text-sm text-[#666] mb-1">No script generated yet</p>
          <p className="text-xs text-[#666]">
            Go back and provide a topic to generate a script.
          </p>
        </div>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between pt-2">
        <Button variant="ghost" onClick={onBack} className="gap-2">
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>

        <Button
          size="lg"
          onClick={onNext}
          disabled={!canProceed}
          className="min-w-[160px] gap-2"
        >
          Voice & Music
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

function ScriptSectionEditor({
  section,
  index,
  onUpdateHeading,
  onUpdateContent,
  onRegenerate,
}: {
  section: ScriptSection;
  index: number;
  onUpdateHeading: (value: string) => void;
  onUpdateContent: (value: string) => void;
  onRegenerate: () => void;
}) {
  return (
    <div
      className={cn(
        "group rounded-2xl border border-white/[0.06] bg-[#1a1a1a] overflow-hidden",
        "transition-all duration-200 hover:border-white/[0.1]"
      )}
    >
      {/* Section header */}
      <div className="flex items-center gap-3 px-5 py-3 border-b border-white/[0.04] bg-white/[0.01]">
        <GripVertical className="h-4 w-4 text-[#444] shrink-0" aria-hidden="true" />

        <span className="text-[11px] font-medium text-[#666] shrink-0 uppercase tracking-wider">
          Section {index + 1}
        </span>

        <Input
          value={section.heading}
          onChange={(e) => onUpdateHeading(e.target.value)}
          className="flex-1 h-8 text-sm font-medium bg-transparent border-none px-2 focus-visible:ring-0 focus-visible:border-none text-[#ececec]"
          aria-label={`Section ${index + 1} heading`}
        />

        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[11px] text-[#666]">
            {section.wordCount} words
          </span>

          <button
            type="button"
            onClick={onRegenerate}
            className={cn(
              "flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[11px] font-medium",
              "text-[#666] hover:text-[#10a37f] hover:bg-[#10a37f]/10",
              "transition-all duration-150",
              "opacity-0 group-hover:opacity-100 focus-visible:opacity-100",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#10a37f]"
            )}
            aria-label={`Regenerate section ${index + 1}`}
          >
            <RotateCcw className="h-3 w-3" />
            Regenerate
          </button>
        </div>
      </div>

      {/* Section content */}
      <div className="p-5">
        <Textarea
          value={section.content}
          onChange={(e) => onUpdateContent(e.target.value)}
          className="min-h-[100px] text-sm leading-relaxed bg-transparent border-none px-0 py-0 focus-visible:ring-0 resize-y text-[#ccc]"
          aria-label={`Section ${index + 1} content`}
        />
      </div>
    </div>
  );
}
