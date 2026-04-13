"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import {
  Sparkles,
  Palette,
  Upload,
  Play,
  ArrowRight,
  ChevronDown,
  Check,
} from "lucide-react";
import { HeroVisual } from "./components/hero-visual";
import { BentoGrid } from "./components/bento-grid";
import { StyleShowcase } from "./components/style-showcase";
import { PricingSection } from "./components/pricing-card";

/* ==========================================================================
   Hero Section
   ========================================================================== */

function HeroSection() {
  return (
    <section className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6 pt-16">
      {/* Background effects */}
      <div className="pointer-events-none absolute inset-0">
        {/* Radial green glow */}
        <div className="hero-glow absolute inset-0" />
        {/* Dot grid pattern */}
        <div className="dot-pattern absolute inset-0" />
        {/* Secondary glow */}
        <div className="absolute right-1/4 top-1/3 h-[500px] w-[500px] rounded-full bg-[#10a37f]/[0.03] blur-[120px]" />
        {/* Bottom fade line */}
        <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />
      </div>

      <div className="relative z-10 mx-auto max-w-[800px] text-center">
        {/* Badge */}
        <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.03] px-4 py-1.5 backdrop-blur-sm">
          <div className="h-1.5 w-1.5 rounded-full bg-[#10a37f] animate-pulse-dot" />
          <span className="text-xs font-medium text-[#a1a1a1]">
            Now with batch production -- create 10 videos at once
          </span>
        </div>

        {/* Heading */}
        <h1 className="text-4xl font-bold leading-[1.08] tracking-[-0.02em] text-[#fafafa] sm:text-5xl md:text-6xl lg:text-[72px]">
          Create YouTube Videos
          <br />
          <span className="gradient-text">with AI</span> in Minutes
        </h1>

        {/* Subheading */}
        <p className="mx-auto mt-6 max-w-[580px] text-base leading-relaxed text-[#a1a1a1] sm:text-[17px]">
          From topic to published video. AI writes the script, generates
          visuals, adds voiceover, and produces a complete faceless YouTube
          video — ready to upload.
        </p>

        {/* CTA Buttons */}
        <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          <Link
            href="/signup"
            className="glow-green-button inline-flex h-12 w-full items-center justify-center gap-2 rounded-full bg-[#10a37f] px-8 text-[15px] font-semibold text-white transition-all duration-150 hover:bg-[#0d8c6d] active:scale-[0.98] sm:w-auto"
          >
            Start Creating Free
            <ArrowRight className="h-4 w-4" />
          </Link>
          <a
            href="#demo"
            className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-full border border-white/[0.1] px-8 text-[15px] font-medium text-[#fafafa] transition-all duration-150 hover:border-white/[0.2] hover:bg-white/[0.03] sm:w-auto"
          >
            <Play className="h-4 w-4" />
            Watch Demo
          </a>
        </div>

        {/* Trust bar */}
        <div className="mt-12 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-[13px] text-[#666]">
          <span>No credit card required</span>
          <span className="hidden h-3 w-px bg-white/[0.08] sm:block" />
          <span>3 free videos</span>
          <span className="hidden h-3 w-px bg-white/[0.08] sm:block" />
          <span>Cancel anytime</span>
        </div>

        {/* Hero Visual / Dashboard Mockup */}
        <HeroVisual />
      </div>
    </section>
  );
}

/* ==========================================================================
   Logo / Social Proof Bar
   ========================================================================== */

const NICHE_LABELS = [
  "Finance",
  "Tech",
  "Education",
  "Health",
  "Business",
  "Crypto",
  "Self-Improvement",
  "True Crime",
  "History",
];

function SocialProofBar() {
  return (
    <section className="border-y border-white/[0.06] bg-white/[0.01] py-12 sm:py-16">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="flex flex-col items-center gap-8">
          <p className="text-sm font-medium text-[#666]">
            Trusted by creators making videos for
          </p>
          <div className="hide-scrollbar flex flex-wrap items-center justify-center gap-2 sm:gap-3">
            {NICHE_LABELS.map((label) => (
              <span
                key={label}
                className="rounded-full border border-white/[0.06] bg-white/[0.02] px-4 py-1.5 text-xs font-medium text-[#a1a1a1] transition-colors duration-150 hover:border-white/[0.1] hover:text-[#fafafa]"
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
    title: "Describe your video",
    description:
      "Enter any topic. AI generates a complete script with sections, hooks, and calls-to-action optimized for retention.",
    icon: Sparkles,
  },
  {
    number: "02",
    title: "Choose your style",
    description:
      "Pick from 10 visual styles — oil paintings, cinematic, anime, and more. AI creates matching visuals for every scene.",
    icon: Palette,
  },
  {
    number: "03",
    title: "Export & publish",
    description:
      "Download in 1080p or auto-publish to YouTube, TikTok, and Instagram. Complete with SEO-optimized metadata.",
    icon: Upload,
  },
];

function HowItWorksSection() {
  return (
    <section id="how-it-works" className="py-24 sm:py-32">
      <div className="mx-auto max-w-[1200px] px-6">
        {/* Section header */}
        <div className="mx-auto max-w-[600px] text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#10a37f]">
            How it works
          </p>
          <h2 className="mt-4 text-3xl font-bold tracking-tight text-[#fafafa] sm:text-4xl lg:text-[42px]">
            Three steps to your first video
          </h2>
          <p className="mt-4 text-base text-[#a1a1a1] sm:text-lg">
            No editing skills required. No camera needed. Just your ideas.
          </p>
        </div>

        {/* Steps */}
        <div className="mt-16 grid gap-5 sm:gap-6 md:grid-cols-3">
          {STEPS.map((step) => (
            <div
              key={step.number}
              className="bento-card group relative rounded-2xl border border-white/[0.06] bg-[#111] p-8"
            >
              {/* Step number */}
              <span className="font-mono text-xs font-semibold text-[#10a37f]">
                {step.number}
              </span>

              {/* Icon */}
              <div className="mt-4 flex h-11 w-11 items-center justify-center rounded-xl bg-[#10a37f]/10 transition-colors duration-200 group-hover:bg-[#10a37f]/15">
                <step.icon className="h-5 w-5 text-[#10a37f]" />
              </div>

              {/* Content */}
              <h3 className="mt-5 text-lg font-semibold text-[#fafafa]">
                {step.title}
              </h3>
              <p className="mt-2.5 text-sm leading-relaxed text-[#a1a1a1]">
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
   FAQ Section
   ========================================================================== */

const FAQ_ITEMS = [
  {
    question: "How does the AI generate videos?",
    answer:
      "AIVIDIO uses a multi-step pipeline: GPT-4o writes a researched script, our visual engine matches each section with imagery (stock footage, oil paintings, or AI-generated scenes), a neural voice narrates the script, and our editor assembles everything with transitions, captions, and background music.",
  },
  {
    question: "Can I edit the script before generating?",
    answer:
      "Absolutely. After the AI generates a script, you get a full editor where you can rewrite sections, adjust timing, change the tone, or add custom segments. You can also provide your own script from scratch.",
  },
  {
    question: "How long does it take to produce a video?",
    answer:
      "A typical 8-10 minute video takes about 5-8 minutes to produce. Stock footage videos render fastest, while AI-generated cinematic scenes take slightly longer. Pro and Business users get priority rendering.",
  },
  {
    question: "Do I own the videos I create?",
    answer:
      "Yes. All videos are yours to use commercially. Pro and Business plans include full commercial rights with no attribution required. Free plan videos include a small watermark.",
  },
  {
    question: "What YouTube niches work best?",
    answer:
      "Finance, history, true crime, motivation, technology explainers, top-10 lists, educational content, and news commentary. Any niche that uses narration over visuals is a great fit.",
  },
  {
    question: "How many visual styles are available?",
    answer:
      "10 styles: Oil Painting, Cinematic Realism, Anime, Watercolor, Dark Noir, Retro Vintage, Corporate Clean, Sci-Fi, Nature, and Stock Footage. Each is optimized for specific content types.",
  },
  {
    question: "Can I use AIVIDIO for YouTube monetization?",
    answer:
      "Yes. Videos created with AIVIDIO are eligible for YouTube monetization. The content is unique, original, and meets YouTube's guidelines for AI-assisted content when properly disclosed.",
  },
  {
    question: "Can I cancel anytime?",
    answer:
      "Yes. No contracts or cancellation fees. Cancel from your account settings anytime. You retain access until the end of your current billing period.",
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
        className="flex w-full items-center justify-between py-5 text-left transition-colors hover:text-[#fafafa]"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <span className="pr-4 text-[15px] font-medium text-[#fafafa]">
          {question}
        </span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-[#666] transition-transform duration-200 ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>
      <div
        className={`grid transition-all duration-300 ease-out ${
          open ? "grid-rows-[1fr] pb-5" : "grid-rows-[0fr]"
        }`}
      >
        <div className="overflow-hidden">
          <p className="text-sm leading-relaxed text-[#a1a1a1]">{answer}</p>
        </div>
      </div>
    </div>
  );
}

function FAQSection() {
  return (
    <section id="faq" className="py-24 sm:py-32">
      <div className="mx-auto max-w-[720px] px-6">
        {/* Section header */}
        <div className="text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#10a37f]">
            FAQ
          </p>
          <h2 className="mt-4 text-3xl font-bold tracking-tight text-[#fafafa] sm:text-4xl lg:text-[42px]">
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
   Final CTA Section
   ========================================================================== */

function CTASection() {
  return (
    <section className="py-24 sm:py-32">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="relative overflow-hidden rounded-3xl border border-white/[0.06] bg-[#111] p-12 text-center sm:p-20">
          {/* Background glow */}
          <div className="pointer-events-none absolute left-1/2 top-0 h-[400px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#10a37f]/[0.08] blur-[120px]" />
          <div className="pointer-events-none absolute bottom-0 left-1/2 h-[200px] w-[400px] -translate-x-1/2 translate-y-1/2 rounded-full bg-[#10a37f]/[0.04] blur-[80px]" />

          <div className="relative z-10">
            <h2 className="text-3xl font-bold tracking-tight text-[#fafafa] sm:text-4xl lg:text-5xl">
              Ready to create your first video?
            </h2>
            <p className="mx-auto mt-5 max-w-[480px] text-base text-[#a1a1a1] sm:text-lg">
              Start creating free — no credit card required.
            </p>
            <div className="mt-10">
              <Link
                href="/signup"
                className="glow-green-button inline-flex h-12 items-center gap-2 rounded-full bg-[#10a37f] px-8 text-[15px] font-semibold text-white transition-all duration-150 hover:bg-[#0d8c6d] active:scale-[0.98]"
              >
                Get Started Free
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
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
    <footer className="border-t border-white/[0.06] bg-[#050505] py-16">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="grid gap-12 sm:grid-cols-2 lg:grid-cols-6">
          {/* Brand */}
          <div className="lg:col-span-2">
            <Link href="/landing" className="flex items-center">
              <Image
                src="/aividio-logo.png"
                alt="AIVIDIO"
                width={120}
                height={32}
                className="invert brightness-200"
              />
            </Link>
            <p className="mt-4 max-w-[280px] text-sm leading-relaxed text-[#666]">
              AI-powered video creation for YouTube. From script to screen in
              minutes.
            </p>
            {/* Social links */}
            <div className="mt-6 flex gap-4">
              <a
                href="https://twitter.com"
                target="_blank"
                rel="noopener noreferrer"
                className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/[0.06] text-[#666] transition-colors hover:border-white/[0.1] hover:text-[#fafafa]"
                aria-label="X (Twitter)"
              >
                <svg
                  className="h-3.5 w-3.5"
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
                className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/[0.06] text-[#666] transition-colors hover:border-white/[0.1] hover:text-[#fafafa]"
                aria-label="YouTube"
              >
                <svg
                  className="h-3.5 w-3.5"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
                </svg>
              </a>
              <a
                href="https://discord.com"
                target="_blank"
                rel="noopener noreferrer"
                className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/[0.06] text-[#666] transition-colors hover:border-white/[0.1] hover:text-[#fafafa]"
                aria-label="Discord"
              >
                <svg
                  className="h-3.5 w-3.5"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z" />
                </svg>
              </a>
            </div>
          </div>

          {/* Link columns */}
          {Object.entries(FOOTER_LINKS).map(([heading, links]) => (
            <div key={heading}>
              <h4 className="text-xs font-semibold uppercase tracking-[0.15em] text-[#555]">
                {heading}
              </h4>
              <ul className="mt-4 flex flex-col gap-3">
                {links.map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      className="text-sm text-[#a1a1a1] transition-colors hover:text-[#fafafa]"
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
            &copy; 2025 AIVIDIO. All rights reserved.
          </p>
          <p className="text-xs text-[#333]">
            Built with AI, for AI creators.
          </p>
        </div>
      </div>
    </footer>
  );
}

/* ==========================================================================
   Landing Page — Full Assembly
   ========================================================================== */

export default function LandingPage() {
  return (
    <>
      <HeroSection />
      <SocialProofBar />
      <HowItWorksSection />
      <BentoGrid />
      <StyleShowcase />
      <PricingSection />
      <FAQSection />
      <CTASection />
      <Footer />
    </>
  );
}
