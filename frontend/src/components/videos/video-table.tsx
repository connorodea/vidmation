"use client";

import { useRouter } from "next/navigation";
import { useState, useMemo } from "react";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { StatusDot } from "@/components/shared/status-dot";
import { formatDuration, formatDate, truncate } from "@/lib/utils";
import type { Video } from "@/types";

type SortKey = "title" | "format" | "status" | "created_at";
type SortDir = "asc" | "desc";

export function VideoTable({ videos }: { videos: Video[] }) {
  const router = useRouter();
  const [sortKey, setSortKey] = useState<SortKey>("created_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const sorted = useMemo(() => {
    return [...videos].sort((a, b) => {
      let cmp = 0;
      if (sortKey === "created_at") {
        cmp =
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      } else {
        cmp = (a[sortKey] ?? "").localeCompare(b[sortKey] ?? "");
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [videos, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  if (videos.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 px-4">
        <p className="text-sm text-[#666] mb-1">No videos yet</p>
        <p className="text-xs text-[#666]">
          Create your first video to get started.
        </p>
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <SortableHead
            label="Title"
            sortKey="title"
            current={sortKey}
            dir={sortDir}
            onSort={toggleSort}
          />
          <TableHead>Channel</TableHead>
          <SortableHead
            label="Format"
            sortKey="format"
            current={sortKey}
            dir={sortDir}
            onSort={toggleSort}
          />
          <TableHead>Duration</TableHead>
          <SortableHead
            label="Status"
            sortKey="status"
            current={sortKey}
            dir={sortDir}
            onSort={toggleSort}
          />
          <SortableHead
            label="Created"
            sortKey="created_at"
            current={sortKey}
            dir={sortDir}
            onSort={toggleSort}
          />
        </TableRow>
      </TableHeader>
      <TableBody>
        {sorted.map((video) => (
          <TableRow
            key={video.id}
            className="cursor-pointer"
            onClick={() => router.push(`/videos/${video.id}`)}
            role="link"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter") router.push(`/videos/${video.id}`);
            }}
          >
            <TableCell className="font-medium text-[#ececec]">
              {truncate(video.title, 48)}
            </TableCell>
            <TableCell className="text-[#999]">
              {video.channel?.name ?? "--"}
            </TableCell>
            <TableCell className="text-[#999] capitalize">
              {video.format}
            </TableCell>
            <TableCell className="tabular-nums text-[#999]">
              {video.duration_seconds
                ? formatDuration(video.duration_seconds)
                : "--"}
            </TableCell>
            <TableCell>
              <div className="flex items-center gap-2">
                <StatusDot status={video.status} />
                <span className="capitalize text-[#999]">{video.status}</span>
              </div>
            </TableCell>
            <TableCell className="text-[#666]">
              {formatDate(video.created_at)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function SortableHead({
  label,
  sortKey,
  current,
  dir,
  onSort,
}: {
  label: string;
  sortKey: SortKey;
  current: SortKey;
  dir: SortDir;
  onSort: (key: SortKey) => void;
}) {
  const active = current === sortKey;
  return (
    <TableHead>
      <button
        onClick={() => onSort(sortKey)}
        className="inline-flex items-center gap-1 hover:text-[#999] transition-colors duration-100"
      >
        {label}
        {active && (
          <svg
            width="10"
            height="10"
            viewBox="0 0 10 10"
            fill="currentColor"
            className={dir === "desc" ? "rotate-180" : ""}
          >
            <path d="M5 2L8 7H2L5 2Z" />
          </svg>
        )}
      </button>
    </TableHead>
  );
}
