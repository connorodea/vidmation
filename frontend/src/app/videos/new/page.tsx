"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { WizardProgress } from "@/components/videos/wizard/wizard-progress";
import { StepTopic } from "@/components/videos/wizard/step-topic";
import { StepScript } from "@/components/videos/wizard/step-script";
import { StepVoice } from "@/components/videos/wizard/step-voice";
import { StepVisuals } from "@/components/videos/wizard/step-visuals";
import { StepReview } from "@/components/videos/wizard/step-review";
import { GenerationProgress } from "@/components/videos/generation-progress";
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
 * Generates demo script sections based on the user's topic.
 * In production this will call the backend AI endpoint.
 */
function generateDemoScript(topic: string, duration: string): ScriptSection[] {
  const topicSnippet =
    topic.length > 60 ? topic.slice(0, 60) + "..." : topic;

  const baseSections: Omit<ScriptSection, "id" | "wordCount">[] = [
    {
      heading: "Hook",
      content: `Did you know that most people completely misunderstand ${topicSnippet}? In this video, we're going to break down exactly what's really going on and why it matters more than ever.`,
    },
    {
      heading: "Context & Background",
      content: `To understand this topic, we need to go back to the fundamentals. ${topicSnippet} isn't just a passing trend -- it represents a fundamental shift in how we think about the world. Experts have been studying this phenomenon for years, and the data tells a compelling story that most mainstream coverage completely ignores.`,
    },
    {
      heading: "Key Insight #1",
      content: `The first thing most people get wrong is assuming this is straightforward. In reality, there are multiple layers at play. The research shows that when you dig beneath the surface of ${topicSnippet}, you find patterns that challenge conventional wisdom. Let's break down exactly what the data reveals.`,
    },
    {
      heading: "Key Insight #2",
      content: `Here's where it gets really interesting. The second major factor is something that rarely gets discussed in mainstream conversations. When you combine this with what we covered in the previous section, a much clearer picture emerges about ${topicSnippet} and its real-world implications.`,
    },
    {
      heading: "Practical Takeaway",
      content: `So what does this actually mean for you? Here are three concrete steps you can take today. First, re-evaluate your assumptions about ${topicSnippet}. Second, look at the data we've discussed and form your own conclusions. Third, share this knowledge with others who might benefit from a deeper understanding.`,
    },
    {
      heading: "Closing & Call to Action",
      content: `That's the real story behind ${topicSnippet}. If you found this valuable, make sure to subscribe and hit the bell icon so you never miss an update. Drop a comment below with your own perspective -- I read every single one. Until next time.`,
    },
  ];

  // Adjust number of sections based on duration
  let sections = baseSections;
  if (duration === "short") {
    sections = baseSections.slice(0, 3); // Hook, Context, CTA
    sections[2] = baseSections[baseSections.length - 1]; // Replace with CTA
  } else if (duration === "long") {
    // Add extra sections for longer content
    sections = [
      ...baseSections.slice(0, 4),
      {
        heading: "Deep Dive Analysis",
        content: `Let's take this even further. When you examine the historical context of ${topicSnippet}, you start to see recurring cycles that most analysts completely overlook. The data from the past decade reveals a pattern that, once you see it, you can never unsee. This has massive implications for what happens next.`,
      },
      {
        heading: "Expert Perspectives",
        content: `I spoke with three leading experts in this field, and their insights were eye-opening. The consensus is shifting rapidly, and what was considered fringe thinking just two years ago is now becoming mainstream. Here's what they had to say about ${topicSnippet} and where things are heading.`,
      },
      ...baseSections.slice(4),
    ];
  }

  return sections.map((s, i) => {
    const wordCount = s.content
      .trim()
      .split(/\s+/)
      .filter((w) => w.length > 0).length;
    return {
      ...s,
      id: `section-${i}`,
      wordCount,
    };
  });
}

export default function NewVideoPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [data, setData] = useState<WizardData>(INITIAL_DATA);
  const [isGenerating, setIsGenerating] = useState(false);
  const [showProgress, setShowProgress] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [isScriptLoading, setIsScriptLoading] = useState(false);

  const updateData = useCallback((updates: Partial<WizardData>) => {
    setData((prev) => ({ ...prev, ...updates }));
  }, []);

  const handleNext = useCallback(() => {
    if (currentStep === 1) {
      // Generate script when moving from step 1 to step 2
      setIsScriptLoading(true);
      setCurrentStep(2);

      // Simulate API delay for script generation
      setTimeout(() => {
        const script = generateDemoScript(data.topic, data.duration);
        const totalWordCount = script.reduce((acc, s) => acc + s.wordCount, 0);
        const estimatedDuration = Math.round((totalWordCount / 150) * 60);

        setData((prev) => ({
          ...prev,
          script,
          totalWordCount,
          estimatedDuration,
        }));
        setIsScriptLoading(false);
      }, 1500);

      return;
    }

    setCurrentStep((prev) => Math.min(prev + 1, 5));
  }, [currentStep, data.topic, data.duration]);

  const handleBack = useCallback(() => {
    setCurrentStep((prev) => Math.max(prev - 1, 1));
  }, []);

  const handleGenerate = useCallback(async () => {
    setIsGenerating(true);

    // Simulate API call to start generation
    setTimeout(() => {
      setJobId("demo-job-id");
      setShowProgress(true);
      setIsGenerating(false);
    }, 1000);
  }, []);

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
            />
          )}
        </div>
      </div>
    </div>
  );
}
