"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { StatusDot } from "@/components/shared/status-dot";
import { Progress } from "@/components/ui/progress";
import type { Job } from "@/types";

export function ActiveJobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    try {
      const data = await api.getJobs({ status: "running" });
      setJobs(data as Job[]);
      setError(null);
    } catch {
      setError("Failed to load jobs");
    }
  }, []);

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 3000);
    return () => clearInterval(interval);
  }, [fetchJobs]);

  if (error) {
    return (
      <div className="rounded-2xl border border-white/[0.08] bg-[#1a1a1a] p-5">
        <p className="text-xs text-[#ef4444]">{error}</p>
      </div>
    );
  }

  if (jobs.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      <h2 className="text-xs font-medium uppercase tracking-wider text-[#666]">
        Active Jobs
      </h2>
      <div className="space-y-2">
        {jobs.map((job) => (
          <div
            key={job.id}
            className="rounded-xl border border-white/[0.08] bg-[#1a1a1a] px-5 py-4"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2.5 min-w-0">
                <StatusDot status={job.status} />
                <span className="text-sm text-[#ececec] truncate">
                  {job.video?.title || `Job ${job.id.slice(0, 8)}`}
                </span>
              </div>
              <span className="text-xs tabular-nums text-[#999] ml-3 shrink-0">
                {job.progress_pct}%
              </span>
            </div>
            <Progress value={job.progress_pct} />
            <p className="text-[11px] text-[#666] mt-2.5 capitalize">
              {job.current_stage.replace(/_/g, " ")}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
