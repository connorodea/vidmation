import Link from "next/link";
import { cn } from "@/lib/utils";
import { VideoTable } from "@/components/videos/video-table";
import type { Video } from "@/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api/v1";

const TABS: { label: string; value: string }[] = [
  { label: "All", value: "all" },
  { label: "Draft", value: "draft" },
  { label: "Generating", value: "generating" },
  { label: "Ready", value: "ready" },
  { label: "Uploaded", value: "uploaded" },
  { label: "Failed", value: "failed" },
];

export async function VideoListContent({
  searchParamsPromise,
}: {
  searchParamsPromise: Promise<{ status?: string }>;
}) {
  const searchParams = await searchParamsPromise;
  const activeTab = searchParams?.status || "all";

  let videos: Video[] = [];

  try {
    const params = activeTab !== "all" ? `?status=${activeTab}` : "";
    const res = await fetch(`${API_BASE}/videos${params}`, {
      cache: "no-store",
    });
    if (res.ok) {
      videos = await res.json();
    }
  } catch {
    // Fail silently
  }

  return (
    <>
      {/* Filter pills */}
      <div className="flex items-center gap-1.5 mb-6">
        {TABS.map((tab) => {
          const isActive = activeTab === tab.value;
          return (
            <Link
              key={tab.value}
              href={
                tab.value === "all"
                  ? "/videos"
                  : `/videos?status=${tab.value}`
              }
              className={cn(
                "px-3 py-1.5 rounded-full text-xs font-medium transition-colors duration-100",
                isActive
                  ? "bg-white/[0.1] text-[#ececec]"
                  : "text-[#666] hover:text-[#999] hover:bg-white/[0.04]"
              )}
            >
              {tab.label}
            </Link>
          );
        })}
      </div>

      {/* Table */}
      <div className="rounded-2xl border border-white/[0.08] bg-[#1a1a1a] overflow-hidden">
        <VideoTable videos={videos} />
      </div>
    </>
  );
}
