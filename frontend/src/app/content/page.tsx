"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { CalendarGrid } from "@/components/content/calendar-grid";
import { TrendingTopics } from "@/components/content/trending-topics";
import { Sparkles, Calendar } from "lucide-react";

export default function ContentPage() {
  const [isGenerating, setIsGenerating] = useState(false);
  const router = useRouter();

  const handleGenerateCalendar = () => {
    setIsGenerating(true);
    // Simulate calendar generation
    setTimeout(() => setIsGenerating(false), 2000);
  };

  return (
    <div className="min-h-screen bg-[#0d0d0d]">
      <div className="mx-auto max-w-[1440px] px-6 py-8">
        {/* Page header */}
        <div className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Calendar className="h-5 w-5 text-[#666]" />
            <h1 className="text-2xl font-semibold text-[#ececec]">Content</h1>
          </div>
          <Button
            onClick={handleGenerateCalendar}
            disabled={isGenerating}
            className="gap-2"
          >
            <Sparkles className="h-4 w-4" />
            {isGenerating ? "Generating..." : "Generate Calendar"}
          </Button>
        </div>

        {/* Main layout: calendar + trending sidebar */}
        <div className="flex gap-6">
          {/* Calendar grid - left 2/3 */}
          <div className="min-w-0 flex-1">
            <CalendarGrid
              onItemClick={(item) => {
                router.push(`/videos/new?topic=${encodeURIComponent(item.topic)}`);
              }}
              onAddClick={(date) => {
                // TODO: Open content creation for this date
              }}
            />
          </div>

          {/* Trending topics sidebar - right 1/3 */}
          <div className="w-[380px] shrink-0">
            <div className="sticky top-8 rounded-2xl border border-white/[0.08] bg-[#1a1a1a] p-5">
              <TrendingTopics />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
