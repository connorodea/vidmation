import Link from "next/link";
import { notFound } from "next/navigation";
import { StatusDot } from "@/components/shared/status-dot";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { formatDuration, formatDate } from "@/lib/utils";
import type { Video, Job } from "@/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function getVideo(id: string): Promise<Video | null> {
  try {
    const res = await fetch(`${API_BASE}/videos/${id}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function VideoDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const video = await getVideo(id);

  if (!video) {
    notFound();
  }

  return (
    <div className="max-w-[1200px]">
      {/* Back link */}
      <Link
        href="/videos"
        className="inline-flex items-center gap-1.5 text-sm text-[#666] hover:text-[#999] transition-colors duration-100 mb-6"
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 14 14"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M9 11L5 7L9 3" />
        </svg>
        Videos
      </Link>

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-2xl font-semibold text-[#ececec] truncate">
            {video.title}
          </h1>
          <StatusDot status={video.status} className="mt-0.5" />
        </div>
        <div className="flex items-center gap-3 text-xs text-[#666]">
          <span className="capitalize">{video.format}</span>
          <span className="text-white/[0.15]">|</span>
          <span>{video.channel?.name ?? "Unknown channel"}</span>
          <span className="text-white/[0.15]">|</span>
          <span className="capitalize">{video.status}</span>
        </div>
      </div>

      {/* Two-column layout */}
      <div className="flex flex-col lg:flex-row gap-8">
        {/* Left column */}
        <div className="flex-1 min-w-0 space-y-6">
          {/* Topic prompt */}
          {video.topic_prompt && (
            <Section title="Topic Prompt">
              <p className="text-sm text-[#999] leading-relaxed">
                {video.topic_prompt}
              </p>
            </Section>
          )}

          {/* Description */}
          {video.description && (
            <Section title="Description">
              <p className="text-sm text-[#999] leading-relaxed whitespace-pre-wrap">
                {video.description}
              </p>
            </Section>
          )}

          {/* Script JSON (collapsible) */}
          {video.script_json && <ScriptSection script={video.script_json} />}

          {/* Jobs */}
          {video.jobs && video.jobs.length > 0 && (
            <Section title="Jobs">
              <div className="space-y-3">
                {video.jobs.map((job: Job) => (
                  <div
                    key={job.id}
                    className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3.5"
                  >
                    <div className="flex items-center justify-between mb-2.5">
                      <div className="flex items-center gap-2">
                        <StatusDot status={job.status} />
                        <span className="text-sm text-[#ececec] capitalize">
                          {job.job_type.replace(/_/g, " ")}
                        </span>
                      </div>
                      <span className="text-xs tabular-nums text-[#666]">
                        {job.progress_pct}%
                      </span>
                    </div>
                    <Progress value={job.progress_pct} />
                    <div className="flex items-center justify-between mt-2.5">
                      <span className="text-[11px] text-[#666] capitalize">
                        {job.current_stage.replace(/_/g, " ")}
                      </span>
                      {job.started_at && (
                        <span className="text-[11px] text-[#666]">
                          {formatDate(job.started_at)}
                        </span>
                      )}
                    </div>
                    {job.error_detail && (
                      <p className="text-xs text-[#ef4444] mt-2">
                        {job.error_detail}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </Section>
          )}
        </div>

        {/* Right column */}
        <div className="w-full lg:w-80 shrink-0 space-y-6">
          {/* Metadata */}
          <Section title="Metadata">
            <div className="space-y-3">
              <MetaRow
                label="Duration"
                value={
                  video.duration_seconds
                    ? formatDuration(video.duration_seconds)
                    : "--"
                }
              />
              <MetaRow label="Format" value={video.format} capitalize />
              <MetaRow label="Created" value={formatDate(video.created_at)} />
              <MetaRow
                label="YouTube ID"
                value={video.youtube_video_id || "--"}
                mono={!!video.youtube_video_id}
              />
              {video.youtube_url && (
                <div className="flex items-start justify-between gap-2">
                  <span className="text-[11px] text-[#666] shrink-0 pt-0.5">
                    YouTube
                  </span>
                  <a
                    href={video.youtube_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-[#10a37f] hover:underline text-right break-all"
                  >
                    {video.youtube_url}
                  </a>
                </div>
              )}
            </div>
          </Section>

          {/* Tags */}
          {video.tags && video.tags.length > 0 && (
            <Section title="Tags">
              <div className="flex flex-wrap gap-1.5">
                {video.tags.map((tag: string) => (
                  <Badge key={tag} variant="default">
                    {tag}
                  </Badge>
                ))}
              </div>
            </Section>
          )}

          {/* Error */}
          {video.error_message && (
            <div className="rounded-2xl border border-[#ef4444]/20 bg-[#ef4444]/5 p-5">
              <h3 className="text-xs font-medium text-[#ef4444] mb-2">
                Error
              </h3>
              <p className="text-xs text-[#ef4444]/80 leading-relaxed">
                {video.error_message}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-white/[0.08] bg-[#1a1a1a] p-6">
      <h3 className="text-xs font-medium uppercase tracking-wider text-[#666] mb-4">
        {title}
      </h3>
      {children}
    </div>
  );
}

function MetaRow({
  label,
  value,
  capitalize: cap,
  mono,
}: {
  label: string;
  value: string;
  capitalize?: boolean;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-[11px] text-[#666]">{label}</span>
      <span
        className={`text-xs text-[#999] ${cap ? "capitalize" : ""} ${mono ? "font-mono" : ""}`}
      >
        {value}
      </span>
    </div>
  );
}

function ScriptSection({ script }: { script: Record<string, unknown> }) {
  return (
    <details className="group rounded-2xl border border-white/[0.08] bg-[#1a1a1a] overflow-hidden">
      <summary className="px-6 py-4 cursor-pointer text-xs font-medium uppercase tracking-wider text-[#666] hover:text-[#999] transition-colors duration-100 flex items-center gap-2 list-none [&::-webkit-details-marker]:hidden">
        <svg
          width="10"
          height="10"
          viewBox="0 0 10 10"
          fill="currentColor"
          className="transition-transform duration-150 group-open:rotate-90"
        >
          <path d="M3 1L8 5L3 9V1Z" />
        </svg>
        Script JSON
      </summary>
      <div className="px-6 pb-5 -mt-1">
        <pre className="text-xs text-[#999] font-mono leading-relaxed overflow-x-auto whitespace-pre-wrap break-words">
          {JSON.stringify(script, null, 2)}
        </pre>
      </div>
    </details>
  );
}
