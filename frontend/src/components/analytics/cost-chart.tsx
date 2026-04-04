"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

interface CostChartProps {
  data: { date: string; cost: number }[];
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: { value?: number }[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-lg border border-white/[0.08] bg-[#2a2a2a] px-3.5 py-2.5 shadow-lg">
      <p className="text-[12px] text-[#666]">{label}</p>
      <p className="mt-0.5 text-sm font-medium text-[#ececec]">
        ${payload[0].value?.toFixed(2)}
      </p>
    </div>
  );
}

export function CostChart({ data }: CostChartProps) {
  if (!data.length) {
    return (
      <div className="flex h-[300px] items-center justify-center text-sm text-[#666]">
        No cost data available yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart
        data={data}
        margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
      >
        <XAxis
          dataKey="date"
          axisLine={false}
          tickLine={false}
          tick={{ fill: "#666", fontSize: 12 }}
          dy={8}
        />
        <YAxis
          axisLine={false}
          tickLine={false}
          tick={{ fill: "#666", fontSize: 12 }}
          tickFormatter={(v: number) => `$${v}`}
          dx={-4}
          width={48}
        />
        <Tooltip content={<CustomTooltip />} cursor={false} />
        <defs>
          <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#10a37f" stopOpacity={0.12} />
            <stop offset="100%" stopColor="#10a37f" stopOpacity={0} />
          </linearGradient>
        </defs>
        <Line
          type="monotone"
          dataKey="cost"
          stroke="#10a37f"
          strokeWidth={2}
          dot={false}
          activeDot={{
            r: 4,
            fill: "#10a37f",
            stroke: "#0d0d0d",
            strokeWidth: 2,
          }}
          fill="url(#costGradient)"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
