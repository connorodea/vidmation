"use client";

import {
  Sparkles,
  Mic,
  Captions,
  Layers,
  Search,
  Globe,
  Music,
  Clapperboard,
  type LucideIcon,
} from "lucide-react";

/* ---------- Data ---------- */

interface BentoItem {
  title: string;
  description: string;
  icon: LucideIcon;
  size: "large" | "medium" | "small";
  content?: React.ReactNode;
}

const VISUAL_STYLES = [
  { name: "Oil Painting", color: "#d97706" },
  { name: "Cinematic", color: "#3b82f6" },
  { name: "Anime", color: "#ec4899" },
  { name: "Watercolor", color: "#a78bfa" },
  { name: "Dark Noir", color: "#ef4444" },
  { name: "Retro", color: "#f97316" },
  { name: "Corporate", color: "#10a37f" },
  { name: "Sci-Fi", color: "#06b6d4" },
  { name: "Nature", color: "#34d399" },
  { name: "Stock", color: "#6b7280" },
];

function ScriptPreview() {
  return (
    <div className="mt-4 rounded-xl border border-white/[0.04] bg-[#0a0a0a] p-4 font-mono text-xs leading-relaxed">
      <div className="text-[#10a37f]">{"// AI-generated script"}</div>
      <div className="mt-2 text-[#666]">
        <span className="text-[#a78bfa]">HOOK</span>{" "}
        <span className="text-[#999]">
          &quot;What if I told you that 40% of today&apos;s jobs
        </span>
      </div>
      <div className="text-[#666]">
        <span className="text-[#999]">
          will be replaced by AI within 5 years?&quot;
        </span>
      </div>
      <div className="mt-2 text-[#666]">
        <span className="text-[#f59e0b]">SECTION_1</span>{" "}
        <span className="text-[#999]">&quot;The Rise of AI Agents&quot;</span>
      </div>
      <div className="text-[#666]">
        <span className="text-[#999]">
          Companies like Google and OpenAI are...
        </span>
      </div>
      <div className="mt-2 text-[#666]">
        <span className="text-[#10a37f]">CTA</span>{" "}
        <span className="text-[#999]">
          &quot;Subscribe for more AI insights&quot;
        </span>
      </div>
    </div>
  );
}

function StyleGrid() {
  return (
    <div className="mt-4 grid grid-cols-5 gap-1.5">
      {VISUAL_STYLES.map((style) => (
        <div
          key={style.name}
          className="flex flex-col items-center gap-1 rounded-lg bg-[#0a0a0a] p-2"
        >
          <div
            className="h-4 w-4 rounded-full"
            style={{ backgroundColor: style.color }}
          />
          <span className="text-[9px] text-[#555] leading-none text-center">
            {style.name}
          </span>
        </div>
      ))}
    </div>
  );
}

function BatchPreview() {
  return (
    <div className="mt-4 space-y-2">
      {[
        { title: "AI Tools 2025", status: "Rendering", progress: 78 },
        { title: "Crypto for Beginners", status: "Rendering", progress: 45 },
        { title: "Productivity Hacks", status: "Queued", progress: 0 },
      ].map((item) => (
        <div
          key={item.title}
          className="flex items-center gap-3 rounded-lg bg-[#0a0a0a] px-3 py-2"
        >
          <div className="flex-1">
            <div className="text-xs text-[#ccc]">{item.title}</div>
            <div className="text-[10px] text-[#555]">{item.status}</div>
          </div>
          <div className="h-1.5 w-20 overflow-hidden rounded-full bg-[#1a1a1a]">
            <div
              className="h-full rounded-full bg-[#10a37f]"
              style={{ width: `${item.progress}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

const BENTO_ITEMS: BentoItem[] = [
  {
    title: "AI Script Generation",
    description:
      "Enter a topic, get a complete video script. Powered by GPT-4o with retention optimization, hooks, and SEO tags.",
    icon: Sparkles,
    size: "large",
    content: <ScriptPreview />,
  },
  {
    title: "10 Visual Styles",
    description:
      "From oil paintings to cinematic realism. Choose the look that matches your niche and audience.",
    icon: Clapperboard,
    size: "medium",
    content: <StyleGrid />,
  },
  {
    title: "Professional Voiceover",
    description:
      "35+ AI voices from OpenAI. Deep narration, energetic presentation, calm meditation -- match your niche.",
    icon: Mic,
    size: "medium",
  },
  {
    title: "Whisper-Synced Captions",
    description:
      "Word-level subtitle timing. Yellow keyword highlights. Montserrat Bold. Burned into video.",
    icon: Captions,
    size: "medium",
  },
  {
    title: "Batch Production",
    description:
      "Generate 10 videos at once. CSV import, RSS feed, or AI topic suggestions. Scale your channel.",
    icon: Layers,
    size: "large",
    content: <BatchPreview />,
  },
  {
    title: "YouTube SEO",
    description: "Auto-optimized titles, descriptions, tags, and thumbnails for maximum click-through rate.",
    icon: Search,
    size: "small",
  },
  {
    title: "Multi-Platform",
    description: "Export for YouTube, TikTok, Instagram Reels with automatic aspect ratio formatting.",
    icon: Globe,
    size: "small",
  },
  {
    title: "Background Music",
    description: "Cinematic, ambient, upbeat tracks auto-mixed and volume-matched to your voiceover.",
    icon: Music,
    size: "small",
  },
  {
    title: "Ken Burns & Effects",
    description: "Film grain, smooth transitions, zoom effects, and parallax motion on every visual.",
    icon: Clapperboard,
    size: "small",
  },
];

/* ---------- Component ---------- */

function BentoCard({ item }: { item: BentoItem }) {
  const isLarge = item.size === "large";

  return (
    <div
      className={`bento-card group rounded-2xl border border-white/[0.06] bg-[#111] p-7 sm:p-8 ${
        isLarge ? "md:col-span-2" : ""
      }`}
    >
      {/* Icon */}
      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#10a37f]/10 transition-colors duration-200 group-hover:bg-[#10a37f]/15">
        <item.icon className="h-5 w-5 text-[#10a37f]" />
      </div>

      {/* Text */}
      <h3 className="mt-5 text-lg font-semibold text-[#fafafa]">
        {item.title}
      </h3>
      <p className="mt-2 text-sm leading-relaxed text-[#a1a1a1]">
        {item.description}
      </p>

      {/* Optional rich content */}
      {item.content}
    </div>
  );
}

export function BentoGrid() {
  return (
    <section id="features" className="py-24 sm:py-32">
      <div className="mx-auto max-w-[1200px] px-6">
        {/* Section header */}
        <div className="mx-auto max-w-[600px] text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#10a37f]">
            Features
          </p>
          <h2 className="mt-4 text-3xl font-bold tracking-tight text-[#fafafa] sm:text-4xl lg:text-[42px]">
            Everything you need
          </h2>
          <p className="mt-4 text-base text-[#a1a1a1] sm:text-lg">
            One platform to create, edit, and publish faceless videos.
          </p>
        </div>

        {/* Grid */}
        <div className="mt-16 grid gap-4 sm:gap-5 md:grid-cols-2 lg:grid-cols-4">
          {/* Row 1: large (2 col) + medium + medium */}
          <div className="md:col-span-2">
            <BentoCard item={BENTO_ITEMS[0]} />
          </div>
          <div className="lg:col-span-1">
            <BentoCard item={BENTO_ITEMS[1]} />
          </div>
          <div className="lg:col-span-1">
            <BentoCard item={BENTO_ITEMS[2]} />
          </div>

          {/* Row 2: medium + medium + large (2 col) — reversed */}
          <div className="lg:col-span-1">
            <BentoCard item={BENTO_ITEMS[3]} />
          </div>
          <div className="lg:col-span-1">
            <BentoCard item={BENTO_ITEMS[5]} />
          </div>
          <div className="md:col-span-2">
            <BentoCard item={BENTO_ITEMS[4]} />
          </div>

          {/* Row 3: 4 small cards */}
          {BENTO_ITEMS.slice(6).map((item) => (
            <div key={item.title} className="lg:col-span-1">
              <BentoCard item={item} />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
