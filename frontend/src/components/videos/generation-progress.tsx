"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import {
  Check,
  Loader2,
  Clock,
  ExternalLink,
  AlertCircle,
  FileText,
  Volume2,
  Image,
  Layers,
  Type,
  Download,
} from "lucide-react";
import type { PipelineStage, PipelineProgress, PIPELINE_STAGES } from "@/types/wizard";

const STAGES: typeof PIPELINE_STAGES = [
  { id: "script", label: "Script" },
  { id: "voiceover", label: "Voiceover" },
  { id: "images", label: "Images" },
  { id: "assembly", label: "Assembly" },
  { id: "captions", label: "Captions" },
  { id: "export", label: "Export" },
];

const STAGE_ICONS: Record<PipelineStage, React.ReactNode> = {
  script: <FileText className="h-4 w-4" />,
  voiceover: <Volume2 className="h-4 w-4" />,
  images: <Image className="h-4 w-4" />,
  assembly: <Layers className="h-4 w-4" />,
  captions: <Type className="h-4 w-4" />,
  export: <Download className="h-4 w-4" />,
};

const STAGE_DESCRIPTIONS: Record<PipelineStage, string> = {
  script: "Generating and refining your script with AI...",
  voiceover: "Converting script to natural speech...",
  images: "Creating visuals for each scene...",
  assembly: "Compositing video timeline...",
  captions: "Generating and syncing captions...",
  export: "Rendering final video file...",
};

interface GenerationProgressProps {
  jobId: string | null;
  onViewVideo: (videoId: string) => void;
}

export function GenerationProgress({
  jobId,
  onViewVideo,
}: GenerationProgressProps) {
  const [progress, setProgress] = useState<PipelineProgress>({
    currentStage: "script",
    completedStages: [],
    progressPct: 0,
    estimatedTimeRemaining: null,
    videoId: null,
  });
  const [pollError, setPollError] = useState<string | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const consecutiveErrorsRef = useRef(0);

  const isComplete = progress.completedStages.length === STAGES.length;

  /**
   * Map the backend stage name to our local PipelineStage type.
   * The backend may use names like "generating_script", "voiceover", etc.
   */
  const mapStage = useCallback((backendStage: string): PipelineStage => {
    const mapping: Record<string, PipelineStage> = {
      script: "script",
      generating_script: "script",
      voiceover: "voiceover",
      generating_voiceover: "voiceover",
      images: "images",
      generating_images: "images",
      assembly: "assembly",
      assembling: "assembly",
      captions: "captions",
      generating_captions: "captions",
      export: "export",
      exporting: "export",
      rendering: "export",
    };
    return mapping[backendStage] ?? "script";
  }, []);

  /**
   * Derive which stages are completed based on the current stage index.
   */
  const deriveCompleted = useCallback(
    (currentStage: PipelineStage): PipelineStage[] => {
      const idx = STAGES.findIndex((s) => s.id === currentStage);
      if (idx <= 0) return [];
      return STAGES.slice(0, idx).map((s) => s.id);
    },
    []
  );

  // Poll the real API for job progress every 3 seconds
  useEffect(() => {
    if (!jobId || isComplete) return;

    const poll = async () => {
      try {
        const result = (await api.getJobProgress(jobId)) as {
          status: string;
          current_stage?: string;
          progress_pct?: number;
          stages?: { id: string; status: string }[];
          estimated_seconds_remaining?: number;
          video_id?: string;
        };

        consecutiveErrorsRef.current = 0;
        setPollError(null);

        // Check terminal states
        if (result.status === "completed" || result.status === "done") {
          setProgress({
            currentStage: "export",
            completedStages: STAGES.map((s) => s.id),
            progressPct: 100,
            estimatedTimeRemaining: 0,
            videoId: result.video_id ?? null,
          });

          // Stop polling
          if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
          }
          return;
        }

        if (result.status === "failed" || result.status === "error") {
          setPollError("Video generation failed. Please try again.");
          if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
          }
          return;
        }

        // Map backend response to our progress state
        const currentStage = result.current_stage
          ? mapStage(result.current_stage)
          : "script";

        // If the backend provides a stages array with statuses, use it
        let completedStages: PipelineStage[];
        if (result.stages && result.stages.length > 0) {
          completedStages = result.stages
            .filter(
              (s: { id: string; status: string }) =>
                s.status === "completed" || s.status === "done"
            )
            .map((s: { id: string; status: string }) => mapStage(s.id));
        } else {
          completedStages = deriveCompleted(currentStage);
        }

        setProgress({
          currentStage,
          completedStages,
          progressPct: Math.min(result.progress_pct ?? 0, 99),
          estimatedTimeRemaining:
            result.estimated_seconds_remaining ?? null,
          videoId: result.video_id ?? null,
        });
      } catch (err) {
        consecutiveErrorsRef.current += 1;
        // Only show error after 3 consecutive failures to avoid transient blips
        if (consecutiveErrorsRef.current >= 3) {
          setPollError(
            err instanceof Error
              ? err.message
              : "Lost connection to server. Retrying..."
          );
        }
      }
    };

    // Initial poll immediately
    poll();

    // Then poll every 3 seconds
    pollTimerRef.current = setInterval(poll, 3000);

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [jobId, isComplete, mapStage, deriveCompleted]);

  function formatTimeRemaining(seconds: number | null): string {
    if (seconds === null || seconds <= 0) return "Almost done...";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (mins === 0) return `${secs}s remaining`;
    return `${mins}m ${secs}s remaining`;
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center">
        <div
          className={cn(
            "inline-flex items-center justify-center h-16 w-16 rounded-2xl mb-5 transition-colors duration-500",
            isComplete
              ? "bg-[#10a37f]/15"
              : "bg-white/[0.04]"
          )}
        >
          {isComplete ? (
            <Check className="h-8 w-8 text-[#10a37f]" />
          ) : (
            <Loader2 className="h-8 w-8 text-[#10a37f] animate-spin" />
          )}
        </div>

        <h2 className="text-2xl font-semibold text-[#ececec] mb-2">
          {isComplete ? "Your video is ready" : "Generating your video"}
        </h2>
        <p className="text-sm text-[#666]">
          {isComplete
            ? "Your video has been successfully generated and is ready to preview."
            : "This may take a few minutes. You can leave this page and come back."}
        </p>
      </div>

      {/* Overall progress */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-[#ececec]">
            {isComplete ? "Complete" : `${progress.progressPct}%`}
          </span>
          <span className="text-xs text-[#666] flex items-center gap-1.5">
            <Clock className="h-3 w-3" />
            {isComplete
              ? "Done"
              : formatTimeRemaining(progress.estimatedTimeRemaining)}
          </span>
        </div>
        <Progress value={isComplete ? 100 : progress.progressPct} />
      </div>

      {/* Stage list */}
      <div className="rounded-2xl border border-white/[0.06] bg-[#1a1a1a] overflow-hidden divide-y divide-white/[0.04]">
        {STAGES.map((stage) => {
          const isStageCompleted = progress.completedStages.includes(stage.id);
          const isCurrent =
            progress.currentStage === stage.id && !isComplete;
          const isUpcoming = !isStageCompleted && !isCurrent;

          return (
            <div
              key={stage.id}
              className={cn(
                "flex items-center gap-4 px-5 py-4 transition-colors duration-300",
                isCurrent && "bg-[#10a37f]/[0.03]"
              )}
            >
              {/* Stage icon */}
              <div
                className={cn(
                  "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-all duration-300",
                  isStageCompleted &&
                    "bg-[#10a37f]/15 text-[#10a37f]",
                  isCurrent && "bg-[#10a37f]/10 text-[#10a37f]",
                  isUpcoming && "bg-white/[0.03] text-[#444]"
                )}
              >
                {isStageCompleted ? (
                  <Check className="h-4 w-4" />
                ) : isCurrent ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  STAGE_ICONS[stage.id]
                )}
              </div>

              {/* Stage info */}
              <div className="flex-1 min-w-0">
                <p
                  className={cn(
                    "text-sm font-medium transition-colors duration-300",
                    isStageCompleted && "text-[#10a37f]",
                    isCurrent && "text-[#ececec]",
                    isUpcoming && "text-[#666]"
                  )}
                >
                  {stage.label}
                </p>
                {isCurrent && (
                  <p className="text-xs text-[#666] mt-0.5">
                    {STAGE_DESCRIPTIONS[stage.id]}
                  </p>
                )}
              </div>

              {/* Stage status */}
              <div className="shrink-0">
                {isStageCompleted && (
                  <span className="text-[11px] text-[#10a37f] font-medium">
                    Done
                  </span>
                )}
                {isCurrent && (
                  <span className="text-[11px] text-[#666] font-medium">
                    In progress
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Poll error */}
      {pollError && !isComplete && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-5 py-4 flex items-center gap-3">
          <AlertCircle className="h-4 w-4 text-red-400 shrink-0" />
          <p className="text-sm text-red-400">{pollError}</p>
        </div>
      )}

      {/* View Video button (when complete) */}
      {isComplete && progress.videoId && (
        <div className="flex justify-center pt-2">
          <Button
            size="lg"
            onClick={() => onViewVideo(progress.videoId!)}
            className="min-w-[200px] gap-2 text-base h-13 px-8"
          >
            View Video
            <ExternalLink className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
