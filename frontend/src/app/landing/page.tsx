"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Sparkles,
  Mic,
  Image,
  Search,
  Layers,
  Share2,
  ChevronDown,
  ChevronRight,
  Play,
  Check,
  ArrowRight,
  Palette,
  Film,
  Clapperboard,
  Users,
  Zap,
} from "lucide-react";

/* ==========================================================================
   Hero Section
   ========================================================================== */

function HeroSection() {
  return (
    <section className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6 pt-16">
      {/* Gradient mesh background */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-1/4 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#10a37f]/[0.07] blur-[120px]" />
        <div className="absolute right-1/4 top-1/2 h-[400px] w-[400px] rounded-full bg-[#10a37f]/[0.04] blur-[100px]" />
        <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />
      </div>

      <div className="relative z-10 mx-auto max-w-[800px] text-center">
        {/* Badge */}
        <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.03] px-4 py-1.5">
          <Zap className="h-3.5 w-3.5 text-[#10a37f]" />
          <span className="text-xs font-medium text-[#999]">
            Now with batch production -- 10 videos at once
          </span>
        </div>

        {/* Heading */}
        <h1 className="text-4xl font-bold leading-[1.1] tracking-tight text-[#ececec] sm:text-5xl md:text-6xl lg:text-[64px]">
          Create Faceless YouTube
          <br />
          Videos with{" "}
          <span className="bg-gradient-to-r from-[#10a37f] to-[#10a37f]/70 bg-clip-text text-transparent">
            AI
          </span>
        </h1>

        {/* Subheading */}
        <p className="mx-auto mt-6 max-w-[560px] text-base leading-relaxed text-[#999] sm:text-lg">
          From topic to published video in minutes. AI writes, narrates, and
          produces professional videos for your YouTube channel.
        </p>

        {/* CTA Buttons */}
        <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          <Button size="lg" className="w-full sm:w-auto px-8 text-[15px]" asChild>
            <Link href="/signup">
              Start Free
              <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </Button>
          <Button
            variant="secondary"
            size="lg"
            className="w-full sm:w-auto px-8 text-[15px]"
            asChild
          >
            <a href="#demo">
              <Play className="mr-1 h-4 w-4" />
              Watch Demo
            </a>
          </Button>
        </div>

        {/* Subtle stats */}
        <div className="mt-16 flex items-center justify-center gap-8 text-sm text-[#666]">
          <span>No credit card required</span>
          <span className="h-3.5 w-px bg-white/[0.1]" />
          <span>3 free videos/month</span>
          <span className="hidden h-3.5 w-px bg-white/[0.1] sm:block" />
          <span className="hidden sm:block">Cancel anytime</span>
        </div>
      </div>
    </section>
  );
}

/* ==========================================================================
   Social Proof Bar
   ========================================================================== */

function SocialProofBar() {
  return (
    <section className="border-y border-white/[0.06] bg-white/[0.02] py-12">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="flex flex-col items-center gap-8">
          <div className="flex items-center gap-3">
            <Users className="h-4 w-4 text-[#10a37f]" />
            <p className="text-sm font-medium text-[#999]">
              Trusted by 1,000+ creators producing 50,000+ videos
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-4">
            {[
              "YouTube Creators",
              "Marketing Agencies",
              "Content Studios",
              "Educators",
              "SaaS Companies",
            ].map((label) => (
              <span
                key={label}
                className="text-xs font-medium uppercase tracking-widest text-[#444]"
              >
                {label}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

/* ==========================================================================
   How It Works
   ========================================================================== */

const STEPS = [
  {
    number: "01",
    title: "Enter your topic",
    description:
      "Type a topic or paste a URL. Our AI researches, outlines, and writes a complete video script with hooks, transitions, and CTAs.",
    icon: Sparkles,
  },
  {
    number: "02",
    title: "Choose your style",
    description:
      "Select from oil paintings, stock footage, or AI-generated cinematic visuals. Pick a voice from 35+ professional narrators.",
    icon: Palette,
  },
  {
    number: "03",
    title: "Publish to YouTube",
    description:
      "Review your video, make any edits, then auto-upload to YouTube with AI-optimized titles, descriptions, tags, and thumbnails.",
    icon: Share2,
  },
];

function HowItWorksSection() {
  return (
    <section id="demo" className="py-24 sm:py-32">
      <div className="mx-auto max-w-[1200px] px-6">
        {/* Section header */}
        <div className="mx-auto max-w-[600px] text-center">
          <p className="text-xs font-semibold uppercase tracking-widest text-[#10a37f]">
            How it works
          </p>
          <h2 className="mt-4 text-3xl font-bold tracking-tight text-[#ececec] sm:text-4xl">
            Three steps to your first video
          </h2>
          <p className="mt-4 text-base text-[#999]">
            No editing skills required. No camera needed. Just your ideas.
          </p>
        </div>

        {/* Steps */}
        <div className="mt-16 grid gap-6 sm:gap-8 md:grid-cols-3">
          {STEPS.map((step) => (
            <div
              key={step.number}
              className="group relative rounded-2xl border border-white/[0.06] bg-[#1a1a1a]/50 p-8 transition-all duration-200 hover:border-[#10a37f]/20 hover:bg-[#1a1a1a]"
            >
              {/* Step number */}
              <span className="text-xs font-mono font-medium text-[#10a37f]">
                {step.number}
              </span>

              {/* Icon */}
              <div className="mt-4 flex h-10 w-10 items-center justify-center rounded-xl bg-[#10a37f]/10">
                <step.icon className="h-5 w-5 text-[#10a37f]" />
              </div>

              {/* Content */}
              <h3 className="mt-5 text-lg font-semibold text-[#ececec]">
                {step.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-[#999]">
                {step.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ==========================================================================
   Features Grid
   ========================================================================== */

const FEATURES = [
  {
    icon: Sparkles,
    title: "AI Script Generation",
    description:
      "GPT-4 powered scripts with research, hooks, and narrative structure tailored for YouTube engagement.",
  },
  {
    icon: Mic,
    title: "Professional Voiceover",
    description:
      "35+ ultra-realistic voices across languages and styles. Male, female, and character voices included.",
  },
  {
    icon: Image,
    title: "Smart Visual Matching",
    description:
      "AI selects and times visuals to match your narration. Stock footage, oil paintings, or generated scenes.",
  },
  {
    icon: Search,
    title: "YouTube-Optimized SEO",
    description:
      "Auto-generated titles, descriptions, tags, and thumbnails designed to maximize click-through rate.",
  },
  {
    icon: Layers,
    title: "Batch Production",
    description:
      "Queue up to 10 videos at once. Set topics, styles, and schedules -- then let AI produce overnight.",
  },
  {
    icon: Share2,
    title: "Multi-Platform Export",
    description:
      "Export in YouTube, TikTok, or Instagram formats. Automatic aspect ratio and duration optimization.",
  },
];

function FeaturesSection() {
  return (
    <section id="features" className="py-24 sm:py-32">
      <div className="mx-auto max-w-[1200px] px-6">
        {/* Section header */}
        <div className="mx-auto max-w-[600px] text-center">
          <p className="text-xs font-semibold uppercase tracking-widest text-[#10a37f]">
            Features
          </p>
          <h2 className="mt-4 text-3xl font-bold tracking-tight text-[#ececec] sm:text-4xl">
            Everything you need to scale content
          </h2>
          <p className="mt-4 text-base text-[#999]">
            Professional video production, automated from start to finish.
          </p>
        </div>

        {/* Grid */}
        <div className="mt-16 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature) => (
            <div
              key={feature.title}
              className="group rounded-2xl border border-white/[0.06] bg-[#1a1a1a]/50 p-7 transition-all duration-200 hover:border-white/[0.1] hover:bg-[#1a1a1a]"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/[0.05] transition-colors duration-200 group-hover:bg-[#10a37f]/10">
                <feature.icon className="h-5 w-5 text-[#666] transition-colors duration-200 group-hover:text-[#10a37f]" />
              </div>
              <h3 className="mt-5 text-[15px] font-semibold text-[#ececec]">
                {feature.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-[#999]">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ==========================================================================
   Style Showcase
   ========================================================================== */

const STYLES = [
  {
    name: "Dark Finance",
    tag: "Oil Painting",
    description:
      "Rich, painterly visuals with dramatic lighting. Perfect for finance, history, and storytelling channels.",
    icon: Palette,
    gradient: "from-amber-900/30 to-amber-950/60",
    accent: "#d97706",
  },
  {
    name: "Stock Footage",
    tag: "B-Roll",
    description:
      "Cinematic stock clips matched to your script. Ideal for explainers, business content, and tutorials.",
    icon: Film,
    gradient: "from-blue-900/30 to-blue-950/60",
    accent: "#3b82f6",
  },
  {
    name: "AI Cinematic",
    tag: "Generated",
    description:
      "AI-generated scenes with cinematic composition. Unique visuals that no stock library can match.",
    icon: Clapperboard,
    gradient: "from-purple-900/30 to-purple-950/60",
    accent: "#8b5cf6",
  },
];

function StyleShowcaseSection() {
  return (
    <section className="border-t border-white/[0.06] bg-[#111111] py-24 sm:py-32">
      <div className="mx-auto max-w-[1200px] px-6">
        {/* Section header */}
        <div className="mx-auto max-w-[600px] text-center">
          <p className="text-xs font-semibold uppercase tracking-widest text-[#10a37f]">
            Video Styles
          </p>
          <h2 className="mt-4 text-3xl font-bold tracking-tight text-[#ececec] sm:text-4xl">
            Choose your visual identity
          </h2>
          <p className="mt-4 text-base text-[#999]">
            Three distinct production styles, each optimized for different content niches.
          </p>
        </div>

        {/* Style cards */}
        <div className="mt-16 grid gap-6 md:grid-cols-3">
          {STYLES.map((style) => (
            <div
              key={style.name}
              className="group overflow-hidden rounded-2xl border border-white/[0.06] bg-[#1a1a1a] transition-all duration-200 hover:border-white/[0.1]"
            >
              {/* Visual preview area */}
              <div
                className={`relative flex h-48 items-center justify-center bg-gradient-to-br ${style.gradient}`}
              >
                <style.icon
                  className="h-12 w-12 transition-transform duration-300 group-hover:scale-110"
                  style={{ color: style.accent }}
                />
                {/* Tag */}
                <span
                  className="absolute right-3 top-3 rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider"
                  style={{
                    backgroundColor: `${style.accent}20`,
                    color: style.accent,
                  }}
                >
                  {style.tag}
                </span>
              </div>

              {/* Content */}
              <div className="p-6">
                <h3 className="text-lg font-semibold text-[#ececec]">
                  {style.name}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-[#999]">
                  {style.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ==========================================================================
   Pricing Section
   ========================================================================== */

const PLANS = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "Try AIVidio with no commitment",
    features: [
      "3 videos per month",
      "720p export quality",
      "AIVidio watermark",
      "1 video style",
      "5 voice options",
      "Community support",
    ],
    cta: "Get Started",
    ctaVariant: "secondary" as const,
    highlight: false,
  },
  {
    name: "Pro",
    price: "$29",
    period: "/month",
    description: "For creators ready to scale",
    features: [
      "30 videos per month",
      "1080p export quality",
      "No watermark",
      "All video styles",
      "35+ voice options",
      "Batch mode (10 at once)",
      "YouTube auto-upload",
      "Priority rendering",
    ],
    cta: "Start Free Trial",
    ctaVariant: "default" as const,
    highlight: true,
  },
  {
    name: "Business",
    price: "$79",
    period: "/month",
    description: "For teams and agencies",
    features: [
      "Unlimited videos",
      "4K export quality",
      "No watermark",
      "All video styles",
      "35+ voice options",
      "API access",
      "White-label export",
      "Priority support",
      "Custom voice cloning",
      "Team collaboration",
    ],
    cta: "Contact Sales",
    ctaVariant: "secondary" as const,
    highlight: false,
  },
];

function PricingSection() {
  return (
    <section id="pricing" className="py-24 sm:py-32">
      <div className="mx-auto max-w-[1200px] px-6">
        {/* Section header */}
        <div className="mx-auto max-w-[600px] text-center">
          <p className="text-xs font-semibold uppercase tracking-widest text-[#10a37f]">
            Pricing
          </p>
          <h2 className="mt-4 text-3xl font-bold tracking-tight text-[#ececec] sm:text-4xl">
            Simple, transparent pricing
          </h2>
          <p className="mt-4 text-base text-[#999]">
            Start free, upgrade when you need more. No hidden fees.
          </p>
        </div>

        {/* Pricing cards */}
        <div className="mt-16 grid gap-6 md:grid-cols-3">
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              className={`relative flex flex-col rounded-2xl border p-8 transition-all duration-200 ${
                plan.highlight
                  ? "border-[#10a37f]/40 bg-[#10a37f]/[0.04]"
                  : "border-white/[0.06] bg-[#1a1a1a]/50 hover:border-white/[0.1]"
              }`}
            >
              {/* Popular badge */}
              {plan.highlight && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-[#10a37f] px-3 py-1 text-[11px] font-semibold text-white">
                  Most Popular
                </span>
              )}

              {/* Plan header */}
              <div>
                <h3 className="text-lg font-semibold text-[#ececec]">
                  {plan.name}
                </h3>
                <p className="mt-1 text-sm text-[#999]">{plan.description}</p>
              </div>

              {/* Price */}
              <div className="mt-6 flex items-baseline gap-1">
                <span className="text-4xl font-bold text-[#ececec]">
                  {plan.price}
                </span>
                <span className="text-sm text-[#666]">{plan.period}</span>
              </div>

              {/* CTA */}
              <Button
                variant={plan.ctaVariant}
                className="mt-6 w-full"
                asChild
              >
                <Link href="/signup">{plan.cta}</Link>
              </Button>

              {/* Divider */}
              <div className="my-6 h-px bg-white/[0.06]" />

              {/* Features */}
              <ul className="flex flex-col gap-3">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-3">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-[#10a37f]" />
                    <span className="text-sm text-[#999]">{feature}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ==========================================================================
   FAQ Section
   ========================================================================== */

const FAQ_ITEMS = [
  {
    question: "How does the AI generate videos?",
    answer:
      "AIVidio uses a multi-step pipeline: first, GPT-4 writes a researched script based on your topic. Then our visual engine matches each section with appropriate imagery (stock footage, oil paintings, or AI-generated scenes). Finally, a neural voice narrates the script while our editor assembles everything with transitions, captions, and background music.",
  },
  {
    question: "Can I edit the script before generating the video?",
    answer:
      "Absolutely. After the AI generates a script, you get a full editor where you can rewrite sections, adjust timing, change the tone, or add custom segments. You can also provide your own script from scratch and skip the AI writing step entirely.",
  },
  {
    question: "How long does it take to produce a video?",
    answer:
      "A typical 8-10 minute video takes about 5-8 minutes to produce. Rendering time depends on the visual style -- stock footage videos are fastest, while AI-generated cinematic scenes take slightly longer. Pro and Business users get priority rendering queues.",
  },
  {
    question: "Do I own the videos I create?",
    answer:
      "Yes. All videos produced with AIVidio are yours to use commercially. Pro and Business plans include full commercial rights with no attribution required. Free plan videos include a small AIVidio watermark.",
  },
  {
    question: "What YouTube niches work best with AIVidio?",
    answer:
      "AIVidio works well for finance, history, true crime, motivation, technology explainers, top-10 lists, educational content, and news commentary. Any niche that uses narration over visuals (rather than talking-head footage) is a great fit.",
  },
  {
    question: "Can I cancel my subscription anytime?",
    answer:
      "Yes. There are no contracts or cancellation fees. You can cancel your Pro or Business subscription at any time from your account settings. You will retain access until the end of your current billing period.",
  },
];

function FAQItem({
  question,
  answer,
}: {
  question: string;
  answer: string;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border-b border-white/[0.06]">
      <button
        className="flex w-full items-center justify-between py-5 text-left transition-colors hover:text-[#ececec]"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <span className="pr-4 text-[15px] font-medium text-[#ececec]">
          {question}
        </span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-[#666] transition-transform duration-200 ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>
      <div
        className={`grid transition-all duration-200 ease-out ${
          open ? "grid-rows-[1fr] pb-5" : "grid-rows-[0fr]"
        }`}
      >
        <div className="overflow-hidden">
          <p className="text-sm leading-relaxed text-[#999]">{answer}</p>
        </div>
      </div>
    </div>
  );
}

function FAQSection() {
  return (
    <section id="faq" className="border-t border-white/[0.06] bg-[#111111] py-24 sm:py-32">
      <div className="mx-auto max-w-[720px] px-6">
        {/* Section header */}
        <div className="text-center">
          <p className="text-xs font-semibold uppercase tracking-widest text-[#10a37f]">
            FAQ
          </p>
          <h2 className="mt-4 text-3xl font-bold tracking-tight text-[#ececec] sm:text-4xl">
            Frequently asked questions
          </h2>
        </div>

        {/* FAQ list */}
        <div className="mt-12">
          {FAQ_ITEMS.map((item) => (
            <FAQItem
              key={item.question}
              question={item.question}
              answer={item.answer}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

/* ==========================================================================
   CTA Section
   ========================================================================== */

function CTASection() {
  return (
    <section className="py-24 sm:py-32">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="relative overflow-hidden rounded-3xl border border-white/[0.06] bg-[#1a1a1a] p-12 sm:p-16 text-center">
          {/* Background glow */}
          <div className="pointer-events-none absolute left-1/2 top-0 h-[300px] w-[500px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#10a37f]/[0.08] blur-[100px]" />

          <div className="relative z-10">
            <h2 className="text-3xl font-bold tracking-tight text-[#ececec] sm:text-4xl">
              Start creating videos today
            </h2>
            <p className="mx-auto mt-4 max-w-[480px] text-base text-[#999]">
              Join thousands of creators using AI to produce professional
              YouTube content at scale.
            </p>
            <div className="mt-8 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
              <Button size="lg" className="px-8 text-[15px]" asChild>
                <Link href="/signup">
                  Get Started Free
                  <ArrowRight className="ml-1 h-4 w-4" />
                </Link>
              </Button>
            </div>
            <p className="mt-6 text-xs text-[#666]">
              Free plan available. No credit card required.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ==========================================================================
   Footer
   ========================================================================== */

const FOOTER_LINKS = {
  Product: [
    { label: "Features", href: "#features" },
    { label: "Pricing", href: "#pricing" },
    { label: "Changelog", href: "#" },
    { label: "API Docs", href: "#" },
  ],
  Resources: [
    { label: "Blog", href: "#" },
    { label: "Tutorials", href: "#" },
    { label: "Help Center", href: "#" },
    { label: "Status", href: "#" },
  ],
  Company: [
    { label: "About", href: "#" },
    { label: "Careers", href: "#" },
    { label: "Contact", href: "#" },
  ],
  Legal: [
    { label: "Terms of Service", href: "#" },
    { label: "Privacy Policy", href: "#" },
    { label: "Cookie Policy", href: "#" },
  ],
};

function Footer() {
  return (
    <footer className="border-t border-white/[0.06] bg-[#0d0d0d] py-16">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="grid gap-12 sm:grid-cols-2 lg:grid-cols-6">
          {/* Brand */}
          <div className="lg:col-span-2">
            <Link href="/landing" className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#10a37f]">
                <span className="text-xs font-bold text-white tracking-tight">
                  Ai
                </span>
              </div>
              <span className="text-[15px] font-semibold text-[#ececec] tracking-tight">
                AIVidio
              </span>
            </Link>
            <p className="mt-4 max-w-[280px] text-sm leading-relaxed text-[#666]">
              AI-powered video production for YouTube creators. From script to
              screen in minutes.
            </p>
            {/* Social links */}
            <div className="mt-6 flex gap-4">
              <a
                href="https://twitter.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#666] transition-colors hover:text-[#ececec]"
                aria-label="Twitter"
              >
                <svg
                  className="h-4 w-4"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
              </a>
              <a
                href="https://youtube.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#666] transition-colors hover:text-[#ececec]"
                aria-label="YouTube"
              >
                <svg
                  className="h-4 w-4"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
                </svg>
              </a>
            </div>
          </div>

          {/* Link columns */}
          {Object.entries(FOOTER_LINKS).map(([heading, links]) => (
            <div key={heading}>
              <h4 className="text-xs font-semibold uppercase tracking-widest text-[#666]">
                {heading}
              </h4>
              <ul className="mt-4 flex flex-col gap-3">
                {links.map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      className="text-sm text-[#999] transition-colors hover:text-[#ececec]"
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="mt-16 flex flex-col items-center justify-between gap-4 border-t border-white/[0.06] pt-8 sm:flex-row">
          <p className="text-xs text-[#444]">
            2024 AIVidio. All rights reserved.
          </p>
          <p className="text-xs text-[#444]">Made with AI</p>
        </div>
      </div>
    </footer>
  );
}

/* ==========================================================================
   Landing Page
   ========================================================================== */

export default function LandingPage() {
  return (
    <>
      <HeroSection />
      <SocialProofBar />
      <HowItWorksSection />
      <FeaturesSection />
      <StyleShowcaseSection />
      <PricingSection />
      <FAQSection />
      <CTASection />
      <Footer />
    </>
  );
}
