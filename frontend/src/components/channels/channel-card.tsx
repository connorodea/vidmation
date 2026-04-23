"use client";

import Link from "next/link";
import type { Channel } from "@/types";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatusDot } from "@/components/shared/status-dot";

function getMonogram(name: string): string {
  return name
    .split(/\s+/)
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

function getMonogramColor(name: string): string {
  const colors = [
    "bg-[#10a37f]/20 text-[#10a37f]",
    "bg-[#6366f1]/20 text-[#6366f1]",
    "bg-[#f59e0b]/20 text-[#f59e0b]",
    "bg-[#ef4444]/20 text-[#ef4444]",
    "bg-[#ec4899]/20 text-[#ec4899]",
    "bg-[#8b5cf6]/20 text-[#8b5cf6]",
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

interface ChannelCardProps {
  channel: Channel;
}

export function ChannelCard({ channel }: ChannelCardProps) {
  return (
    <Link href={`/channels/${channel.id}`}>
      <Card className="group cursor-pointer transition-all duration-150 hover:border-white/[0.15] hover:bg-[#1a1a1a]/80">
        <CardContent className="p-6">
          <div className="flex items-start gap-4">
            <div
              className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-sm font-semibold ${getMonogramColor(channel.name)}`}
            >
              {getMonogram(channel.name)}
            </div>

            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2.5">
                <h3 className="truncate text-[15px] font-medium text-[#ececec]">
                  {channel.name}
                </h3>
                <StatusDot status={channel.is_active ? "ready" : "draft"} />
              </div>

              <p className="mt-1 truncate text-[13px] text-[#666]">
                {channel.profile_path}
              </p>

              <div className="mt-3 flex items-center gap-2">
                {channel.youtube_channel_id ? (
                  <Badge variant="success">YouTube linked</Badge>
                ) : (
                  <Badge>Not linked</Badge>
                )}
                <Badge variant={channel.is_active ? "success" : "default"}>
                  {channel.is_active ? "Active" : "Inactive"}
                </Badge>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
