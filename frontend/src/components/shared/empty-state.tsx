import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-2xl border border-white/[0.08] bg-[#1a1a1a] p-12 text-center",
        className
      )}
    >
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-white/[0.06]">
        <Icon className="h-6 w-6 text-[#666]" strokeWidth={1.5} />
      </div>
      <h3 className="text-base font-semibold text-[#ececec]">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-[#666]">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
