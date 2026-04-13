"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Plus, MoreHorizontal, Settings, Trash2, ExternalLink } from "lucide-react"
import { cn } from "@/lib/utils"

const mockChannels = [
  {
    id: "ch_1",
    name: "Wealth Wisdom",
    niche: "finance",
    youtube_channel_id: "UC123456",
    video_count: 24,
  },
  {
    id: "ch_2",
    name: "Tech Explained",
    niche: "tech",
    youtube_channel_id: "UC789012",
    video_count: 18,
  },
  {
    id: "ch_3",
    name: "Daily Finance",
    niche: "finance",
    youtube_channel_id: null,
    video_count: 8,
  },
]

const niches = ["finance", "tech", "self_improvement", "business", "crypto", "health", "education"]

export default function ChannelsPage() {
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [newChannelName, setNewChannelName] = useState("")
  const [newChannelNiche, setNewChannelNiche] = useState("")

  const handleCreateChannel = () => {
    setIsCreateOpen(false)
    setNewChannelName("")
    setNewChannelNiche("")
  }

  return (
    <div className="p-8 lg:p-12">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-[32px] font-semibold tracking-tight">Channels</h1>
          <p className="mt-1 text-[15px] text-foreground/60">
            {mockChannels.length} channels
          </p>
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button className="h-9 gap-1.5 rounded-full bg-foreground px-4 text-[13px] font-medium text-background hover:bg-foreground/90">
              <Plus className="h-3.5 w-3.5" />
              New Channel
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="text-[17px]">Create Channel</DialogTitle>
              <DialogDescription className="text-[13px] text-foreground/60">
                Add a new channel to organize your videos.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label className="text-[13px]">Name</Label>
                <Input
                  placeholder="e.g., Wealth Wisdom"
                  value={newChannelName}
                  onChange={(e) => setNewChannelName(e.target.value)}
                  className="h-10 rounded-xl border-foreground/10"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-[13px]">Niche</Label>
                <Select value={newChannelNiche} onValueChange={setNewChannelNiche}>
                  <SelectTrigger className="h-10 rounded-xl border-foreground/10">
                    <SelectValue placeholder="Select a niche" />
                  </SelectTrigger>
                  <SelectContent>
                    {niches.map((niche) => (
                      <SelectItem key={niche} value={niche} className="capitalize">
                        {niche.replace("_", " ")}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="ghost" onClick={() => setIsCreateOpen(false)} className="h-9 rounded-full text-[13px]">
                Cancel
              </Button>
              <Button
                onClick={handleCreateChannel}
                disabled={!newChannelName || !newChannelNiche}
                className="h-9 rounded-full bg-foreground px-5 text-[13px] text-background"
              >
                Create
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Channels Table */}
      <div className="mt-8 rounded-xl border border-foreground/10">
        <table className="w-full">
          <thead>
            <tr className="border-b border-foreground/10">
              <th className="px-4 py-3 text-left text-[12px] font-medium text-foreground/50">Name</th>
              <th className="px-4 py-3 text-left text-[12px] font-medium text-foreground/50">Niche</th>
              <th className="px-4 py-3 text-left text-[12px] font-medium text-foreground/50">Videos</th>
              <th className="px-4 py-3 text-left text-[12px] font-medium text-foreground/50">YouTube</th>
              <th className="px-4 py-3 text-right text-[12px] font-medium text-foreground/50"></th>
            </tr>
          </thead>
          <tbody>
            {mockChannels.map((channel) => (
              <tr key={channel.id} className="group border-b border-foreground/5 last:border-0">
                <td className="px-4 py-4">
                  <span className="text-[14px] font-medium">{channel.name}</span>
                </td>
                <td className="px-4 py-4">
                  <span className="text-[13px] capitalize text-foreground/60">
                    {channel.niche.replace("_", " ")}
                  </span>
                </td>
                <td className="px-4 py-4">
                  <span className="text-[13px] text-foreground/60">{channel.video_count}</span>
                </td>
                <td className="px-4 py-4">
                  {channel.youtube_channel_id ? (
                    <span className={cn(
                      "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium",
                      "bg-foreground text-background"
                    )}>
                      Connected
                    </span>
                  ) : (
                    <Button variant="ghost" size="sm" className="h-6 rounded-full px-2 text-[11px]">
                      Connect
                    </Button>
                  )}
                </td>
                <td className="px-4 py-4 text-right">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-7 w-7 rounded-full opacity-0 group-hover:opacity-100">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem className="text-[13px]">
                        <Settings className="mr-2 h-3.5 w-3.5" />
                        Settings
                      </DropdownMenuItem>
                      {channel.youtube_channel_id && (
                        <DropdownMenuItem className="text-[13px]">
                          <ExternalLink className="mr-2 h-3.5 w-3.5" />
                          View on YouTube
                        </DropdownMenuItem>
                      )}
                      <DropdownMenuSeparator />
                      <DropdownMenuItem className="text-[13px] text-destructive">
                        <Trash2 className="mr-2 h-3.5 w-3.5" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
