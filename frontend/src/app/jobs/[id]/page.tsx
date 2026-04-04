"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  XCircle,
  RotateCw,
  Play,
  Hash,
  Layers,
  Calendar,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import type { Job, JobStatus, JobType } from "@/types";
import { api } from "@/lib/api";
import { formatDate, truncate } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusDot } from "@/components/shared/status-dot";

const STATUS_BADGE: Record<JobStatus, "default" | "success" | "warning" | "error" | "info"> = {
  queued: "warning",
  running: "info",
  completed: "success",
  failed: "error",
  cancelled: "default",
};

const STATUS_LABEL: Record<JobStatus, string> = {
  queued: "Queued",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

const JOB_TYPE_LABELS: Record<JobType, string> = {
  full_pipeline: "Full Pipeline",
  script_only: "Script Generation",
  tts_only: "Text-to-Speech",
  video_only: "Video Render",
  upload_only: "Upload",
  thumbnail_only: "Thumbnail",
};

export default function JobDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!params.id) return;
    api
      .getJob(params.id)
      .then((data) => {
        setJob(data as Job);
        setError(null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [params.id]);

  // Poll for updates on active jobs
  useEffect(() => {
    if (!job || !params.id) return;
    if (job.status === "running" || job.status === "queued") {
      intervalRef.current = setInterval(async () => {
        try {
          const data = await api.getJob(params.id);
          setJob(data as Job);
        } catch {
          // Keep showing stale data on poll failure
        }
      }, 2000);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [job?.status, params.id]);

  async function handleCancel() {
    if (!params.id) return;
    try {
      await api.cancelJob(params.id);
      const data = await api.getJob(params.id);
      setJob(data as Job);
    } catch {
      // UI reflects state on next poll
    }
  }

  async function handleRetry() {
    if (!params.id) return;
    try {
      await api.retryJob(params.id);
      const data = await api.getJob(params.id);
      setJob(data as Job);
    } catch {
      // UI reflects state on next poll
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen">
        <div className="max-w-[960px] mx-auto px-6 py-10">
          <div className="h-5 w-32 animate-pulse rounded-lg bg-white/[0.06]" />
          <div className="mt-8 h-16 animate-pulse rounded-2xl border border-white/[0.08] bg-[#1a1a1a]" />
          <div className="mt-6 grid gap-6 md:grid-cols-2">
            <div className="h-56 animate-pulse rounded-2xl border border-white/[0.08] bg-[#1a1a1a]" />
            <div className="h-56 animate-pulse rounded-2xl border border-white/[0.08] bg-[#1a1a1a]" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="min-h-screen">
        <div className="max-w-[960px] mx-auto px-6 py-10">
          <Link
            href="/jobs"
            className="inline-flex items-center gap-1.5 text-sm text-[#666] transition-colors hover:text-[#ececec]"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Jobs
          </Link>
          <div className="mt-8 rounded-2xl border border-[#ef4444]/20 bg-[#ef4444]/5 p-6">
            <p className="text-sm text-[#ef4444]">
              {error || "Job not found"}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="max-w-[960px] mx-auto px-6 py-10">
        {/* Back link */}
        <Link
          href="/jobs"
          className="inline-flex items-center gap-1.5 text-sm text-[#666] transition-colors hover:text-[#ececec]"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Jobs
        </Link>

        {/* Header */}
        <div className="mt-8 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight text-[#ececec]">
              {truncate(job.id, 12)}
            </h1>
            <Badge variant={STATUS_BADGE[job.status]}>
              {STATUS_LABEL[job.status]}
            </Badge>
          </div>
          <span className="text-sm text-[#666]">
            {JOB_TYPE_LABELS[job.job_type]}
          </span>
        </div>

        {/* Two-column layout */}
        <div className="mt-8 grid gap-6 md:grid-cols-2">
          {/* Progress */}
          <Card>
            <CardHeader>
              <CardTitle>Progress</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-5">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-2 text-sm text-[#666]">
                    <StatusDot status={job.status} />
                    Status
                  </span>
                  <span className="text-sm text-[#ececec]">
                    {STATUS_LABEL[job.status]}
                  </span>
                </div>

                {job.current_stage && (
                  <>
                    <div className="h-px bg-white/[0.06]" />
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-2 text-sm text-[#666]">
                        <Layers className="h-4 w-4" />
                        Stage
                      </span>
                      <span className="text-sm text-[#ececec]">
                        {job.current_stage}
                      </span>
                    </div>
                  </>
                )}

                <div className="h-px bg-white/[0.06]" />

                <div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[#666]">Progress</span>
                    <span className="tabular-nums text-[#ececec]">
                      {Math.round(job.progress_pct)}%
                    </span>
                  </div>
                  <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-white/[0.06]">
                    <div
                      className="progress-bar h-full rounded-full bg-[#10a37f]"
                      style={{ width: `${job.progress_pct}%` }}
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Details */}
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="space-y-4">
                <div className="flex items-center justify-between">
                  <dt className="flex items-center gap-2 text-sm text-[#666]">
                    <Hash className="h-4 w-4" />
                    Job ID
                  </dt>
                  <dd className="max-w-[180px] truncate font-mono text-xs text-[#ececec]">
                    {job.id}
                  </dd>
                </div>

                <div className="h-px bg-white/[0.06]" />

                <div className="flex items-center justify-between">
                  <dt className="flex items-center gap-2 text-sm text-[#666]">
                    <Layers className="h-4 w-4" />
                    Type
                  </dt>
                  <dd className="text-sm text-[#ececec]">
                    {JOB_TYPE_LABELS[job.job_type]}
                  </dd>
                </div>

                <div className="h-px bg-white/[0.06]" />

                <div className="flex items-center justify-between">
                  <dt className="flex items-center gap-2 text-sm text-[#666]">
                    <Calendar className="h-4 w-4" />
                    Started
                  </dt>
                  <dd className="text-sm text-[#ececec]">
                    {job.started_at ? formatDate(job.started_at) : "Pending"}
                  </dd>
                </div>

                <div className="h-px bg-white/[0.06]" />

                <div className="flex items-center justify-between">
                  <dt className="flex items-center gap-2 text-sm text-[#666]">
                    <CheckCircle2 className="h-4 w-4" />
                    Completed
                  </dt>
                  <dd className="text-sm text-[#ececec]">
                    {job.completed_at ? formatDate(job.completed_at) : "--"}
                  </dd>
                </div>
              </dl>
            </CardContent>
          </Card>
        </div>

        {/* Action buttons */}
        <div className="mt-6 flex items-center gap-3">
          {(job.status === "running" || job.status === "queued") && (
            <Button variant="destructive" onClick={handleCancel}>
              <XCircle className="h-4 w-4" />
              Cancel Job
            </Button>
          )}

          {job.status === "failed" && (
            <Button onClick={handleRetry}>
              <RotateCw className="h-4 w-4" />
              Retry Job
            </Button>
          )}

          {job.status === "completed" && job.video_id && (
            <Button
              variant="secondary"
              onClick={() => router.push(`/videos/${job.video_id}`)}
            >
              <Play className="h-4 w-4" />
              View Video
            </Button>
          )}
        </div>

        {/* Error details */}
        {job.status === "failed" && job.error_detail && (
          <Card className="mt-6 border-[#ef4444]/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-[#ef4444]">
                <AlertTriangle className="h-4 w-4" />
                Error Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="overflow-x-auto whitespace-pre-wrap break-words rounded-xl bg-[#0d0d0d] p-4 font-mono text-xs leading-relaxed text-[#ef4444]/80">
                {job.error_detail}
              </pre>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
