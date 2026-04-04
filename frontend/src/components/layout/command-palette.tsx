"use client";

import { useState, useCallback, useEffect, useRef, useMemo } from "react";
import { useRouter } from "next/navigation";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import {
  Search,
  Video,
  Plus,
  LayoutDashboard,
  BarChart3,
  Tv2,
  Cog,
  FileText,
  ArrowRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useKeyboardShortcut } from "@/hooks/use-keyboard-shortcut";

interface CommandItem {
  id: string;
  label: string;
  icon: React.ElementType;
  section: "quick" | "pages" | "recent";
  href?: string;
  action?: () => void;
}

const defaultItems: CommandItem[] = [
  { id: "new-video", label: "Create new video", icon: Plus, section: "quick" },
  { id: "new-channel", label: "Add channel", icon: Tv2, section: "quick" },
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, section: "pages", href: "/" },
  { id: "videos", label: "Videos", icon: Video, section: "pages", href: "/videos" },
  { id: "channels", label: "Channels", icon: Tv2, section: "pages", href: "/channels" },
  { id: "jobs", label: "Jobs", icon: Cog, section: "pages", href: "/jobs" },
  { id: "analytics", label: "Analytics", icon: BarChart3, section: "pages", href: "/analytics" },
  { id: "content", label: "Content Library", icon: FileText, section: "pages", href: "/content" },
];

const sectionLabels: Record<string, string> = {
  quick: "Quick Actions",
  recent: "Recent",
  pages: "Pages",
};

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  const filtered = defaultItems.filter((item) =>
    item.label.toLowerCase().includes(query.toLowerCase())
  );

  const sections = ["quick", "pages", "recent"].filter((s) =>
    filtered.some((item) => item.section === s)
  );

  const handleSelect = useCallback(
    (item: CommandItem) => {
      if (item.href) {
        router.push(item.href);
      }
      item.action?.();
      onOpenChange(false);
      setQuery("");
      setActiveIndex(0);
    },
    [onOpenChange, router]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((i) => (i + 1) % filtered.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((i) => (i - 1 + filtered.length) % filtered.length);
      } else if (e.key === "Enter" && filtered[activeIndex]) {
        e.preventDefault();
        handleSelect(filtered[activeIndex]);
      }
    },
    [filtered, activeIndex, handleSelect]
  );

  // Reset on open
  useEffect(() => {
    if (open) {
      setQuery("");
      setActiveIndex(0);
      // Focus input after dialog animation
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  // Scroll active item into view
  useEffect(() => {
    if (!listRef.current) return;
    const activeEl = listRef.current.querySelector("[data-active=true]");
    activeEl?.scrollIntoView({ block: "nearest" });
  }, [activeIndex]);

  let itemCounter = 0;

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <DialogPrimitive.Content
          className="fixed left-[50%] top-[20%] z-50 w-full max-w-xl translate-x-[-50%] rounded-2xl border border-white/[0.08] bg-[#1a1a1a] shadow-2xl shadow-black/40 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=open]:slide-in-from-left-1/2"
          onKeyDown={handleKeyDown}
        >
          <DialogPrimitive.Title className="sr-only">
            Command Palette
          </DialogPrimitive.Title>
          <DialogPrimitive.Description className="sr-only">
            Search for pages, actions, and commands
          </DialogPrimitive.Description>

          {/* Search input */}
          <div className="flex items-center gap-3 border-b border-white/[0.06] px-4">
            <Search className="h-4 w-4 shrink-0 text-[#666]" strokeWidth={1.5} />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setActiveIndex(0);
              }}
              placeholder="Search pages, actions..."
              className="flex-1 bg-transparent py-4 text-sm text-[#ececec] placeholder:text-[#666] outline-none"
            />
            <kbd className="rounded-md border border-white/[0.08] bg-white/[0.04] px-1.5 py-0.5 text-[10px] font-medium text-[#666]">
              ESC
            </kbd>
          </div>

          {/* Results */}
          <div ref={listRef} className="max-h-80 overflow-y-auto p-2">
            {filtered.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-[#666]">
                No results found for &ldquo;{query}&rdquo;
              </div>
            ) : (
              sections.map((section) => {
                const sectionItems = filtered.filter(
                  (item) => item.section === section
                );
                if (sectionItems.length === 0) return null;

                return (
                  <div key={section} className="mb-2">
                    <div className="px-3 py-1.5 text-xs font-medium text-[#666]">
                      {sectionLabels[section]}
                    </div>
                    {sectionItems.map((item) => {
                      const currentIndex = itemCounter;
                      itemCounter++;
                      const isActive = currentIndex === activeIndex;

                      return (
                        <button
                          key={item.id}
                          data-active={isActive}
                          onClick={() => handleSelect(item)}
                          onMouseEnter={() => setActiveIndex(currentIndex)}
                          className={cn(
                            "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-[#999] transition-colors duration-100",
                            isActive && "bg-white/[0.06] text-[#ececec]"
                          )}
                        >
                          <item.icon className="h-4 w-4 shrink-0" strokeWidth={1.5} />
                          <span className="flex-1 text-left">{item.label}</span>
                          {isActive && (
                            <ArrowRight className="h-3 w-3 text-[#666]" />
                          )}
                        </button>
                      );
                    })}
                  </div>
                );
              })
            )}
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

/**
 * Wrapper that manages its own open state and registers Cmd+K.
 * Usage: <CommandPaletteWithShortcut />
 */
export function CommandPaletteWithShortcut() {
  const [open, setOpen] = useState(false);

  useKeyboardShortcut({ key: "k", meta: true }, () => setOpen(true));

  return <CommandPalette open={open} onOpenChange={setOpen} />;
}
