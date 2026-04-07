"use client";

import { cn } from "@/lib/utils";

interface LogoProps {
  size?: "sm" | "md" | "lg" | "xl";
  showText?: boolean;
  className?: string;
}

const sizes = {
  sm: { icon: "h-7 w-7 rounded-lg", text: "text-sm", fontSize: "text-[11px]" },
  md: { icon: "h-9 w-9 rounded-xl", text: "text-base", fontSize: "text-xs" },
  lg: { icon: "h-12 w-12 rounded-xl", text: "text-xl", fontSize: "text-sm" },
  xl: { icon: "h-16 w-16 rounded-2xl", text: "text-2xl", fontSize: "text-lg" },
};

export function Logo({ size = "md", showText = true, className }: LogoProps) {
  const s = sizes[size];

  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      {/* Icon mark */}
      <div
        className={cn(
          s.icon,
          "flex items-center justify-center",
          "bg-gradient-to-br from-[#10a37f] to-[#0d8c6d]",
          "shadow-lg shadow-[#10a37f]/20"
        )}
      >
        <span
          className={cn(
            s.fontSize,
            "font-extrabold text-white tracking-tight"
          )}
        >
          Ai
        </span>
      </div>

      {/* Wordmark */}
      {showText && (
        <span
          className={cn(
            s.text,
            "font-bold tracking-tight text-[#fafafa]"
          )}
        >
          AIVidio
        </span>
      )}
    </div>
  );
}
