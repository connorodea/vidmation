import { cn } from "@/lib/utils";

type Status = "uploaded" | "generating" | "failed" | "ready" | "queued" | "draft" | "running" | "completed" | "cancelled";

const statusConfig: Record<Status, { color: string; pulse?: boolean; label: string }> = {
  uploaded: { color: "bg-[#10a37f]", label: "Uploaded" },
  generating: { color: "bg-[#6366f1]", pulse: true, label: "Generating" },
  running: { color: "bg-[#6366f1]", pulse: true, label: "Running" },
  failed: { color: "bg-[#ef4444]", label: "Failed" },
  ready: { color: "bg-[#f59e0b]", label: "Ready" },
  queued: { color: "bg-[#f59e0b]", label: "Queued" },
  completed: { color: "bg-[#10a37f]", label: "Completed" },
  cancelled: { color: "bg-[#666]", label: "Cancelled" },
  draft: { color: "bg-[#666]", label: "Draft" },
};

interface StatusDotProps {
  status: Status;
  showLabel?: boolean;
  className?: string;
}

export function StatusDot({ status, showLabel = false, className }: StatusDotProps) {
  const config = statusConfig[status] || statusConfig.draft;

  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <span
        className={cn(
          "h-2 w-2 rounded-full shrink-0",
          config.color,
          config.pulse && "animate-pulse-dot"
        )}
        aria-label={config.label}
      />
      {showLabel && (
        <span className="text-xs text-[#999] capitalize">{config.label}</span>
      )}
    </span>
  );
}
