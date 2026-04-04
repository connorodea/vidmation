"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus, Tv2 } from "lucide-react";
import type { Channel } from "@/types";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { ChannelCard } from "@/components/channels/channel-card";

export default function ChannelsPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getChannels()
      .then((data) => setChannels(data as Channel[]))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen">
      <div className="max-w-[1280px] mx-auto px-6 py-10">
        <PageHeader
          title="Channels"
          description="Manage your YouTube channels and profiles"
          action={
            <Button asChild>
              <Link href="/channels/new">
                <Plus className="h-4 w-4" />
                Add Channel
              </Link>
            </Button>
          }
        />

        <div className="mt-8">
          {loading && (
            <div className="grid gap-4 lg:grid-cols-3 md:grid-cols-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div
                  key={i}
                  className="h-[140px] animate-pulse rounded-2xl border border-white/[0.08] bg-[#1a1a1a]"
                />
              ))}
            </div>
          )}

          {error && (
            <div className="rounded-2xl border border-[#ef4444]/20 bg-[#ef4444]/5 p-6">
              <p className="text-sm text-[#ef4444]">{error}</p>
            </div>
          )}

          {!loading && !error && channels.length === 0 && (
            <EmptyState
              icon={Tv2}
              title="No channels yet"
              description="Create your first channel to start generating videos."
              action={
                <Button asChild>
                  <Link href="/channels/new">
                    <Plus className="h-4 w-4" />
                    Add Channel
                  </Link>
                </Button>
              }
            />
          )}

          {!loading && !error && channels.length > 0 && (
            <div className="grid gap-4 lg:grid-cols-3 md:grid-cols-2">
              {channels.map((channel) => (
                <ChannelCard key={channel.id} channel={channel} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
