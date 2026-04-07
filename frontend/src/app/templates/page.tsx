"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import {
  TemplateCard,
  type VideoTemplate,
} from "@/components/templates/template-card";
import { ArrowRight, Sparkles } from "lucide-react";

const TEMPLATES: VideoTemplate[] = [
  {
    id: "dark-cinematic",
    name: "Dark Cinematic",
    description:
      "Dramatic storytelling with bold white captions and film-grade transitions. Perfect for documentaries and deep dives.",
    accent: "#3b82f6",
    captionStyle: {
      text: "The untold story begins here...",
      position: "bottom-center",
      fontWeight: "700",
      fontSize: "14px",
    },
    tags: {
      transition: "Cinematic Cuts",
      music: "Cinematic",
      captionAnimation: "Fade In",
    },
  },
  {
    id: "clean-educational",
    name: "Clean Educational",
    description:
      "Minimalist design that keeps the focus on your content. Clean subtitles and calm background music.",
    accent: "#10b981",
    captionStyle: {
      text: "Step 1: Understanding the basics",
      position: "bottom-center",
      fontWeight: "400",
      fontSize: "12px",
    },
    tags: {
      transition: "Smooth Fade",
      music: "Ambient",
      captionAnimation: "Typewriter",
    },
  },
  {
    id: "tiktok-viral",
    name: "TikTok Viral",
    description:
      "Eye-catching neon bold captions with punchy animations. Built to stop the scroll and go viral.",
    accent: "#f43f5e",
    captionStyle: {
      text: "YOU WON'T BELIEVE THIS",
      position: "center",
      fontWeight: "900",
      fontSize: "16px",
    },
    tags: {
      transition: "Zoom Flash",
      music: "Electronic",
      captionAnimation: "Pop In",
    },
  },
  {
    id: "storytelling",
    name: "Storytelling",
    description:
      "Warm, narrative-driven style with elegant serif captions and gentle fade transitions. For long-form stories.",
    accent: "#f59e0b",
    captionStyle: {
      text: "Once upon a midnight hour...",
      position: "bottom-center",
      fontWeight: "400",
      fontStyle: "italic",
      fontSize: "13px",
      fontFamily: "Georgia, serif",
    },
    tags: {
      transition: "Fade",
      music: "Cinematic",
      captionAnimation: "Slide Up",
    },
  },
  {
    id: "finance-business",
    name: "Finance / Business",
    description:
      "Professional dark theme with green accent data overlays. Clean, authoritative, and trustworthy.",
    accent: "#10a37f",
    captionStyle: {
      text: "Markets rallied 2.4% today",
      position: "bottom-center",
      fontWeight: "500",
      fontSize: "12px",
      fontFamily: "system-ui, sans-serif",
    },
    tags: {
      transition: "Slide",
      music: "Lo-Fi",
      captionAnimation: "Word Highlight",
    },
  },
  {
    id: "motivation",
    name: "Motivation",
    description:
      "High-contrast, large karaoke-style captions that hit hard. Designed for gym clips and motivational content.",
    accent: "#8b5cf6",
    captionStyle: {
      text: "NEVER GIVE UP",
      position: "center",
      fontWeight: "900",
      fontSize: "18px",
    },
    tags: {
      transition: "Hard Cut",
      music: "Electronic",
      captionAnimation: "Karaoke",
    },
  },
  {
    id: "podcast-style",
    name: "Podcast Style",
    description:
      "Minimal, relaxed layout with bottom-left subtitles. Feels like a conversation, ideal for podcast clips.",
    accent: "#6b7280",
    captionStyle: {
      text: "...and that changed everything.",
      position: "bottom-left",
      fontWeight: "400",
      fontSize: "12px",
    },
    tags: {
      transition: "Crossfade",
      music: "Chill",
      captionAnimation: "Fade",
    },
  },
];

export default function TemplatesPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selectedTemplate = TEMPLATES.find((t) => t.id === selectedId);

  return (
    <div className="max-w-[1200px]">
      <PageHeader
        title="Templates"
        description="Choose a video style template to define the look, feel, and caption style of your next video."
      />

      {/* Template grid */}
      <div className="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {TEMPLATES.map((template) => (
          <TemplateCard
            key={template.id}
            template={template}
            selected={selectedId === template.id}
            onSelect={() =>
              setSelectedId((prev) =>
                prev === template.id ? null : template.id
              )
            }
          />
        ))}
      </div>

      {/* Sticky bottom bar when a template is selected */}
      <div
        className={`fixed bottom-0 left-0 right-0 z-50 transition-all duration-300 ease-out ${
          selectedTemplate
            ? "translate-y-0 opacity-100"
            : "translate-y-full opacity-0 pointer-events-none"
        }`}
      >
        <div className="border-t border-white/[0.06] bg-[#0d0d0d]/90 backdrop-blur-xl">
          <div className="mx-auto flex max-w-[1200px] items-center justify-between px-6 py-4 pl-[284px]">
            <div className="flex items-center gap-3">
              {selectedTemplate && (
                <>
                  <div
                    className="h-3 w-3 rounded-full shrink-0"
                    style={{ backgroundColor: selectedTemplate.accent }}
                  />
                  <div>
                    <p className="text-sm font-medium text-[#ececec]">
                      {selectedTemplate.name}
                    </p>
                    <p className="text-xs text-[#666]">
                      {selectedTemplate.tags.music} &middot;{" "}
                      {selectedTemplate.tags.transition} &middot;{" "}
                      {selectedTemplate.tags.captionAnimation}
                    </p>
                  </div>
                </>
              )}
            </div>
            <Button asChild size="lg" className="gap-2">
              <Link
                href={`/videos/new?template=${selectedTemplate?.id ?? ""}`}
              >
                <Sparkles className="h-4 w-4" />
                Create Video with this Style
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </div>

      {/* Bottom spacer so cards aren't hidden behind the sticky bar */}
      {selectedTemplate && <div className="h-24" />}
    </div>
  );
}
