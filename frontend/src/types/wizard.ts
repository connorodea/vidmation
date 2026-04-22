export type VideoStyle = "dark-finance" | "stock-footage" | "ai-cinematic" | "educational";
export type VideoNiche = "finance" | "tech" | "self-improvement" | "business" | "crypto" | "health";
export type VideoDuration = "short" | "medium" | "long";
export type VoiceId = "onyx" | "echo" | "nova" | "alloy";
export type MusicStyle = "ambient" | "cinematic" | "upbeat" | "dark" | "none";
export type CaptionStyle = "yellow-keyword" | "white-clean" | "bold-centered";
export type ColorGrade = "cinematic-warm" | "cool-moody" | "natural" | "custom";

export interface ScriptSection {
  id: string;
  heading: string;
  content: string;
  wordCount: number;
}

export interface WizardData {
  // Step 1: Topic & Style
  topic: string;
  style: VideoStyle | null;
  niche: VideoNiche | null;
  duration: VideoDuration;

  // Step 2: Script
  script: ScriptSection[];
  totalWordCount: number;
  estimatedDuration: number; // seconds

  // Step 3: Voice & Music
  voiceId: VoiceId;
  musicStyle: MusicStyle;
  musicVolume: number; // 0-100

  // Step 4: Visuals
  captionStyle: CaptionStyle;
  colorGrade: ColorGrade;
  kenBurns: boolean;
  filmGrain: boolean;
}

export interface WizardStepProps {
  data: WizardData;
  onUpdate: (updates: Partial<WizardData>) => void;
  onNext: () => void;
  onBack: () => void;
}

export type PipelineStage =
  | "script"
  | "voiceover"
  | "images"
  | "assembly"
  | "captions"
  | "export";

export interface PipelineProgress {
  currentStage: PipelineStage;
  completedStages: PipelineStage[];
  progressPct: number;
  estimatedTimeRemaining: number | null; // seconds
  videoId: string | null;
}

export const PIPELINE_STAGES: { id: PipelineStage; label: string }[] = [
  { id: "script", label: "Script" },
  { id: "voiceover", label: "Voiceover" },
  { id: "images", label: "Images" },
  { id: "assembly", label: "Assembly" },
  { id: "captions", label: "Captions" },
  { id: "export", label: "Export" },
];
