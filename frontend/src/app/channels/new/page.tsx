"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function NewChannelPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [profilePath, setProfilePath] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;

    setSubmitting(true);
    setError(null);

    try {
      await api.createChannel({
        name: name.trim(),
        profile_path: profilePath.trim() || undefined,
      });
      router.push("/channels");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create channel");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen">
      <div className="max-w-lg mx-auto px-6 py-10">
        {/* Back link */}
        <Link
          href="/channels"
          className="inline-flex items-center gap-1.5 text-sm text-[#666] transition-colors hover:text-[#ececec]"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Channels
        </Link>

        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Add Channel</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <label
                  htmlFor="channel-name"
                  className="block text-sm font-medium text-[#ececec]"
                >
                  Channel name
                </label>
                <Input
                  id="channel-name"
                  placeholder="My Automation Channel"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  autoFocus
                />
              </div>

              <div className="space-y-2">
                <label
                  htmlFor="profile-path"
                  className="block text-sm font-medium text-[#ececec]"
                >
                  Profile path
                </label>
                <Input
                  id="profile-path"
                  placeholder="/profiles/default"
                  value={profilePath}
                  onChange={(e) => setProfilePath(e.target.value)}
                />
                <p className="text-xs text-[#666]">
                  Path to the configuration profile for this channel.
                </p>
              </div>

              {error && (
                <div className="rounded-xl border border-[#ef4444]/20 bg-[#ef4444]/5 px-4 py-3">
                  <p className="text-sm text-[#ef4444]">{error}</p>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <Button type="button" variant="ghost" asChild>
                  <Link href="/channels">Cancel</Link>
                </Button>
                <Button type="submit" disabled={!name.trim() || submitting}>
                  {submitting && (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  )}
                  Create Channel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
