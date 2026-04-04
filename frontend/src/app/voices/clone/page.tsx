"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import {
  Upload,
  Mic,
  ArrowLeft,
  FileAudio,
  X,
  AudioLines,
} from "lucide-react";

type CloneProvider = "elevenlabs" | "replicate" | "fal";

const PROVIDERS: { value: CloneProvider; label: string; description: string }[] =
  [
    {
      value: "elevenlabs",
      label: "ElevenLabs",
      description: "High-quality voice cloning with emotional range",
    },
    {
      value: "replicate",
      label: "Replicate",
      description: "Open-source models, cost-effective for bulk generation",
    },
    {
      value: "fal",
      label: "fal",
      description: "Fast inference, optimized for real-time applications",
    },
  ];

export default function CloneVoicePage() {
  const [name, setName] = useState("");
  const [provider, setProvider] = useState<CloneProvider>("elevenlabs");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isCloning, setIsCloning] = useState(false);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped && dropped.type.startsWith("audio/")) {
      setFile(dropped);
    }
  }, []);

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = e.target.files?.[0];
      if (selected) setFile(selected);
    },
    []
  );

  const handleClone = () => {
    if (!name || !file) return;
    setIsCloning(true);
    // Placeholder for actual clone logic
    setTimeout(() => setIsCloning(false), 3000);
  };

  const canSubmit = name.trim().length > 0 && file !== null && !isCloning;

  return (
    <div className="min-h-screen bg-[#0d0d0d]">
      <div className="mx-auto max-w-2xl px-6 py-8">
        {/* Back navigation */}
        <Link
          href="/voices"
          className="mb-6 inline-flex items-center gap-1.5 text-xs text-[#666] transition-colors duration-150 hover:text-[#999]"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Voices
        </Link>

        {/* Page header */}
        <div className="mb-8 flex items-center gap-3">
          <Mic className="h-5 w-5 text-[#666]" />
          <h1 className="text-2xl font-semibold text-[#ececec]">
            Clone Voice
          </h1>
        </div>

        <div className="space-y-8">
          {/* Upload area */}
          <div>
            <label className="mb-2 block text-sm font-medium text-[#ececec]">
              Voice Sample
            </label>
            <p className="mb-3 text-xs text-[#666]">
              Upload a clear audio recording. WAV or MP3, at least 30 seconds recommended.
            </p>

            {!file ? (
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={cn(
                  "relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed py-16 transition-all duration-150",
                  isDragOver
                    ? "border-[#10a37f] bg-[#10a37f]/[0.04]"
                    : "border-white/[0.08] bg-[#1a1a1a] hover:border-white/[0.15]"
                )}
              >
                <div
                  className={cn(
                    "mb-4 flex h-14 w-14 items-center justify-center rounded-full transition-colors duration-150",
                    isDragOver ? "bg-[#10a37f]/10" : "bg-white/[0.04]"
                  )}
                >
                  <Upload
                    className={cn(
                      "h-6 w-6",
                      isDragOver ? "text-[#10a37f]" : "text-[#666]"
                    )}
                  />
                </div>
                <p className="text-sm text-[#999]">
                  Drag and drop your audio file here
                </p>
                <p className="mt-1 text-xs text-[#666]">
                  or click to browse
                </p>
                <input
                  type="file"
                  accept="audio/*"
                  onChange={handleFileSelect}
                  className="absolute inset-0 cursor-pointer opacity-0"
                  aria-label="Upload voice sample"
                />
              </div>
            ) : (
              <div className="flex items-center gap-4 rounded-2xl border border-white/[0.08] bg-[#1a1a1a] p-5">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[#10a37f]/10">
                  <FileAudio className="h-5 w-5 text-[#10a37f]" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-[#ececec]">
                    {file.name}
                  </p>
                  <p className="mt-0.5 text-xs text-[#666]">
                    {(file.size / (1024 * 1024)).toFixed(1)} MB
                  </p>
                </div>
                <button
                  onClick={() => setFile(null)}
                  className="flex h-8 w-8 items-center justify-center rounded-lg text-[#666] transition-colors duration-150 hover:bg-white/[0.06] hover:text-[#999]"
                  aria-label="Remove file"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>

          {/* Voice name */}
          <div>
            <label
              htmlFor="voice-name"
              className="mb-2 block text-sm font-medium text-[#ececec]"
            >
              Voice Name
            </label>
            <Input
              id="voice-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Custom Voice"
              className="max-w-sm"
            />
          </div>

          {/* Provider selector */}
          <div>
            <label className="mb-2 block text-sm font-medium text-[#ececec]">
              Provider
            </label>
            <div className="grid grid-cols-3 gap-3">
              {PROVIDERS.map((p) => (
                <button
                  key={p.value}
                  onClick={() => setProvider(p.value)}
                  className={cn(
                    "rounded-xl border p-4 text-left transition-all duration-150",
                    provider === p.value
                      ? "border-[#10a37f]/40 bg-[#10a37f]/[0.04]"
                      : "border-white/[0.08] bg-[#1a1a1a] hover:border-white/[0.15]"
                  )}
                >
                  <p
                    className={cn(
                      "text-sm font-medium",
                      provider === p.value
                        ? "text-[#ececec]"
                        : "text-[#999]"
                    )}
                  >
                    {p.label}
                  </p>
                  <p className="mt-1 text-[11px] leading-snug text-[#666]">
                    {p.description}
                  </p>
                </button>
              ))}
            </div>
          </div>

          {/* Description */}
          <div>
            <label
              htmlFor="voice-description"
              className="mb-2 block text-sm font-medium text-[#ececec]"
            >
              Description
              <span className="ml-1 text-xs font-normal text-[#666]">
                Optional
              </span>
            </label>
            <Textarea
              id="voice-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="A warm, professional narrator voice suited for tech explainers"
              rows={3}
            />
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 border-t border-white/[0.06] pt-6">
            <Button
              onClick={handleClone}
              disabled={!canSubmit}
              className="gap-2"
            >
              <AudioLines className="h-4 w-4" />
              {isCloning ? "Cloning..." : "Clone Voice"}
            </Button>
            <Link href="/voices">
              <Button variant="ghost">Cancel</Button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
