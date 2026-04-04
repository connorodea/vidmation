import { Suspense } from "react";
import Link from "next/link";
import { ActiveJobs } from "@/components/dashboard/active-jobs";
import { CostWidget } from "@/components/dashboard/cost-widget";
import { DashboardVideos } from "@/components/dashboard/recent-videos";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function getStats() {
  try {
    const [videosRes, channelsRes, jobsRes] = await Promise.all([
      fetch(`${API_BASE}/videos`, { cache: "no-store" }),
      fetch(`${API_BASE}/channels`, { cache: "no-store" }),
      fetch(`${API_BASE}/jobs?status=running`, { cache: "no-store" }),
    ]);

    const videos = videosRes.ok ? await videosRes.json() : [];
    const channels = channelsRes.ok ? await channelsRes.json() : [];
    const activeJobs = jobsRes.ok ? await jobsRes.json() : [];

    const uploaded = Array.isArray(videos)
      ? videos.filter((v: { status: string }) => v.status === "uploaded").length
      : 0;

    return {
      totalVideos: Array.isArray(videos) ? videos.length : 0,
      uploaded,
      activeJobs: Array.isArray(activeJobs) ? activeJobs.length : 0,
      channels: Array.isArray(channels) ? channels.length : 0,
    };
  } catch {
    return { totalVideos: 0, uploaded: 0, activeJobs: 0, channels: 0 };
  }
}

export default async function DashboardPage() {
  const stats = await getStats();

  return (
    <div className="max-w-[1200px]">
      <h1 className="text-2xl font-semibold text-[#ececec] mb-8">Dashboard</h1>

      <div className="flex flex-col lg:flex-row gap-8">
        {/* Main content */}
        <div className="flex-1 min-w-0 space-y-8">
          {/* Stats row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatCard label="Total Videos" value={stats.totalVideos} />
            <StatCard label="Uploaded" value={stats.uploaded} />
            <StatCard label="Active Jobs" value={stats.activeJobs} />
            <StatCard label="Channels" value={stats.channels} />
          </div>

          {/* Quick actions */}
          <div className="flex items-center gap-6">
            <QuickLink href="/videos/new" label="Generate Video" />
            <QuickLink href="/videos" label="Batch Import" />
            <QuickLink href="/analytics" label="View Analytics" />
          </div>

          {/* Active jobs (polling client component) */}
          <Suspense fallback={null}>
            <ActiveJobs />
          </Suspense>

          {/* Recent videos */}
          <div>
            <h2 className="text-xs font-medium uppercase tracking-wider text-[#666] mb-3">
              Recent Videos
            </h2>
            <div className="rounded-2xl border border-white/[0.08] bg-[#1a1a1a] overflow-hidden">
              <Suspense
                fallback={
                  <div className="p-6 space-y-3">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <div
                        key={i}
                        className="h-11 rounded-lg bg-white/[0.04] animate-pulse"
                      />
                    ))}
                  </div>
                }
              >
                <DashboardVideos />
              </Suspense>
            </div>
          </div>
        </div>

        {/* Right sidebar */}
        <div className="w-full lg:w-80 shrink-0">
          <Suspense fallback={null}>
            <CostWidget />
          </Suspense>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-white/[0.08] bg-[#1a1a1a] px-5 py-4">
      <p className="text-2xl font-semibold tabular-nums text-[#ececec]">
        {value}
      </p>
      <p className="text-[11px] text-[#666] mt-1">{label}</p>
    </div>
  );
}

function QuickLink({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="text-sm text-[#666] hover:text-[#ececec] transition-colors duration-150 flex items-center gap-1"
    >
      {label}
      <svg
        width="14"
        height="14"
        viewBox="0 0 14 14"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="opacity-60"
      >
        <path d="M5 3L9 7L5 11" />
      </svg>
    </Link>
  );
}
