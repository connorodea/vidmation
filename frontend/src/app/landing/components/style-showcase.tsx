"use client";

const STYLES = [
  {
    name: "Oil Painting",
    bestFor: "Finance, History, Storytelling",
    accent: "#d97706",
    gradient: "linear-gradient(135deg, #78350f, #92400e, #d97706)",
  },
  {
    name: "Cinematic Realism",
    bestFor: "Tech, Business, Explainers",
    accent: "#3b82f6",
    gradient: "linear-gradient(135deg, #1e3a5f, #1e40af, #3b82f6)",
  },
  {
    name: "Anime",
    bestFor: "Gaming, Entertainment, Pop Culture",
    accent: "#ec4899",
    gradient: "linear-gradient(135deg, #831843, #be185d, #ec4899)",
  },
  {
    name: "Watercolor",
    bestFor: "Education, Wellness, Art",
    accent: "#a78bfa",
    gradient: "linear-gradient(135deg, #4c1d95, #6d28d9, #a78bfa)",
  },
  {
    name: "Dark Noir",
    bestFor: "True Crime, Mystery, Horror",
    accent: "#ef4444",
    gradient: "linear-gradient(135deg, #450a0a, #991b1b, #ef4444)",
  },
  {
    name: "Retro Vintage",
    bestFor: "Nostalgia, Music, Culture",
    accent: "#f97316",
    gradient: "linear-gradient(135deg, #7c2d12, #c2410c, #f97316)",
  },
  {
    name: "Corporate Clean",
    bestFor: "SaaS, Marketing, Startup",
    accent: "#10a37f",
    gradient: "linear-gradient(135deg, #064e3b, #047857, #10a37f)",
  },
  {
    name: "Sci-Fi",
    bestFor: "Space, Futurism, Technology",
    accent: "#06b6d4",
    gradient: "linear-gradient(135deg, #164e63, #0e7490, #06b6d4)",
  },
  {
    name: "Nature",
    bestFor: "Travel, Wildlife, Meditation",
    accent: "#34d399",
    gradient: "linear-gradient(135deg, #064e3b, #059669, #34d399)",
  },
  {
    name: "Stock Footage",
    bestFor: "News, Commentary, Tutorials",
    accent: "#6b7280",
    gradient: "linear-gradient(135deg, #1f2937, #374151, #6b7280)",
  },
];

export function StyleShowcase() {
  return (
    <section className="overflow-hidden py-24 sm:py-32">
      <div className="mx-auto max-w-[1200px] px-6">
        {/* Section header */}
        <div className="mx-auto max-w-[600px] text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#10a37f]">
            Visual Styles
          </p>
          <h2 className="mt-4 text-3xl font-bold tracking-tight text-[#fafafa] sm:text-4xl lg:text-[42px]">
            10 visual styles for any niche
          </h2>
          <p className="mt-4 text-base text-[#a1a1a1] sm:text-lg">
            Each style is optimized for specific content types and audiences.
          </p>
        </div>
      </div>

      {/* Horizontal scroll row */}
      <div className="mt-16 w-full">
        <div className="hide-scrollbar flex gap-4 overflow-x-auto px-6 pb-4 sm:gap-5">
          {/* Left spacer for centering on large screens */}
          <div className="shrink-0 sm:w-[calc((100vw-1200px)/2)]" />

          {STYLES.map((style) => (
            <div
              key={style.name}
              className="group flex w-[260px] shrink-0 flex-col overflow-hidden rounded-2xl border border-white/[0.06] bg-[#111] transition-all duration-200 hover:border-white/[0.12]"
            >
              {/* Gradient preview area */}
              <div
                className="flex h-36 items-center justify-center"
                style={{ background: style.gradient }}
              >
                <div className="rounded-full bg-white/10 px-4 py-1.5 text-xs font-semibold text-white/80 backdrop-blur-sm">
                  {style.name}
                </div>
              </div>

              {/* Info */}
              <div className="flex flex-1 flex-col p-5">
                <h3 className="text-[15px] font-semibold text-[#fafafa]">
                  {style.name}
                </h3>
                <p className="mt-1.5 text-xs text-[#666]">Best for:</p>
                <p className="text-sm text-[#a1a1a1]">{style.bestFor}</p>
              </div>
            </div>
          ))}

          {/* Right spacer */}
          <div className="shrink-0 sm:w-[calc((100vw-1200px)/2)]" />
        </div>
      </div>
    </section>
  );
}
