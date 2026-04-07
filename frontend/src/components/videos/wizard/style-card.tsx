"use client";

import { cn } from "@/lib/utils";
import { Check } from "lucide-react";

interface StyleCardProps {
  title: string;
  description: string;
  gradient: string;
  icon: React.ReactNode;
  selected: boolean;
  onSelect: () => void;
}

export function StyleCard({
  title,
  description,
  gradient,
  icon,
  selected,
  onSelect,
}: StyleCardProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "group relative flex flex-col rounded-2xl border p-0 overflow-hidden text-left transition-all duration-200",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#10a37f] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0d0d0d]",
        selected
          ? "border-[#10a37f] shadow-[0_0_0_1px_#10a37f]"
          : "border-white/[0.08] hover:border-white/[0.15]"
      )}
    >
      {/* Preview area */}
      <div
        className={cn(
          "relative h-28 w-full flex items-center justify-center transition-opacity duration-200",
          gradient
        )}
      >
        <div className="text-white/80 transition-transform duration-200 group-hover:scale-110">
          {icon}
        </div>

        {/* Selected check */}
        {selected && (
          <div className="absolute top-3 right-3 flex h-6 w-6 items-center justify-center rounded-full bg-[#10a37f]">
            <Check className="h-3.5 w-3.5 text-white" />
          </div>
        )}
      </div>

      {/* Text content */}
      <div className="p-4 bg-[#1a1a1a]">
        <p className="text-sm font-medium text-[#ececec]">{title}</p>
        <p className="text-xs text-[#666] mt-1 leading-relaxed">{description}</p>
      </div>
    </button>
  );
}
