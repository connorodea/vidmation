"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Sparkles, Plus, ChevronLeft, ChevronRight, Check, Clock } from "lucide-react"
import { cn } from "@/lib/utils"

const mockCalendar = [
  {
    week: "Apr 6 - 12",
    items: [
      { topic: "The Psychology of Wealth Building", status: "completed" },
      { topic: "5 Investment Mistakes to Avoid", status: "completed" },
      { topic: "How Banks Create Money", status: "completed" },
    ],
  },
  {
    week: "Apr 13 - 19",
    items: [
      { topic: "AI Tools That Will Change Finance", status: "pending" },
      { topic: "The Future of Cryptocurrency", status: "pending" },
      { topic: "Building Passive Income Streams", status: "pending" },
    ],
  },
  {
    week: "Apr 20 - 26",
    items: [
      { topic: "Tax Strategies for 2026", status: "pending" },
      { topic: "Real Estate vs Stocks", status: "pending" },
    ],
  },
]

const trendingTopics = [
  { topic: "AI Regulation Impact on Tech Stocks", score: 95 },
  { topic: "Federal Reserve Rate Decisions", score: 92 },
  { topic: "Bitcoin ETF Performance Analysis", score: 88 },
  { topic: "Housing Market Predictions", score: 85 },
]

export default function ContentPage() {
  const [isGenerating, setIsGenerating] = useState(false)

  const handleGenerate = async () => {
    setIsGenerating(true)
    await new Promise((resolve) => setTimeout(resolve, 2000))
    setIsGenerating(false)
  }

  return (
    <div className="p-8 lg:p-12">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-[32px] font-semibold tracking-tight">Content Planner</h1>
          <p className="mt-1 text-[15px] text-foreground/60">
            Plan your video content calendar
          </p>
        </div>
        <Button
          className="h-9 gap-1.5 rounded-full bg-foreground px-4 text-[13px] font-medium text-background hover:bg-foreground/90"
          onClick={handleGenerate}
          disabled={isGenerating}
        >
          <Sparkles className="h-3.5 w-3.5" />
          {isGenerating ? "Generating..." : "Generate Ideas"}
        </Button>
      </div>

      <div className="mt-10 grid gap-8 lg:grid-cols-3">
        {/* Calendar */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between">
            <h2 className="text-[15px] font-semibold">Calendar</h2>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon" className="h-7 w-7 rounded-full">
                <ChevronLeft className="h-3.5 w-3.5" />
              </Button>
              <span className="text-[13px]">April 2026</span>
              <Button variant="ghost" size="icon" className="h-7 w-7 rounded-full">
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          <div className="mt-4 space-y-4">
            {mockCalendar.map((week, weekIndex) => (
              <div key={weekIndex} className="rounded-xl border border-foreground/10">
                <div className="flex items-center justify-between border-b border-foreground/10 px-4 py-2.5">
                  <span className="text-[12px] font-medium">Week {weekIndex + 1}: {week.week}</span>
                  <span className="text-[11px] text-foreground/50">{week.items.length} videos</span>
                </div>
                <div className="divide-y divide-foreground/5">
                  {week.items.map((item, itemIndex) => (
                    <div key={itemIndex} className="flex items-center justify-between px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className={cn(
                          "flex h-6 w-6 items-center justify-center rounded-full",
                          item.status === "completed" ? "bg-foreground" : "bg-foreground/10"
                        )}>
                          {item.status === "completed" ? (
                            <Check className="h-3 w-3 text-background" />
                          ) : (
                            <Clock className="h-3 w-3 text-foreground/50" />
                          )}
                        </div>
                        <span className="text-[13px]">{item.topic}</span>
                      </div>
                      {item.status === "pending" && (
                        <Button variant="ghost" size="sm" className="h-7 rounded-full px-3 text-[11px]">
                          Create
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <div>
            <h2 className="text-[15px] font-semibold">Trending Topics</h2>
            <p className="mt-1 text-[13px] text-foreground/50">Based on your niche</p>
            <div className="mt-4 space-y-2">
              {trendingTopics.map((topic, i) => (
                <div
                  key={i}
                  className="group flex items-center justify-between rounded-xl border border-foreground/10 p-3 transition-colors hover:bg-foreground/[0.02]"
                >
                  <div className="flex-1">
                    <p className="text-[13px]">{topic.topic}</p>
                    <div className="mt-1.5 flex items-center gap-2">
                      <div className="h-1 w-16 overflow-hidden rounded-full bg-foreground/10">
                        <div className="h-full rounded-full bg-foreground" style={{ width: `${topic.score}%` }} />
                      </div>
                      <span className="text-[10px] text-foreground/40">{topic.score}%</span>
                    </div>
                  </div>
                  <Button variant="ghost" size="icon" className="h-6 w-6 rounded-full opacity-0 group-hover:opacity-100">
                    <Plus className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-foreground/10 p-4">
            <h3 className="text-[13px] font-semibold">This Month</h3>
            <div className="mt-3 space-y-2">
              <div className="flex items-center justify-between text-[12px]">
                <span className="text-foreground/60">Planned</span>
                <span className="font-medium">8 videos</span>
              </div>
              <div className="flex items-center justify-between text-[12px]">
                <span className="text-foreground/60">Completed</span>
                <span className="font-medium">3 videos</span>
              </div>
              <div className="flex items-center justify-between text-[12px]">
                <span className="text-foreground/60">Pending</span>
                <span className="font-medium">5 videos</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
