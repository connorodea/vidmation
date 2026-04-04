"use client";

import { useEffect, useState } from "react";
import { DollarSign, TrendingUp, Film, Cpu, BarChart3 } from "lucide-react";
import type { CostSummary } from "@/types";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/page-header";
import { CostChart } from "@/components/analytics/cost-chart";

interface AnalyticsStatCardProps {
  label: string;
  value: string;
  icon: React.ReactNode;
  sublabel?: string;
}

function AnalyticsStatCard({ label, value, icon, sublabel }: AnalyticsStatCardProps) {
  return (
    <div className="rounded-2xl border border-white/[0.08] bg-[#1a1a1a] p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-[#666] uppercase tracking-wider">
            {label}
          </p>
          <p className="mt-2 text-2xl font-semibold tabular-nums text-[#ececec]">
            {value}
          </p>
          {sublabel && (
            <p className="mt-1 text-xs text-[#666]">{sublabel}</p>
          )}
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/[0.06]">
          {icon}
        </div>
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  const [costData, setCostData] = useState<CostSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getCosts()
      .then((data) => setCostData(data as CostSummary))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const totalCost = costData?.total_cost ?? 0;
  const totalCalls = costData?.total_calls ?? 0;
  const avgCost = totalCalls > 0 ? totalCost / totalCalls : 0;
  const serviceCount = costData ? Object.keys(costData.by_service).length : 0;

  const todayCost =
    costData?.daily_trend?.length
      ? costData.daily_trend[costData.daily_trend.length - 1]?.cost ?? 0
      : 0;

  const sortedServices = costData
    ? Object.entries(costData.by_service).sort(([, a], [, b]) => b - a)
    : [];

  return (
    <div className="min-h-screen">
      <div className="max-w-[1280px] mx-auto px-6 py-10">
        <PageHeader
          title="Analytics"
          description="Cost tracking and usage insights"
        />

        {/* Stat cards */}
        <div className="mt-8 grid grid-cols-2 sm:grid-cols-4 gap-3">
          {loading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="h-[112px] animate-pulse rounded-2xl border border-white/[0.08] bg-[#1a1a1a]"
              />
            ))
          ) : (
            <>
              <AnalyticsStatCard
                label="Monthly Spend"
                value={`$${totalCost.toFixed(2)}`}
                icon={<DollarSign className="h-5 w-5 text-[#10a37f]" />}
                sublabel={`${totalCalls} total calls`}
              />
              <AnalyticsStatCard
                label="Today's Spend"
                value={`$${todayCost.toFixed(2)}`}
                icon={<TrendingUp className="h-5 w-5 text-[#6366f1]" />}
              />
              <AnalyticsStatCard
                label="Avg Cost / Video"
                value={`$${avgCost.toFixed(2)}`}
                icon={<Film className="h-5 w-5 text-[#f59e0b]" />}
              />
              <AnalyticsStatCard
                label="Active Services"
                value={String(serviceCount)}
                icon={<Cpu className="h-5 w-5 text-[#ec4899]" />}
              />
            </>
          )}
        </div>

        {error && (
          <div className="mt-6 rounded-2xl border border-[#ef4444]/20 bg-[#ef4444]/5 p-6">
            <p className="text-sm text-[#ef4444]">{error}</p>
          </div>
        )}

        {/* Daily cost chart */}
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Daily Cost</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="h-[300px] animate-pulse rounded-xl bg-white/[0.03]" />
            ) : (
              <CostChart data={costData?.daily_trend ?? []} />
            )}
          </CardContent>
        </Card>

        {/* Service breakdown + top videos */}
        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          {/* Service breakdown */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-[#666]" />
                Service Breakdown
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-3">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <div
                      key={i}
                      className="h-8 animate-pulse rounded-lg bg-white/[0.03]"
                    />
                  ))}
                </div>
              ) : sortedServices.length === 0 ? (
                <p className="py-8 text-center text-sm text-[#666]">
                  No usage data yet
                </p>
              ) : (
                <div className="space-y-4">
                  {sortedServices.map(([service, cost]) => {
                    const pct = totalCost > 0 ? (cost / totalCost) * 100 : 0;
                    return (
                      <div key={service}>
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-[#ececec]">{service}</span>
                          <span className="font-mono text-xs tabular-nums text-[#999]">
                            ${cost.toFixed(2)}
                          </span>
                        </div>
                        <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-white/[0.06]">
                          <div
                            className="h-full rounded-full bg-[#10a37f] transition-all duration-300"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Top videos by cost */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Film className="h-4 w-4 text-[#666]" />
                Top Videos by Cost
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-3">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div
                      key={i}
                      className="h-8 animate-pulse rounded-lg bg-white/[0.03]"
                    />
                  ))}
                </div>
              ) : sortedServices.length === 0 ? (
                <p className="py-8 text-center text-sm text-[#666]">
                  No video cost data yet
                </p>
              ) : (
                <div className="space-y-1">
                  {sortedServices.slice(0, 5).map(([service, cost], i) => (
                    <div
                      key={service}
                      className="flex items-center justify-between rounded-lg px-3 py-2.5 transition-colors hover:bg-white/[0.03]"
                    >
                      <div className="flex items-center gap-3">
                        <span className="flex h-6 w-6 items-center justify-center rounded-md bg-white/[0.06] font-mono text-[11px] tabular-nums text-[#666]">
                          {i + 1}
                        </span>
                        <span className="text-sm text-[#ececec]">
                          {service}
                        </span>
                      </div>
                      <span className="font-mono text-xs tabular-nums text-[#999]">
                        ${cost.toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
