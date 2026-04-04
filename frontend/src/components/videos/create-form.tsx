"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Channel, VideoFormat } from "@/types";

const FORMAT_OPTIONS: { value: VideoFormat; label: string; desc: string }[] = [
  { value: "landscape", label: "Landscape", desc: "16:9" },
  { value: "portrait", label: "Portrait", desc: "9:16" },
  { value: "short", label: "Short", desc: "<60s" },
];

export function CreateForm() {
  const router = useRouter();
  const [topic, setTopic] = useState("");
  const [channelId, setChannelId] = useState("");
  const [format, setFormat] = useState<VideoFormat>("landscape");
  const [channels, setChannels] = useState<Channel[]>([]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getChannels()
      .then((data) => {
        const list = data as Channel[];
        setChannels(list);
        if (list.length > 0 && !channelId) {
          setChannelId(list[0].id);
        }
      })
      .catch(() => {
        // Channel load failure -- user can still type
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!topic.trim() || !channelId) return;

    setSubmitting(true);
    setError(null);

    try {
      await api.createVideo({
        topic: topic.trim(),
        channel_id: channelId,
        format,
      });
      router.push("/videos");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setSubmitting(false);
    }
  }

  const canSubmit = topic.trim().length > 0 && channelId && !submitting;

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
      {/* Hero textarea */}
      <div className="mb-8">
        <Textarea
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="What video would you like to create?"
          rows={4}
          className="text-base px-5 py-4 min-h-[120px] rounded-2xl"
          autoFocus
          disabled={submitting}
        />
      </div>

      {/* Channel + Format */}
      <div className="flex flex-col sm:flex-row gap-4 mb-8">
        <div className="flex-1">
          <label className="block text-xs text-[#666] mb-2">Channel</label>
          <Select
            value={channelId}
            onValueChange={setChannelId}
            disabled={submitting || channels.length === 0}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select a channel" />
            </SelectTrigger>
            <SelectContent>
              {channels.map((ch) => (
                <SelectItem key={ch.id} value={ch.id}>
                  {ch.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex-1">
          <label className="block text-xs text-[#666] mb-2">Format</label>
          <div className="grid grid-cols-3 gap-2">
            {FORMAT_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setFormat(opt.value)}
                disabled={submitting}
                className={cn(
                  "h-10 rounded-xl border text-sm transition-all duration-150 flex flex-col items-center justify-center",
                  format === opt.value
                    ? "border-[#10a37f] bg-[#10a37f]/10 text-[#10a37f]"
                    : "border-white/[0.08] bg-transparent text-[#999] hover:border-white/[0.15] hover:text-[#ececec]",
                  "disabled:opacity-40"
                )}
              >
                <span className="text-xs font-medium">{opt.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Advanced options */}
      <div className="mb-8">
        <button
          type="button"
          onClick={() => setShowAdvanced((v) => !v)}
          className="text-xs text-[#666] hover:text-[#999] transition-colors duration-100 flex items-center gap-1.5"
        >
          <svg
            width="10"
            height="10"
            viewBox="0 0 10 10"
            fill="currentColor"
            className={cn(
              "transition-transform duration-150",
              showAdvanced && "rotate-90"
            )}
          >
            <path d="M3 1L8 5L3 9V1Z" />
          </svg>
          Advanced options
        </button>

        {showAdvanced && (
          <div className="mt-4 rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 space-y-4">
            <AdvancedRow
              label="Voice"
              text="Default voice settings from channel profile."
            />
            <AdvancedRow
              label="Caption template"
              text="Auto-generated captions based on format."
            />
            <AdvancedRow
              label="Background music"
              text="Selected automatically based on topic."
            />
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-xl border border-[#ef4444]/20 bg-[#ef4444]/5 px-4 py-3 mb-6">
          <p className="text-xs text-[#ef4444]">{error}</p>
        </div>
      )}

      {/* Submit row */}
      <div className="flex items-center justify-between">
        <p className="text-[11px] text-[#666]">
          Estimated cost: ~$0.15 per video
        </p>
        <Button type="submit" size="lg" disabled={!canSubmit} className="min-w-[140px]">
          {submitting ? (
            <span className="flex items-center gap-2">
              <span className="h-3.5 w-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Generating
            </span>
          ) : (
            "Generate"
          )}
        </Button>
      </div>
    </form>
  );
}

function AdvancedRow({ label, text }: { label: string; text: string }) {
  return (
    <div>
      <p className="text-xs text-[#666] mb-1">{label}</p>
      <p className="text-xs text-[#999]">{text}</p>
    </div>
  );
}
