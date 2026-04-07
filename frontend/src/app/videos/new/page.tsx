"use client";

import { useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { WizardProgress } from "@/components/videos/wizard/wizard-progress";
import { StepTopic } from "@/components/videos/wizard/step-topic";
import { StepScript } from "@/components/videos/wizard/step-script";
import { StepVoice } from "@/components/videos/wizard/step-voice";
import { StepVisuals } from "@/components/videos/wizard/step-visuals";
import { StepReview } from "@/components/videos/wizard/step-review";
import { GenerationProgress } from "@/components/videos/generation-progress";
import { api } from "@/lib/api";
import type { WizardData, ScriptSection } from "@/types/wizard";

const INITIAL_DATA: WizardData = {
  topic: "",
  style: null,
  niche: null,
  duration: "medium",
  script: [],
  totalWordCount: 0,
  estimatedDuration: 0,
  voiceId: "onyx",
  musicStyle: "cinematic",
  musicVolume: 30,
  captionStyle: "yellow-keyword",
  colorGrade: "cinematic-warm",
  kenBurns: true,
  filmGrain: false,
};

/**
 * Ensures the user has at least one channel. Creates "My Channel" if none exist.
 * Returns the channel name to use for video generation.
 */
async function ensureChannel(): Promise<string> {
  try {
    const channels = (await api.getChannels()) as { id: string; name: string }[];
    if (channels && channels.length > 0) {
      return channels[0].name;
    }
  } catch {
    // Channels endpoint may return 404 or empty — fall through to create
  }

  try {
    const created = (await api.createChannel({ name: "My Channel" })) as {
      id: string;
      name: string;
    };
    return created.name;
  } catch {
    // If creation also fails, return a sensible default
    return "My Channel";
  }
}

export default function NewVideoPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [data, setData] = useState<WizardData>(INITIAL_DATA);
  const [isGenerating, setIsGenerating] = useState(false);
  const [showProgress, setShowProgress] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [isScriptLoading, setIsScriptLoading] = useState(false);
  const [scriptError, setScriptError] = useState<string | null>(null);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const channelNameRef = useRef<string | null>(null);

  const updateData = useCallback((updates: Partial<WizardData>) => {
    setData((prev) => ({ ...prev, ...updates }));
  }, []);

  const handleNext = useCallback(async () => {
    if (currentStep === 1) {
      // Generate script via real backend API
      setIsScriptLoading(true);
      setScriptError(null);
      setCurrentStep(2);

      try {
        const result = await api.generateScript({
          topic: data.topic,
          style: data.style ?? "dark-finance",
          niche: data.niche ?? "finance",
          duration: data.duration,
        });

        // Build script sections from the API response.
        // The hook and outro come as separate fields; sections[] holds the body.
        const allSections: Omit<ScriptSection, "id" | "wordCount">[] = [];

        if (result.hook) {
          allSections.push({ heading: "Hook", content: result.hook });
        }
        if (result.sections) {
          for (const s of result.sections) {
            allSections.push({ heading: s.heading, content: s.content });
          }
        }
        if (result.outro) {
          allSections.push({ heading: "Outro", content: result.outro });
        }

        const script: ScriptSection[] = allSections.map((s, i) => {
          const wordCount = s.content
            .trim()
            .split(/\s+/)
            .filter((w: string) => w.length > 0).length;
          return { ...s, id: `section-${i}`, wordCount };
        });

        const totalWordCount =
          result.total_words ??
          script.reduce((acc, s) => acc + s.wordCount, 0);
        const estimatedDuration =
          result.estimated_duration_seconds ??
          Math.round((totalWordCount / 150) * 60);

        setData((prev) => ({
          ...prev,
          script,
          totalWordCount,
          estimatedDuration,
        }));
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to generate script";
        setScriptError(message);
      } finally {
        setIsScriptLoading(false);
      }

      return;
    }

    setCurrentStep((prev) => Math.min(prev + 1, 5));
  }, [currentStep, data.topic, data.duration, data.style, data.niche]);

  const handleBack = useCallback(() => {
    setScriptError(null);
    setGenerateError(null);
    setCurrentStep((prev) => Math.max(prev - 1, 1));
  }, []);

  const handleGenerate = useCallback(async () => {
    setIsGenerating(true);
    setGenerateError(null);

    try {
      // Ensure the user has a channel before generating
      if (!channelNameRef.current) {
        channelNameRef.current = await ensureChannel();
      }

      const result = await api.generateVideo({
        topic: data.topic,
        channel_name: channelNameRef.current,
        style: data.style ?? "dark-finance",
        format: "landscape",
        voice: data.voiceId,
        music_style: data.musicStyle,
        caption_style: data.captionStyle,
        duration: data.duration,
      });

      setJobId(result.job_id);
      setShowProgress(true);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to start video generation";
      setGenerateError(message);
    } finally {
      setIsGenerating(false);
    }
  }, [data]);

  const handleViewVideo = useCallback(
    (videoId: string) => {
      router.push(`/videos/${videoId}`);
    },
    [router]
  );

  // Show generation progress screen
  if (showProgress) {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-12">
        <GenerationProgress jobId={jobId} onViewVideo={handleViewVideo} />
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-4rem)] flex flex-col px-4 py-8">
      {/* Progress bar */}
      <div className="w-full max-w-3xl mx-auto mb-10">
        <WizardProgress currentStep={currentStep} />
      </div>

      {/* Step content */}
      <div className="w-full max-w-3xl mx-auto flex-1">
        <div
          className={cn(
            "transition-opacity duration-300",
            isScriptLoading && currentStep === 2 ? "opacity-50" : "opacity-100"
          )}
        >
          {currentStep === 1 && (
            <StepTopic
              data={data}
              onUpdate={updateData}
              onNext={handleNext}
              onBack={handleBack}
            />
          )}

          {currentStep === 2 && (
            <>
              {isScriptLoading ? (
                <div className="flex flex-col items-center justify-center py-24">
                  <div className="relative mb-6">
                    <div className="h-14 w-14 rounded-2xl bg-[#10a37f]/10 flex items-center justify-center">
                      <div className="h-6 w-6 border-2 border-[#10a37f]/30 border-t-[#10a37f] rounded-full animate-spin" />
                    </div>
                  </div>
                  <h3 className="text-lg font-semibold text-[#ececec] mb-2">
                    Generating your script
                  </h3>
                  <p className="text-sm text-[#666] text-center max-w-sm">
                    Our AI is crafting a compelling script based on your topic
                    and preferences...
                  </p>
                </div>
              ) : scriptError ? (
                <div className="flex flex-col items-center justify-center py-24">
                  <div className="h-14 w-14 rounded-2xl bg-red-500/10 flex items-center justify-center mb-6">
                    <span className="text-red-400 text-2xl">!</span>
                  </div>
                  <h3 className="text-lg font-semibold text-[#ececec] mb-2">
                    Script generation failed
                  </h3>
                  <p className="text-sm text-red-400 text-center max-w-sm mb-6">
                    {scriptError}
                  </p>
                  <div className="flex gap-3">
                    <Button variant="ghost" onClick={handleBack}>
                      Go Back
                    </Button>
                    <Button onClick={handleNext}>
                      Retry
                    </Button>
                  </div>
                </div>
              ) : (
                <StepScript
                  data={data}
                  onUpdate={updateData}
                  onNext={handleNext}
                  onBack={handleBack}
                />
              )}
            </>
          )}

          {currentStep === 3 && (
            <StepVoice
              data={data}
              onUpdate={updateData}
              onNext={handleNext}
              onBack={handleBack}
            />
          )}

          {currentStep === 4 && (
            <StepVisuals
              data={data}
              onUpdate={updateData}
              onNext={handleNext}
              onBack={handleBack}
            />
          )}

          {currentStep === 5 && (
            <StepReview
              data={data}
              onUpdate={updateData}
              onNext={handleNext}
              onBack={handleBack}
              onGenerate={handleGenerate}
              isGenerating={isGenerating}
              generateError={generateError}
            />
          )}
        </div>
      </div>
    </div>
  );
}
