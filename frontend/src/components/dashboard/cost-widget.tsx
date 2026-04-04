"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { CostSummary } from "@/types";

const MONTHLY_BUDGET = 50;

export function CostWidget() {
  const [costs, setCosts] = useState<CostSummary | null>(null);

  useEffect(() => {
    api.getCosts({ period: "month" }).then((data) => {
      setCosts(data as CostSummary);
    }).catch(() => {
      // Silently fail -- widget is non-critical
    });
  }, []);

  const total = costs?.total_cost ?? 0;
  const pct = Math.min((total / MONTHLY_BUDGET) * 100, 100);

  const barColor =
    pct >= 85
      ? "bg-[#ef4444]"
      : pct >= 60
        ? "bg-[#f59e0b]"
        : "bg-[#10a37f]";

  const aiCost = costs?.by_service?.["openai"] ?? 0;
  const ttsCost = costs?.by_service?.["tts"] ?? 0;
  const mediaCost = costs?.by_service?.["media"] ?? 0;

  return (
    <div className="rounded-2xl border border-white/[0.08] bg-[#1a1a1a] p-6">
      <h3 className="text-xs font-medium uppercase tracking-wider text-[#666] mb-5">
        Monthly Cost
      </h3>

      <div className="mb-1">
        <span className="text-2xl font-semibold tabular-nums text-[#ececec]">
          ${total.toFixed(2)}
        </span>
        <span className="text-xs text-[#666] ml-1.5">
          of ${MONTHLY_BUDGET} budget
        </span>
      </div>

      <div className="w-full h-1.5 rounded-full bg-white/[0.06] overflow-hidden mt-3 mb-6">
        <div
          className={cn("h-full rounded-full progress-bar", barColor)}
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="grid grid-cols-3 gap-3">
        <CostLine label="AI / LLM" value={aiCost} />
        <CostLine label="TTS" value={ttsCost} />
        <CostLine label="Media" value={mediaCost} />
      </div>
    </div>
  );
}

function CostLine({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-[11px] text-[#666] mb-0.5">{label}</p>
      <p className="text-xs tabular-nums text-[#999]">${value.toFixed(2)}</p>
    </div>
  );
}
