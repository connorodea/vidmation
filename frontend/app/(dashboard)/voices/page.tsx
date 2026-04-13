"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Plus, Play, Pause, Upload, Star } from "lucide-react"
import { cn } from "@/lib/utils"

const standardVoices = [
  { id: "onyx", name: "Onyx", description: "Deep, authoritative", usage: 156, favorite: true },
  { id: "echo", name: "Echo", description: "Warm, friendly", usage: 89, favorite: false },
  { id: "nova", name: "Nova", description: "Professional", usage: 124, favorite: true },
  { id: "alloy", name: "Alloy", description: "Neutral, balanced", usage: 67, favorite: false },
  { id: "shimmer", name: "Shimmer", description: "Bright, energetic", usage: 45, favorite: false },
]

const clonedVoices = [
  { id: "custom_1", name: "My Voice", usage: 12 },
]

export default function VoicesPage() {
  const [playingVoice, setPlayingVoice] = useState<string | null>(null)
  const [isCloneOpen, setIsCloneOpen] = useState(false)
  const [cloneName, setCloneName] = useState("")
  const [cloneProvider, setCloneProvider] = useState("")

  const handlePlayVoice = (voiceId: string) => {
    if (playingVoice === voiceId) {
      setPlayingVoice(null)
    } else {
      setPlayingVoice(voiceId)
      setTimeout(() => setPlayingVoice(null), 3000)
    }
  }

  return (
    <div className="p-8 lg:p-12">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-[32px] font-semibold tracking-tight">Voices</h1>
          <p className="mt-1 text-[15px] text-foreground/60">
            {standardVoices.length + clonedVoices.length} voices available
          </p>
        </div>
        <Dialog open={isCloneOpen} onOpenChange={setIsCloneOpen}>
          <DialogTrigger asChild>
            <Button className="h-9 gap-1.5 rounded-full bg-foreground px-4 text-[13px] font-medium text-background hover:bg-foreground/90">
              <Plus className="h-3.5 w-3.5" />
              Clone Voice
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="text-[17px]">Clone Your Voice</DialogTitle>
              <DialogDescription className="text-[13px] text-foreground/60">
                Upload an audio sample to create a custom AI voice.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label className="text-[13px]">Name</Label>
                <Input
                  placeholder="e.g., My Voice"
                  value={cloneName}
                  onChange={(e) => setCloneName(e.target.value)}
                  className="h-10 rounded-xl border-foreground/10"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-[13px]">Provider</Label>
                <Select value={cloneProvider} onValueChange={setCloneProvider}>
                  <SelectTrigger className="h-10 rounded-xl border-foreground/10">
                    <SelectValue placeholder="Select provider" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="elevenlabs">ElevenLabs</SelectItem>
                    <SelectItem value="replicate">Replicate</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-[13px]">Audio Sample</Label>
                <div className="flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-foreground/20 p-8 transition-colors hover:border-foreground/40">
                  <Upload className="h-6 w-6 text-foreground/40" />
                  <p className="mt-2 text-[13px] font-medium">Upload audio file</p>
                  <p className="text-[11px] text-foreground/50">MP3 or WAV, 30s to 5 min</p>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="ghost" onClick={() => setIsCloneOpen(false)} className="h-9 rounded-full text-[13px]">
                Cancel
              </Button>
              <Button
                onClick={() => setIsCloneOpen(false)}
                disabled={!cloneName || !cloneProvider}
                className="h-9 rounded-full bg-foreground px-5 text-[13px] text-background"
              >
                Clone
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Cloned Voices */}
      {clonedVoices.length > 0 && (
        <div className="mt-10">
          <h2 className="text-[15px] font-semibold">Your Voices</h2>
          <div className="mt-4 rounded-xl border border-foreground/10">
            {clonedVoices.map((voice, i) => (
              <div
                key={voice.id}
                className={cn(
                  "flex items-center justify-between p-4",
                  i > 0 && "border-t border-foreground/5"
                )}
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-foreground text-background text-[13px] font-semibold">
                    {voice.name.charAt(0)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-[14px] font-medium">{voice.name}</span>
                      <span className="rounded-full bg-foreground/10 px-2 py-0.5 text-[10px] font-medium">
                        Custom
                      </span>
                    </div>
                    <span className="text-[12px] text-foreground/50">{voice.usage} videos</span>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 gap-1.5 rounded-full px-3 text-[12px]"
                  onClick={() => handlePlayVoice(voice.id)}
                >
                  {playingVoice === voice.id ? (
                    <><Pause className="h-3 w-3" />Playing</>
                  ) : (
                    <><Play className="h-3 w-3" />Preview</>
                  )}
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Standard Voices */}
      <div className="mt-10">
        <h2 className="text-[15px] font-semibold">Standard Voices</h2>
        <p className="mt-1 text-[13px] text-foreground/50">High-quality AI voices included with your plan</p>
        <div className="mt-4 rounded-xl border border-foreground/10 divide-y divide-foreground/5">
          {standardVoices.map((voice) => (
            <div key={voice.id} className="flex items-center justify-between p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-foreground/5 text-[13px] font-semibold">
                  {voice.name.charAt(0)}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[14px] font-medium">{voice.name}</span>
                    {voice.favorite && <Star className="h-3 w-3 fill-foreground text-foreground" />}
                  </div>
                  <span className="text-[12px] text-foreground/50">{voice.description}</span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[12px] text-foreground/40">{voice.usage} videos</span>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 gap-1.5 rounded-full border-foreground/10 px-3 text-[12px]"
                  onClick={() => handlePlayVoice(voice.id)}
                >
                  {playingVoice === voice.id ? (
                    <><Pause className="h-3 w-3" />Playing</>
                  ) : (
                    <><Play className="h-3 w-3" />Preview</>
                  )}
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
