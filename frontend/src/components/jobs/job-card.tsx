"use client";

import Link from "next/link";
import { RotateCw } from "lucide-react";
import type { Job, JobStatus, JobType } from "@/types";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatusDot } from "@/components/shared/status-dot";
import { formatRelativeTime, truncate } from "@/lib/utils";

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

interface JobCardProps {
  job: Job;
  onRetry?: (id: string) => void;
}

export function JobCard({ job, onRetry }: JobCardProps) {
  return (
    <Link href={`/jobs/${job.id}`}>
      <Card className="group cursor-pointer transition-all duration-150 hover:border-white/[0.15] hover:bg-[#1a1a1a]/80">
        <CardContent className="p-6">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2.5">
                <StatusDot status={job.status} />
                <Badge variant={STATUS_BADGE[job.status]}>
                  {STATUS_LABEL[job.status]}
                </Badge>
                <span className="text-[13px] text-[#666]">
                  {JOB_TYPE_LABELS[job.job_type]}
                </span>
              </div>

              {job.video?.topic_prompt && (
                <p className="mt-3 text-[15px] text-[#ececec]">
                  {truncate(job.video.topic_prompt, 80)}
                </p>
              )}

              {job.current_stage && (
                <p className="mt-1.5 text-[13px] text-[#666]">
                  Stage: {job.current_stage}
                </p>
              )}

              {(job.status === "running" || job.status === "queued") &&
                job.progress_pct > 0 && (
                  <div className="mt-4">
                    <div className="flex items-center justify-between text-[12px] text-[#666]">
                      <span>Progress</span>
                      <span>{Math.round(job.progress_pct)}%</span>
                    </div>
                    <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-white/[0.06]">
                      <div
                        className="progress-bar h-full rounded-full bg-[#10a37f]"
                        style={{ width: `${job.progress_pct}%` }}
                      />
                    </div>
                  </div>
                )}

              <p className="mt-3 text-[12px] text-[#666]">
                {truncate(job.id, 12)}
                {job.started_at && (
                  <span className="ml-2">
                    {formatRelativeTime(job.started_at)}
                  </span>
                )}
              </p>
            </div>

            {job.status === "failed" && onRetry && (
              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onRetry(job.id);
                }}
                aria-label="Retry job"
                className="shrink-0"
              >
                <RotateCw className="h-4 w-4" />
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
