"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { UpcomingList } from "@/components/schedule/upcoming-list";
import {
  CalendarClock,
  Plus,
  Repeat,
  Hash,
  Clock,
  Zap,
} from "lucide-react";

interface RecurringRule {
  id: string;
  channel: string;
  frequency: string;
  topicSource: string;
  isActive: boolean;
  nextRun: string;
  videosGenerated: number;
}

const SAMPLE_RULES: RecurringRule[] = [
  {
    id: "1",
    channel: "Tech Daily",
    frequency: "Daily at 9:00 AM",
    topicSource: "AI-suggested trending topics",
    isActive: true,
    nextRun: "2026-04-05T09:00:00Z",
    videosGenerated: 47,
  },
  {
    id: "2",
    channel: "Dev Tutorials",
    frequency: "3x per week (Mon, Wed, Fri)",
    topicSource: "Content calendar queue",
    isActive: true,
    nextRun: "2026-04-07T10:00:00Z",
    videosGenerated: 23,
  },
  {
    id: "3",
    channel: "Business Talks",
    frequency: "Weekly on Tuesdays",
    topicSource: "RSS feed: TechCrunch",
    isActive: false,
    nextRun: "2026-04-08T08:00:00Z",
    videosGenerated: 12,
  },
];

export default function SchedulePage() {
  const [showForm, setShowForm] = useState(false);
  const [rules] = useState<RecurringRule[]>(SAMPLE_RULES);

  return (
    <div className="min-h-screen bg-[#0d0d0d]">
      <div className="mx-auto max-w-[1200px] px-6 py-8">
        {/* Page header */}
        <div className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CalendarClock className="h-5 w-5 text-[#666]" />
            <h1 className="text-2xl font-semibold text-[#ececec]">Schedule</h1>
          </div>
          <Button
            onClick={() => setShowForm(!showForm)}
            className="gap-2"
          >
            <Plus className="h-4 w-4" />
            Schedule Video
          </Button>
        </div>

        <div className="space-y-10">
          {/* Upcoming section */}
          <section>
            <div className="mb-4 flex items-center gap-2">
              <Clock className="h-4 w-4 text-[#666]" />
              <h2 className="text-sm font-medium text-[#999]">Upcoming</h2>
            </div>
            <UpcomingList />
          </section>

          {/* Recurring section */}
          <section>
            <div className="mb-4 flex items-center gap-2">
              <Repeat className="h-4 w-4 text-[#666]" />
              <h2 className="text-sm font-medium text-[#999]">
                Recurring Rules
              </h2>
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              {rules.map((rule) => (
                <div
                  key={rule.id}
                  className="rounded-2xl border border-white/[0.08] bg-[#1a1a1a] p-5 transition-colors duration-150 hover:border-white/[0.12]"
                >
                  {/* Rule header */}
                  <div className="mb-4 flex items-start justify-between">
                    <div>
                      <h3 className="text-sm font-medium text-[#ececec]">
                        {rule.channel}
                      </h3>
                      <p className="mt-0.5 text-xs text-[#666]">
                        {rule.frequency}
                      </p>
                    </div>
                    <Badge
                      variant={rule.isActive ? "success" : "default"}
                    >
                      {rule.isActive ? "Active" : "Paused"}
                    </Badge>
                  </div>

                  {/* Rule details */}
                  <div className="space-y-3 border-t border-white/[0.06] pt-4">
                    <div className="flex items-start gap-2.5">
                      <Zap className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#666]" />
                      <div>
                        <p className="text-[11px] text-[#666]">
                          Topic Source
                        </p>
                        <p className="text-xs text-[#999]">
                          {rule.topicSource}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-2.5">
                      <Hash className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#666]" />
                      <div>
                        <p className="text-[11px] text-[#666]">Generated</p>
                        <p className="text-xs tabular-nums text-[#999]">
                          {rule.videosGenerated} videos
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Next run */}
                  <div className="mt-4 rounded-lg bg-white/[0.03] px-3 py-2">
                    <p className="text-[10px] text-[#666]">Next run</p>
                    <p className="text-xs tabular-nums text-[#999]">
                      {new Date(rule.nextRun).toLocaleDateString("en-US", {
                        weekday: "short",
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
