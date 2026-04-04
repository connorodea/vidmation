export type VideoFormat = "landscape" | "portrait" | "short";
export type VideoStatus = "draft" | "generating" | "ready" | "uploaded" | "failed";
export type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";
export type JobType = "full_pipeline" | "script_only" | "tts_only" | "video_only" | "upload_only" | "thumbnail_only";

export interface Video {
  id: string;
  channel_id: string;
  title: string;
  description: string;
  tags: string[];
  topic_prompt: string;
  script_json: Record<string, unknown> | null;
  format: VideoFormat;
  status: VideoStatus;
  youtube_video_id: string | null;
  youtube_url: string | null;
  duration_seconds: number | null;
  file_path: string | null;
  thumbnail_path: string | null;
  error_message: string | null;
  created_at: string;
  channel: Channel;
  jobs: Job[];
}

export interface Channel {
  id: string;
  name: string;
  youtube_channel_id: string | null;
  profile_path: string;
  is_active: boolean;
  created_at: string;
}

export interface Job {
  id: string;
  video_id: string;
  job_type: JobType;
  status: JobStatus;
  current_stage: string;
  progress_pct: number;
  started_at: string | null;
  completed_at: string | null;
  error_detail: string | null;
  created_at: string;
  video?: Video;
}

export interface UsageEvent {
  id: string;
  service: string;
  operation: string;
  cost_usd: number;
  tokens_used: number | null;
  duration_seconds: number | null;
  model_name: string | null;
  created_at: string;
}

export interface CostSummary {
  total_cost: number;
  total_calls: number;
  by_service: Record<string, number>;
  daily_trend: { date: string; cost: number }[];
}
