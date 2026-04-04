import { VideoTable } from "@/components/videos/video-table";
import type { Video } from "@/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export async function DashboardVideos() {
  let videos: Video[] = [];

  try {
    const res = await fetch(`${API_BASE}/videos?limit=10`, {
      cache: "no-store",
    });
    if (res.ok) {
      videos = await res.json();
    }
  } catch {
    // Fail silently -- table will show empty state
  }

  return <VideoTable videos={videos} />;
}
