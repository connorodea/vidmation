"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Spinner } from "@/components/ui/spinner"
import { cn } from "@/lib/utils"
import { ArrowLeft, ArrowRight, Sparkles, Play, Check } from "lucide-react"

const steps = ["Topic", "Script", "Voice", "Visuals", "Generate"]

const visualStyles = [
  { id: "oil_painting", name: "Oil Painting", best: "History, finance" },
  { id: "cinematic_realism", name: "Cinematic", best: "Business, tech" },
  { id: "anime_illustration", name: "Anime", best: "Gaming, pop culture" },
  { id: "watercolor", name: "Watercolor", best: "Wellness, nature" },
  { id: "dark_noir", name: "Dark Noir", best: "Crime, mystery" },
  { id: "corporate_clean", name: "Corporate", best: "Business, SaaS" },
]

const voices = [
  { id: "onyx", name: "Onyx", description: "Deep, authoritative" },
  { id: "echo", name: "Echo", description: "Warm, friendly" },
  { id: "nova", name: "Nova", description: "Professional" },
  { id: "alloy", name: "Alloy", description: "Neutral, balanced" },
  { id: "shimmer", name: "Shimmer", description: "Energetic" },
]

const durations = [
  { id: "short", name: "Short", time: "2-4 min", cost: "$0.30" },
  { id: "medium", name: "Medium", time: "5-8 min", cost: "$0.60" },
  { id: "long", name: "Long", time: "10-15 min", cost: "$1.00" },
]

const channels = [
  { id: "ch_1", name: "Wealth Wisdom" },
  { id: "ch_2", name: "Tech Explained" },
]

const mockScript = {
  title: "The Hidden Psychology of Wealth Building",
  hook: "What if everything you believed about getting rich was completely wrong?",
  sections: [
    { heading: "The Wealth Mindset", narration: "Most people think wealth is about making more money. But studies show that 80% of millionaires are self-made..." },
    { heading: "The Compound Effect", narration: "Albert Einstein once called compound interest the eighth wonder of the world..." },
  ],
  outro: "If you found this valuable, subscribe and hit the bell icon.",
  estimated_duration: "8-10 min",
  total_words: 1200,
}

export default function CreateVideoPage() {
  const router = useRouter()
  const [currentStep, setCurrentStep] = useState(0)
  const [isGeneratingScript, setIsGeneratingScript] = useState(false)
  const [isGeneratingVideo, setIsGeneratingVideo] = useState(false)
  const [scriptGenerated, setScriptGenerated] = useState(false)
  
  const [topic, setTopic] = useState("")
  const [channelId, setChannelId] = useState("")
  const [duration, setDuration] = useState("medium")
  const [style, setStyle] = useState("oil_painting")
  const [voice, setVoice] = useState("onyx")
  const [script, setScript] = useState(mockScript)

  const handleGenerateScript = async () => {
    setIsGeneratingScript(true)
    await new Promise((resolve) => setTimeout(resolve, 2000))
    setScriptGenerated(true)
    setIsGeneratingScript(false)
  }

  const handleGenerateVideo = async () => {
    setIsGeneratingVideo(true)
    await new Promise((resolve) => setTimeout(resolve, 1500))
    router.push("/videos/vid_new?generating=true")
  }

  const canProceed = () => {
    switch (currentStep) {
      case 0: return topic.trim().length > 0 && channelId
      case 1: return scriptGenerated
      case 2: return voice
      case 3: return style
      case 4: return true
      default: return false
    }
  }

  return (
    <div className="min-h-screen p-8 lg:p-12">
      <div className="mx-auto max-w-2xl">
        {/* Header */}
        <button
          onClick={() => router.back()}
          className="mb-8 flex items-center gap-1.5 text-[13px] text-foreground/60 transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back
        </button>

        <h1 className="text-[32px] font-semibold tracking-tight">Create Video</h1>
        <p className="mt-1 text-[15px] text-foreground/60">
          Step {currentStep + 1} of {steps.length}: {steps[currentStep]}
        </p>

        {/* Progress */}
        <div className="mt-8 flex gap-1">
          {steps.map((_, i) => (
            <div
              key={i}
              className={cn(
                "h-1 flex-1 rounded-full transition-colors",
                i <= currentStep ? "bg-foreground" : "bg-foreground/10"
              )}
            />
          ))}
        </div>

        {/* Step Content */}
        <div className="mt-10">
          {/* Step 1: Topic */}
          {currentStep === 0 && (
            <div className="space-y-6">
              <div className="space-y-2">
                <Label className="text-[13px] font-medium">Topic</Label>
                <Textarea
                  placeholder="e.g., The psychology of wealth building"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  rows={3}
                  className="resize-none rounded-xl border-foreground/10 bg-transparent text-[15px] placeholder:text-foreground/30 focus-visible:border-foreground/30 focus-visible:ring-0"
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label className="text-[13px] font-medium">Channel</Label>
                  <Select value={channelId} onValueChange={setChannelId}>
                    <SelectTrigger className="h-10 rounded-xl border-foreground/10 bg-transparent text-[13px]">
                      <SelectValue placeholder="Select channel" />
                    </SelectTrigger>
                    <SelectContent>
                      {channels.map((ch) => (
                        <SelectItem key={ch.id} value={ch.id}>{ch.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label className="text-[13px] font-medium">Duration</Label>
                  <Select value={duration} onValueChange={setDuration}>
                    <SelectTrigger className="h-10 rounded-xl border-foreground/10 bg-transparent text-[13px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {durations.map((d) => (
                        <SelectItem key={d.id} value={d.id}>
                          {d.name} ({d.time}) - {d.cost}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Script */}
          {currentStep === 1 && (
            <div className="space-y-6">
              {!scriptGenerated ? (
                <div className="py-16 text-center">
                  <p className="text-[15px] text-foreground/60">Ready to generate script for:</p>
                  <p className="mt-2 text-[17px] font-medium">&quot;{topic}&quot;</p>
                  <Button
                    className="mt-8 h-10 gap-2 rounded-full bg-foreground px-6 text-[13px] font-medium text-background hover:bg-foreground/90"
                    onClick={handleGenerateScript}
                    disabled={isGeneratingScript}
                  >
                    {isGeneratingScript ? (
                      <><Spinner className="h-4 w-4" />Generating...</>
                    ) : (
                      <><Sparkles className="h-4 w-4" />Generate Script</>
                    )}
                  </Button>
                </div>
              ) : (
                <div className="space-y-5">
                  <div className="space-y-2">
                    <Label className="text-[13px] font-medium">Title</Label>
                    <Input
                      value={script.title}
                      onChange={(e) => setScript({ ...script, title: e.target.value })}
                      className="h-10 rounded-xl border-foreground/10 bg-transparent text-[15px] font-medium"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label className="text-[13px] font-medium">Hook</Label>
                    <Textarea
                      value={script.hook}
                      onChange={(e) => setScript({ ...script, hook: e.target.value })}
                      rows={2}
                      className="resize-none rounded-xl border-foreground/10 bg-transparent text-[14px]"
                    />
                  </div>

                  <div className="space-y-3">
                    <Label className="text-[13px] font-medium">Sections</Label>
                    {script.sections.map((section, index) => (
                      <div key={index} className="rounded-xl border border-foreground/10 p-4">
                        <Input
                          value={section.heading}
                          onChange={(e) => {
                            const newSections = [...script.sections]
                            newSections[index] = { ...section, heading: e.target.value }
                            setScript({ ...script, sections: newSections })
                          }}
                          className="mb-2 h-8 border-0 bg-transparent p-0 text-[14px] font-medium focus-visible:ring-0"
                        />
                        <Textarea
                          value={section.narration}
                          onChange={(e) => {
                            const newSections = [...script.sections]
                            newSections[index] = { ...section, narration: e.target.value }
                            setScript({ ...script, sections: newSections })
                          }}
                          rows={2}
                          className="resize-none border-0 bg-foreground/[0.02] p-2 text-[13px]"
                        />
                      </div>
                    ))}
                  </div>

                  <div className="flex items-center justify-between rounded-xl border border-foreground/10 p-4">
                    <span className="text-[13px] text-foreground/60">Estimated duration</span>
                    <span className="text-[13px] font-medium">{script.estimated_duration} · {script.total_words} words</span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 3: Voice */}
          {currentStep === 2 && (
            <div className="space-y-3">
              <RadioGroup value={voice} onValueChange={setVoice} className="space-y-2">
                {voices.map((v) => (
                  <Label
                    key={v.id}
                    htmlFor={`voice-${v.id}`}
                    className={cn(
                      "flex cursor-pointer items-center justify-between rounded-xl border p-4 transition-all",
                      voice === v.id ? "border-foreground bg-foreground/[0.02]" : "border-foreground/10 hover:border-foreground/20"
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <RadioGroupItem value={v.id} id={`voice-${v.id}`} className="sr-only" />
                      <div className={cn(
                        "flex h-5 w-5 items-center justify-center rounded-full border-2",
                        voice === v.id ? "border-foreground bg-foreground" : "border-foreground/20"
                      )}>
                        {voice === v.id && <Check className="h-3 w-3 text-background" />}
                      </div>
                      <div>
                        <p className="text-[14px] font-medium">{v.name}</p>
                        <p className="text-[12px] text-foreground/50">{v.description}</p>
                      </div>
                    </div>
                    <Button variant="ghost" size="sm" className="h-7 gap-1 rounded-full px-3 text-[12px]">
                      <Play className="h-3 w-3" />
                      Preview
                    </Button>
                  </Label>
                ))}
              </RadioGroup>
            </div>
          )}

          {/* Step 4: Visuals */}
          {currentStep === 3 && (
            <div className="space-y-3">
              <RadioGroup value={style} onValueChange={setStyle} className="grid gap-3 sm:grid-cols-2">
                {visualStyles.map((s) => (
                  <Label
                    key={s.id}
                    htmlFor={`style-${s.id}`}
                    className={cn(
                      "flex cursor-pointer flex-col rounded-xl border p-4 transition-all",
                      style === s.id ? "border-foreground bg-foreground/[0.02]" : "border-foreground/10 hover:border-foreground/20"
                    )}
                  >
                    <RadioGroupItem value={s.id} id={`style-${s.id}`} className="sr-only" />
                    <div className="flex items-center justify-between">
                      <span className="text-[14px] font-medium">{s.name}</span>
                      <div className={cn(
                        "flex h-5 w-5 items-center justify-center rounded-full border-2",
                        style === s.id ? "border-foreground bg-foreground" : "border-foreground/20"
                      )}>
                        {style === s.id && <Check className="h-3 w-3 text-background" />}
                      </div>
                    </div>
                    <span className="mt-1 text-[12px] text-foreground/50">Best for: {s.best}</span>
                  </Label>
                ))}
              </RadioGroup>
            </div>
          )}

          {/* Step 5: Generate */}
          {currentStep === 4 && (
            <div className="space-y-6">
              <div className="rounded-xl border border-foreground/10 divide-y divide-foreground/10">
                <div className="flex items-center justify-between p-4">
                  <span className="text-[13px] text-foreground/60">Topic</span>
                  <span className="text-[13px] font-medium">{topic}</span>
                </div>
                <div className="flex items-center justify-between p-4">
                  <span className="text-[13px] text-foreground/60">Duration</span>
                  <span className="text-[13px] font-medium">{durations.find(d => d.id === duration)?.name}</span>
                </div>
                <div className="flex items-center justify-between p-4">
                  <span className="text-[13px] text-foreground/60">Voice</span>
                  <span className="text-[13px] font-medium">{voices.find(v => v.id === voice)?.name}</span>
                </div>
                <div className="flex items-center justify-between p-4">
                  <span className="text-[13px] text-foreground/60">Visual Style</span>
                  <span className="text-[13px] font-medium">{visualStyles.find(s => s.id === style)?.name}</span>
                </div>
                <div className="flex items-center justify-between p-4">
                  <span className="text-[13px] text-foreground/60">Estimated Cost</span>
                  <span className="text-[13px] font-semibold">{durations.find(d => d.id === duration)?.cost}</span>
                </div>
              </div>

              <Button
                className="w-full h-12 rounded-full bg-foreground text-[14px] font-medium text-background hover:bg-foreground/90"
                onClick={handleGenerateVideo}
                disabled={isGeneratingVideo}
              >
                {isGeneratingVideo ? (
                  <><Spinner className="mr-2 h-4 w-4" />Creating Video...</>
                ) : (
                  "Generate Video"
                )}
              </Button>
            </div>
          )}
        </div>

        {/* Navigation */}
        <div className="mt-10 flex items-center justify-between">
          <Button
            variant="ghost"
            className="h-10 gap-1.5 rounded-full px-4 text-[13px]"
            onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
            disabled={currentStep === 0}
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back
          </Button>
          
          {currentStep < 4 && (
            <Button
              className="h-10 gap-1.5 rounded-full bg-foreground px-6 text-[13px] font-medium text-background hover:bg-foreground/90"
              onClick={() => setCurrentStep(Math.min(4, currentStep + 1))}
              disabled={!canProceed()}
            >
              Continue
              <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
