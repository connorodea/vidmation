"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  LayoutDashboard,
  Video,
  Tv2,
  Cog,
  BarChart3,
  FileText,
  Mic2,
  Calendar,
  PanelLeftClose,
  PanelLeft,
  Plus,
} from "lucide-react";

const navItems = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Videos", href: "/videos", icon: Video },
  { label: "Channels", href: "/channels", icon: Tv2 },
  { label: "Jobs", href: "/jobs", icon: Cog },
  { label: "Analytics", href: "/analytics", icon: BarChart3 },
  { label: "Content", href: "/content", icon: FileText },
  { label: "Voices", href: "/voices", icon: Mic2 },
  { label: "Schedule", href: "/schedule", icon: Calendar },
  { label: "Settings", href: "/settings", icon: Cog },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex flex-col border-r border-white/[0.06] bg-[#0d0d0d] transition-all duration-200 ease-out",
          collapsed ? "w-16" : "w-[260px]"
        )}
      >
        {/* Logo */}
        <div
          className={cn(
            "flex h-16 shrink-0 items-center gap-3 border-b border-white/[0.06] px-4",
            collapsed && "justify-center px-0"
          )}
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#10a37f] text-sm font-bold text-white">
            V
          </div>
          {!collapsed && (
            <span className="text-sm font-semibold tracking-wide text-[#ececec]">
              VIDMATION
            </span>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-2 py-3">
          <ul className="space-y-0.5">
            {navItems.map((item) => {
              const active = isActive(item.href);
              const linkContent = (
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-150 ease-out",
                    active
                      ? "bg-white/[0.06] text-white"
                      : "text-[#666] hover:text-[#999] hover:bg-white/[0.03]",
                    collapsed && "justify-center px-0"
                  )}
                >
                  <item.icon
                    className="h-5 w-5 shrink-0"
                    strokeWidth={1.5}
                  />
                  {!collapsed && <span>{item.label}</span>}
                </Link>
              );

              if (collapsed) {
                return (
                  <li key={item.href}>
                    <Tooltip>
                      <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
                      <TooltipContent side="right">
                        {item.label}
                      </TooltipContent>
                    </Tooltip>
                  </li>
                );
              }

              return <li key={item.href}>{linkContent}</li>;
            })}
          </ul>
        </nav>

        {/* Bottom section */}
        <div
          className={cn(
            "shrink-0 border-t border-white/[0.06] p-3 space-y-2",
            collapsed && "flex flex-col items-center"
          )}
        >
          {collapsed ? (
            <>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Link href="/videos/new">
                    <Button size="icon" className="w-10 h-10">
                      <Plus className="h-4 w-4" />
                    </Button>
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right">New Video</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={() => setCollapsed(false)}
                    className="flex h-10 w-10 items-center justify-center rounded-xl text-[#666] transition-colors hover:text-[#999] hover:bg-white/[0.06]"
                    aria-label="Expand sidebar"
                  >
                    <PanelLeft className="h-5 w-5" strokeWidth={1.5} />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="right">Expand</TooltipContent>
              </Tooltip>
            </>
          ) : (
            <>
              <Link href="/videos/new">
                <Button className="w-full gap-2" size="default">
                  <Plus className="h-4 w-4" />
                  New Video
                </Button>
              </Link>
              <button
                onClick={() => setCollapsed(true)}
                className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-[#666] transition-colors hover:text-[#999] hover:bg-white/[0.03]"
                aria-label="Collapse sidebar"
              >
                <PanelLeftClose className="h-5 w-5 shrink-0" strokeWidth={1.5} />
                <span>Collapse</span>
              </button>
            </>
          )}
        </div>
      </aside>
    </TooltipProvider>
  );
}
