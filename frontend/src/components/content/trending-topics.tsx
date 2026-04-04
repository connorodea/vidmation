"use client";

import { useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { TrendingUp, ArrowRight, ExternalLink, RefreshCw } from "lucide-react";

interface TrendingTopic {
  id: string;
  title: string;
  relevance: number; // 0-100
  source: string;
  category: string;
}

// Realistic sample data
const SAMPLE_TOPICS: TrendingTopic[] = [
  {
    id: "1",
    title: "OpenAI releases GPT-5 with native video understanding",
    relevance: 95,
    source: "X / Twitter",
    category: "AI",
  },
  {
    id: "2",
    title: "Apple Vision Pro 2 announced with spatial video editing",
    relevance: 88,
    source: "Hacker News",
    category: "Tech",
  },
  {
    id: "3",
    title: "YouTube Shorts now supports 3-minute videos",
    relevance: 82,
    source: "YouTube Blog",
    category: "Platform",
  },
  {
    id: "4",
    title: "The rise of AI-generated podcasts: ethical concerns",
    relevance: 76,
    source: "Reddit",
    category: "Ethics",
  },
  {
    id: "5",
    title: "Rust overtakes Python in developer satisfaction survey",
    relevance: 71,
    source: "Stack Overflow",
    category: "Dev",
  },
  {
    id: "6",
    title: "How creators are using AI voices for multilingual content",
    relevance: 65,
    source: "Creator Economy",
    category: "Creator",
  },
  {
    id: "7",
    title: "Next.js 16 server actions performance benchmarks",
    relevance: 58,
    source: "Vercel Blog",
    category: "Dev",
  },
];

export function TrendingTopics() {
  const [topics] = useState<TrendingTopic[]>(SAMPLE_TOPICS);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = () => {
    setIsRefreshing(true);
    // Simulate refresh
    setTimeout(() => setIsRefreshing(false), 1500);
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-[#10a37f]" />
          <h3 className="text-sm font-medium text-[#ececec]">
            Trending Topics
          </h3>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="flex h-7 w-7 items-center justify-center rounded-md text-[#666] transition-colors duration-150 hover:bg-white/[0.06] hover:text-[#999] disabled:opacity-40"
          aria-label="Refresh topics"
        >
          <RefreshCw
            className={cn("h-3.5 w-3.5", isRefreshing && "animate-spin")}
          />
        </button>
      </div>

      {/* Topic list */}
      <div className="space-y-1.5">
        {topics.map((topic) => (
          <div
            key={topic.id}
            className="group rounded-xl border border-white/[0.04] bg-white/[0.02] p-3.5 transition-all duration-150 hover:border-white/[0.08] hover:bg-white/[0.04]"
          >
            <div className="mb-2.5 flex items-start justify-between gap-3">
              <p className="text-[13px] leading-snug text-[#ececec]">
                {topic.title}
              </p>
              <Link
                href={`/videos/new?topic=${encodeURIComponent(topic.title)}`}
                className="shrink-0"
              >
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 gap-1 px-2.5 text-[11px] opacity-0 transition-opacity duration-150 group-hover:opacity-100"
                >
                  Use
                  <ArrowRight className="h-3 w-3" />
                </Button>
              </Link>
            </div>

            {/* Relevance bar */}
            <div className="mb-2">
              <div className="h-1 w-full overflow-hidden rounded-full bg-white/[0.06]">
                <div
                  className="h-full rounded-full bg-[#10a37f] transition-all duration-500"
                  style={{ width: `${topic.relevance}%` }}
                />
              </div>
            </div>

            {/* Meta */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="rounded-md bg-white/[0.06] px-1.5 py-0.5 text-[10px] font-medium text-[#999]">
                  {topic.category}
                </span>
                <span className="flex items-center gap-1 text-[10px] text-[#666]">
                  <ExternalLink className="h-2.5 w-2.5" />
                  {topic.source}
                </span>
              </div>
              <span className="text-[10px] tabular-nums font-medium text-[#10a37f]">
                {topic.relevance}%
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
