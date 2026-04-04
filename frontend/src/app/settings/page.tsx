"use client";

import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  Settings,
  Key,
  Bell,
  DollarSign,
  Webhook,
  Plus,
  Trash2,
  Eye,
  EyeOff,
  Copy,
  Check,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface ApiKey {
  id: string;
  prefix: string;
  createdAt: string;
  lastUsed: string | null;
}

interface WebhookEntry {
  id: string;
  url: string;
  events: string[];
  isActive: boolean;
}

/* ------------------------------------------------------------------ */
/* Sample Data                                                         */
/* ------------------------------------------------------------------ */

const SAMPLE_KEYS: ApiKey[] = [
  {
    id: "1",
    prefix: "vm_live_abc1",
    createdAt: "2026-03-15T10:00:00Z",
    lastUsed: "2026-04-04T08:30:00Z",
  },
  {
    id: "2",
    prefix: "vm_test_xyz9",
    createdAt: "2026-04-01T14:00:00Z",
    lastUsed: null,
  },
];

const SAMPLE_WEBHOOKS: WebhookEntry[] = [
  {
    id: "1",
    url: "https://hooks.slack.com/services/T00/B00/xxxx",
    events: ["video.completed", "video.failed"],
    isActive: true,
  },
  {
    id: "2",
    url: "https://discord.com/api/webhooks/1234/abcd",
    events: ["video.completed"],
    isActive: true,
  },
];

/* ------------------------------------------------------------------ */
/* Section wrapper                                                     */
/* ------------------------------------------------------------------ */

function SettingsSection({
  icon: Icon,
  title,
  description,
  children,
}: {
  icon: typeof Key;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-white/[0.08] bg-[#1a1a1a]">
      <div className="border-b border-white/[0.06] px-6 py-5">
        <div className="flex items-center gap-2.5">
          <Icon className="h-4 w-4 text-[#666]" />
          <h2 className="text-sm font-medium text-[#ececec]">{title}</h2>
        </div>
        <p className="mt-1 text-xs text-[#666]">{description}</p>
      </div>
      <div className="p-6">{children}</div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Toggle component                                                    */
/* ------------------------------------------------------------------ */

function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (val: boolean) => void;
  label: string;
}) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full transition-colors duration-200",
        checked ? "bg-[#10a37f]" : "bg-white/[0.12]"
      )}
    >
      <span
        className={cn(
          "pointer-events-none inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform duration-200",
          checked ? "translate-x-[18px]" : "translate-x-[3px]"
        )}
      />
    </button>
  );
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export default function SettingsPage() {
  const [keys] = useState<ApiKey[]>(SAMPLE_KEYS);
  const [webhooks] = useState<WebhookEntry[]>(SAMPLE_WEBHOOKS);

  // Notification toggles
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [discordEnabled, setDiscordEnabled] = useState(true);
  const [slackEnabled, setSlackEnabled] = useState(false);
  const [discordWebhook, setDiscordWebhook] = useState(
    "https://discord.com/api/webhooks/..."
  );
  const [slackWebhook, setSlackWebhook] = useState("");

  // Budget
  const [monthlyBudget, setMonthlyBudget] = useState("50.00");
  const currentSpend = 23.47;

  // Webhook form
  const [newWebhookUrl, setNewWebhookUrl] = useState("");

  // Clipboard
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const handleCopy = useCallback((text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }, []);

  const budgetPct = Math.min(
    (currentSpend / parseFloat(monthlyBudget || "1")) * 100,
    100
  );

  return (
    <div className="min-h-screen bg-[#0d0d0d]">
      <div className="mx-auto max-w-3xl px-6 py-8">
        {/* Page header */}
        <div className="mb-8 flex items-center gap-3">
          <Settings className="h-5 w-5 text-[#666]" />
          <h1 className="text-2xl font-semibold text-[#ececec]">Settings</h1>
        </div>

        <div className="space-y-6">
          {/* ---- API Keys ---- */}
          <SettingsSection
            icon={Key}
            title="API Keys"
            description="Manage your API keys for programmatic access"
          >
            <div className="space-y-3">
              {keys.map((key) => (
                <div
                  key={key.id}
                  className="flex items-center gap-4 rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3"
                >
                  <code className="text-xs font-mono text-[#ececec]">
                    {key.prefix}...
                  </code>
                  <div className="flex-1" />
                  <span className="text-[11px] text-[#666]">
                    Created{" "}
                    {new Date(key.createdAt).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                    })}
                  </span>
                  <button
                    onClick={() => handleCopy(key.prefix, key.id)}
                    className="flex h-7 w-7 items-center justify-center rounded-md text-[#666] transition-colors duration-150 hover:bg-white/[0.06] hover:text-[#999]"
                    aria-label="Copy key prefix"
                  >
                    {copiedId === key.id ? (
                      <Check className="h-3.5 w-3.5 text-[#10a37f]" />
                    ) : (
                      <Copy className="h-3.5 w-3.5" />
                    )}
                  </button>
                  <button
                    className="flex h-7 w-7 items-center justify-center rounded-md text-[#666] transition-colors duration-150 hover:bg-[#ef4444]/10 hover:text-[#ef4444]"
                    aria-label="Revoke key"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
            <Button variant="secondary" size="sm" className="mt-4 gap-2">
              <Plus className="h-3.5 w-3.5" />
              Create Key
            </Button>
          </SettingsSection>

          {/* ---- Notifications ---- */}
          <SettingsSection
            icon={Bell}
            title="Notifications"
            description="Choose how and where you receive alerts"
          >
            <div className="space-y-5">
              {/* Email */}
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-[#ececec]">Email</p>
                  <p className="text-xs text-[#666]">
                    Receive email notifications for completed and failed jobs
                  </p>
                </div>
                <Toggle
                  checked={emailEnabled}
                  onChange={setEmailEnabled}
                  label="Toggle email notifications"
                />
              </div>

              {/* Discord */}
              <div className="space-y-3 border-t border-white/[0.06] pt-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-[#ececec]">Discord</p>
                    <p className="text-xs text-[#666]">
                      Post updates to a Discord channel
                    </p>
                  </div>
                  <Toggle
                    checked={discordEnabled}
                    onChange={setDiscordEnabled}
                    label="Toggle Discord notifications"
                  />
                </div>
                {discordEnabled && (
                  <Input
                    value={discordWebhook}
                    onChange={(e) => setDiscordWebhook(e.target.value)}
                    placeholder="https://discord.com/api/webhooks/..."
                    className="text-xs"
                  />
                )}
              </div>

              {/* Slack */}
              <div className="space-y-3 border-t border-white/[0.06] pt-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-[#ececec]">Slack</p>
                    <p className="text-xs text-[#666]">
                      Post updates to a Slack channel
                    </p>
                  </div>
                  <Toggle
                    checked={slackEnabled}
                    onChange={setSlackEnabled}
                    label="Toggle Slack notifications"
                  />
                </div>
                {slackEnabled && (
                  <Input
                    value={slackWebhook}
                    onChange={(e) => setSlackWebhook(e.target.value)}
                    placeholder="https://hooks.slack.com/services/..."
                    className="text-xs"
                  />
                )}
              </div>
            </div>
          </SettingsSection>

          {/* ---- Budget ---- */}
          <SettingsSection
            icon={DollarSign}
            title="Budget"
            description="Set spending limits for AI generation costs"
          >
            <div className="space-y-5">
              <div className="flex items-end gap-4">
                <div className="flex-1">
                  <label
                    htmlFor="monthly-budget"
                    className="mb-2 block text-xs text-[#666]"
                  >
                    Monthly limit (USD)
                  </label>
                  <div className="relative max-w-[200px]">
                    <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm text-[#666]">
                      $
                    </span>
                    <Input
                      id="monthly-budget"
                      type="number"
                      value={monthlyBudget}
                      onChange={(e) => setMonthlyBudget(e.target.value)}
                      className="pl-7 tabular-nums"
                      min="0"
                      step="5"
                    />
                  </div>
                </div>
              </div>

              {/* Spend bar */}
              <div>
                <div className="mb-2 flex items-baseline justify-between">
                  <span className="text-xs text-[#666]">Current spend</span>
                  <span className="text-sm tabular-nums font-medium text-[#ececec]">
                    ${currentSpend.toFixed(2)}{" "}
                    <span className="text-[#666]">
                      / ${parseFloat(monthlyBudget || "0").toFixed(2)}
                    </span>
                  </span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-white/[0.06]">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-500",
                      budgetPct > 90 ? "bg-[#ef4444]" : budgetPct > 70 ? "bg-[#f59e0b]" : "bg-[#10a37f]"
                    )}
                    style={{ width: `${budgetPct}%` }}
                  />
                </div>
                <p className="mt-1.5 text-[11px] text-[#666]">
                  {budgetPct.toFixed(0)}% of monthly budget used
                </p>
              </div>
            </div>
          </SettingsSection>

          {/* ---- Webhooks ---- */}
          <SettingsSection
            icon={Webhook}
            title="Webhooks"
            description="Get notified when events happen via HTTP callbacks"
          >
            <div className="space-y-3">
              {webhooks.map((wh) => (
                <div
                  key={wh.id}
                  className="flex items-center gap-4 rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3"
                >
                  <div className="min-w-0 flex-1">
                    <code className="block truncate text-xs font-mono text-[#ececec]">
                      {wh.url}
                    </code>
                    <div className="mt-1 flex items-center gap-1.5">
                      {wh.events.map((ev) => (
                        <Badge key={ev} className="text-[10px]">
                          {ev}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <Badge
                    variant={wh.isActive ? "success" : "default"}
                    className="shrink-0"
                  >
                    {wh.isActive ? "Active" : "Inactive"}
                  </Badge>
                  <button
                    className="flex h-7 w-7 items-center justify-center rounded-md text-[#666] transition-colors duration-150 hover:bg-[#ef4444]/10 hover:text-[#ef4444]"
                    aria-label="Delete webhook"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>

            {/* Add new webhook */}
            <div className="mt-4 flex items-center gap-3">
              <Input
                value={newWebhookUrl}
                onChange={(e) => setNewWebhookUrl(e.target.value)}
                placeholder="https://your-endpoint.com/webhook"
                className="flex-1 text-xs font-mono"
              />
              <Button
                variant="secondary"
                size="sm"
                disabled={!newWebhookUrl.trim()}
                className="shrink-0 gap-2"
              >
                <Plus className="h-3.5 w-3.5" />
                Add
              </Button>
            </div>
          </SettingsSection>
        </div>
      </div>
    </div>
  );
}
