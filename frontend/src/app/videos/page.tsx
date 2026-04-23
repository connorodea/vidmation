import { Suspense } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { VideoListContent } from "@/components/videos/video-list-content";

export default function VideosPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  return (
    <div className="max-w-[1200px]">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-semibold text-[#ececec]">Videos</h1>
        <Button asChild>
          <Link href="/videos/new">New Video</Link>
        </Button>
      </div>

      {/* Content with filter tabs and table */}
      <Suspense
        fallback={
          <div className="space-y-3 mt-12">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="h-12 rounded-lg bg-white/[0.04] animate-pulse"
              />
            ))}
          </div>
        }
      >
        <VideoListContent searchParamsPromise={searchParams} />
      </Suspense>
    </div>
  );
}
