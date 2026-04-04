"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { Layers } from "lucide-react";
import type { Job, JobStatus } from "@/types";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { JobCard } from "@/components/jobs/job-card";

const STATUS_TABS: { label: string; value: JobStatus | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Running", value: "running" },
  { label: "Queued", value: "queued" },
  { label: "Completed", value: "completed" },
  { label: "Failed", value: "failed" },
  { label: "Cancelled", value: "cancelled" },
];

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<JobStatus | "all">("all");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchJobs = useCallback(async () => {
    try {
      const params: Record<string, string> = {};
      if (filter !== "all") params.status = filter;
      const data = await api.getJobs(params);
      setJobs(data as Job[]);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load jobs");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    setLoading(true);
    fetchJobs();
  }, [fetchJobs]);

  // Poll for running job updates
  useEffect(() => {
    const hasActive = jobs.some(
      (j) => j.status === "running" || j.status === "queued"
    );
    if (hasActive) {
      intervalRef.current = setInterval(fetchJobs, 3000);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [jobs, fetchJobs]);

  async function handleRetry(id: string) {
    try {
      await api.retryJob(id);
      fetchJobs();
    } catch {
      // Silently handle -- card reflects current state on next poll
    }
  }

  const filteredJobs =
    filter === "all" ? jobs : jobs.filter((j) => j.status === filter);

  return (
    <div className="min-h-screen">
      <div className="max-w-[1280px] mx-auto px-6 py-10">
        <PageHeader
          title="Jobs"
          description="Track video generation pipeline progress"
        />

        {/* Filter tabs */}
        <div className="mt-8 flex gap-1 rounded-xl bg-white/[0.03] p-1 w-fit">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setFilter(tab.value)}
              className={`rounded-lg px-3.5 py-1.5 text-xs font-medium transition-all duration-150 ${
                filter === tab.value
                  ? "bg-white/[0.08] text-[#ececec]"
                  : "text-[#666] hover:text-[#999]"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="mt-6">
          {loading && (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div
                  key={i}
                  className="h-[120px] animate-pulse rounded-2xl border border-white/[0.08] bg-[#1a1a1a]"
                />
              ))}
            </div>
          )}

          {error && (
            <div className="rounded-2xl border border-[#ef4444]/20 bg-[#ef4444]/5 p-6">
              <p className="text-sm text-[#ef4444]">{error}</p>
            </div>
          )}

          {!loading && !error && filteredJobs.length === 0 && (
            <EmptyState
              icon={Layers}
              title="No jobs found"
              description={
                filter === "all"
                  ? "Jobs will appear here when you generate videos."
                  : `No ${filter} jobs at the moment.`
              }
            />
          )}

          {!loading && !error && filteredJobs.length > 0 && (
            <div className="space-y-3">
              {filteredJobs.map((job) => (
                <JobCard key={job.id} job={job} onRetry={handleRetry} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
