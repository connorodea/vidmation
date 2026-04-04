import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  trend?: {
    value: number;
    direction: "up" | "down";
  };
  className?: string;
}

export function StatCard({ label, value, trend, className }: StatCardProps) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-white/[0.08] bg-[#1a1a1a] p-6",
        className
      )}
    >
      <p className="text-xs font-medium text-[#666] uppercase tracking-wider">
        {label}
      </p>
      <div className="mt-2 flex items-end gap-2">
        <span className="text-2xl font-semibold text-[#ececec] tabular-nums">
          {value}
        </span>
        {trend && (
          <span
            className={cn(
              "mb-0.5 inline-flex items-center gap-0.5 text-xs font-medium",
              trend.direction === "up" ? "text-[#10a37f]" : "text-[#ef4444]"
            )}
          >
            {trend.direction === "up" ? (
              <TrendingUp className="h-3 w-3" />
            ) : (
              <TrendingDown className="h-3 w-3" />
            )}
            {trend.value}%
          </span>
        )}
      </div>
    </div>
  );
}
