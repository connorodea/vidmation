"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Play, Link2, Calendar, Tv2, Activity } from "lucide-react";
import type { Channel } from "@/types";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

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

export default function ChannelDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [channel, setChannel] = useState<Channel | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!params.id) return;
    api
      .getChannel(params.id)
      .then((data) => setChannel(data as Channel))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [params.id]);

  if (loading) {
    return (
      <div className="min-h-screen">
        <div className="max-w-[960px] mx-auto px-6 py-10">
          <div className="h-5 w-32 animate-pulse rounded-lg bg-white/[0.06]" />
          <div className="mt-8 h-20 animate-pulse rounded-2xl border border-white/[0.08] bg-[#1a1a1a]" />
          <div className="mt-6 grid gap-6 md:grid-cols-2">
            <div className="h-52 animate-pulse rounded-2xl border border-white/[0.08] bg-[#1a1a1a]" />
            <div className="h-52 animate-pulse rounded-2xl border border-white/[0.08] bg-[#1a1a1a]" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !channel) {
    return (
      <div className="min-h-screen">
        <div className="max-w-[960px] mx-auto px-6 py-10">
          <Link
            href="/channels"
            className="inline-flex items-center gap-1.5 text-sm text-[#666] transition-colors hover:text-[#ececec]"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Channels
          </Link>
          <div className="mt-8 rounded-2xl border border-[#ef4444]/20 bg-[#ef4444]/5 p-6">
            <p className="text-sm text-[#ef4444]">
              {error || "Channel not found"}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="max-w-[960px] mx-auto px-6 py-10">
        {/* Back link */}
        <Link
          href="/channels"
          className="inline-flex items-center gap-1.5 text-sm text-[#666] transition-colors hover:text-[#ececec]"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Channels
        </Link>

        {/* Channel header */}
        <div className="mt-8 flex items-center gap-4">
          <div
            className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-xl text-base font-semibold ${getMonogramColor(channel.name)}`}
          >
            {getMonogram(channel.name)}
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-[#ececec]">
              {channel.name}
            </h1>
            <p className="mt-0.5 text-sm text-[#666]">
              {channel.profile_path}
            </p>
          </div>
        </div>

        {/* Cards */}
        <div className="mt-8 grid gap-6 md:grid-cols-2">
          {/* Details */}
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="space-y-4">
                <div className="flex items-center justify-between">
                  <dt className="flex items-center gap-2 text-sm text-[#666]">
                    <Activity className="h-4 w-4" />
                    Status
                  </dt>
                  <dd>
                    <Badge variant={channel.is_active ? "success" : "default"}>
                      {channel.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </dd>
                </div>

                <div className="h-px bg-white/[0.06]" />

                <div className="flex items-center justify-between">
                  <dt className="flex items-center gap-2 text-sm text-[#666]">
                    <Tv2 className="h-4 w-4" />
                    YouTube
                  </dt>
                  <dd>
                    {channel.youtube_channel_id ? (
                      <Badge variant="success">
                        {channel.youtube_channel_id}
                      </Badge>
                    ) : (
                      <span className="text-sm text-[#666]">Not linked</span>
                    )}
                  </dd>
                </div>

                <div className="h-px bg-white/[0.06]" />

                <div className="flex items-center justify-between">
                  <dt className="flex items-center gap-2 text-sm text-[#666]">
                    <Calendar className="h-4 w-4" />
                    Created
                  </dt>
                  <dd className="text-sm text-[#ececec]">
                    {formatDate(channel.created_at)}
                  </dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          {/* Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <Button
                  className="w-full justify-start"
                  onClick={() =>
                    router.push(`/videos/new?channel_id=${channel.id}`)
                  }
                >
                  <Play className="h-4 w-4" />
                  Generate Video
                </Button>

                <Button
                  variant="secondary"
                  className="w-full justify-start"
                  disabled={!!channel.youtube_channel_id}
                >
                  <Link2 className="h-4 w-4" />
                  {channel.youtube_channel_id
                    ? "YouTube Connected"
                    : "Link YouTube Account"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
