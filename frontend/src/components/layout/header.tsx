"use client";

import { Search, Bell } from "lucide-react";
import { cn } from "@/lib/utils";

interface HeaderProps {
  onOpenCommandPalette?: () => void;
  className?: string;
}

export function Header({ onOpenCommandPalette, className }: HeaderProps) {
  return (
    <header
      className={cn(
        "sticky top-0 z-30 flex h-14 items-center justify-between gap-4 border-b border-white/[0.06] bg-[#0d0d0d]/70 px-6 backdrop-blur-xl",
        className
      )}
    >
      {/* Left: Breadcrumb area */}
      <div className="flex items-center gap-2 text-sm">
        <span className="text-[#666]">AIVidio</span>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        {/* Search trigger */}
        <button
          onClick={onOpenCommandPalette}
          className="flex h-9 items-center gap-2 rounded-xl border border-white/[0.08] bg-white/[0.03] px-3 text-sm text-[#666] transition-colors duration-150 hover:border-white/[0.15] hover:text-[#999]"
          aria-label="Open command palette"
        >
          <Search className="h-3.5 w-3.5" strokeWidth={1.5} />
          <span className="hidden sm:inline">Search</span>
          <kbd className="ml-2 hidden rounded-md border border-white/[0.08] bg-white/[0.04] px-1.5 py-0.5 text-[10px] font-medium text-[#666] sm:inline-block">
            Cmd+K
          </kbd>
        </button>

        {/* Notifications */}
        <button
          className="relative flex h-9 w-9 items-center justify-center rounded-xl text-[#666] transition-colors duration-150 hover:text-[#999] hover:bg-white/[0.06]"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" strokeWidth={1.5} />
        </button>

        {/* User avatar */}
        <button
          className="flex h-8 w-8 items-center justify-center rounded-full bg-[#2a2a2a] text-xs font-medium text-[#999] transition-colors hover:bg-white/[0.1]"
          aria-label="User menu"
        >
          CO
        </button>
      </div>
    </header>
  );
}
