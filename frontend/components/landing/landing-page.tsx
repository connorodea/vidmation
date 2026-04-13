"use client"

import { useState } from "react"
import Link from "next/link"
import {
  Play,
  ArrowRight,
  Check,
  Wand2,
  Mic2,
  Layers,
  Upload,
  ChevronRight,
  ChevronDown,
  Zap,
  Globe,
  Sparkles,
  Video,
} from "lucide-react"

/* ==========================================================================
   Navigation — Fixed, minimal, blur background
   ========================================================================== */

function Nav() {
  return (
    <nav className="fixed top-0 z-50 w-full">
      <div className="mx-auto flex h-14 max-w-[1200px] items-center justify-between px-6">
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-white">
              <Sparkles className="h-3.5 w-3.5 text-black" strokeWidth={2.5} />
            </div>
            <span className="text-[15px] font-semibold text-white tracking-[-0.01em]">
              AIVidio
            </span>
          </Link>
          <div className="hidden items-center gap-6 md:flex">
            {[
              { label: "Features", href: "#features" },
              { label: "How it works", href: "#how-it-works" },
              { label: "Pricing", href: "#pricing" },
              { label: "FAQ", href: "#faq" },
            ].map((item) => (
              <a
                key={item.label}
                href={item.href}
                className="text-[13px] text-white/40 transition-colors duration-200 hover:text-white/80"
              >
                {item.label}
              </a>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/login"
            className="hidden sm:block text-[13px] text-white/40 transition-colors duration-200 hover:text-white/80"
          >
            Log in
          </Link>
          <Link
            href="/signup"
            className="inline-flex h-8 items-center rounded-full bg-white px-4 text-[13px] font-medium text-black transition-all duration-200 hover:bg-white/90"
          >
            Get started
          </Link>
        </div>
      </div>
      <div className="h-px w-full bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />
    </nav>
  )
}

/* ==========================================================================
   Hero — Apple/OpenAI-inspired cinematic hero
   ========================================================================== */

function HeroSection() {
  return (
    <section className="relative flex min-h-[100vh] flex-col items-center justify-center overflow-hidden px-6 pt-14">
      {/* Ambient glow */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-1/3 h-[600px] w-[900px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/[0.02] blur-[120px]" />
        <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />
      </div>

      <div className="relative z-10 mx-auto max-w-[900px] text-center">
        {/* Announcement */}
        <Link
          href="/pricing"
          className="group mb-8 inline-flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.03] px-3.5 py-1.5 backdrop-blur-sm transition-colors duration-200 hover:border-white/[0.12] hover:bg-white/[0.05]"
        >
          <span className="flex h-5 items-center rounded-full bg-emerald-500/15 px-2 text-[11px] font-medium text-emerald-400">
            New
          </span>
          <span className="text-[13px] text-white/50">
            Batch production — create 10 videos at once
          </span>
          <ChevronRight className="h-3 w-3 text-white/30 transition-transform duration-200 group-hover:translate-x-0.5" />
        </Link>

        {/* Headline */}
        <h1 className="text-[clamp(44px,8vw,80px)] font-semibold leading-[1.05] tracking-[-0.04em] text-white">
          Create YouTube videos
          <br />
          <span className="bg-gradient-to-r from-white/40 via-white/20 to-white/40 bg-clip-text text-transparent">
            with AI
          </span>
        </h1>

        {/* Sub */}
        <p className="mx-auto mt-6 max-w-[480px] text-[17px] leading-relaxed text-white/40">
          From topic to published video in minutes. AI writes the script,
          generates visuals, adds voiceover, and produces a complete
          video — ready to upload.
        </p>

        {/* CTAs */}
        <div className="mt-10 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <Link
            href="/signup"
            className="inline-flex h-11 items-center gap-2 rounded-full bg-white px-6 text-[14px] font-medium text-black transition-all duration-200 hover:bg-white/90 hover:shadow-[0_0_20px_rgba(255,255,255,0.15)]"
          >
            Start creating free
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
          <a
            href="#demo"
            className="inline-flex h-11 items-center gap-2 rounded-full border border-white/[0.08] px-6 text-[14px] font-medium text-white/60 transition-all duration-200 hover:border-white/[0.15] hover:bg-white/[0.03] hover:text-white/80"
          >
            <Play className="h-3.5 w-3.5" />
            Watch demo
          </a>
        </div>

        {/* Trust */}
        <div className="mt-10 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-[13px] text-white/25">
          <span>No credit card required</span>
          <span className="hidden h-3 w-px bg-white/[0.08] sm:block" />
          <span>5 free videos</span>
          <span className="hidden h-3 w-px bg-white/[0.08] sm:block" />
          <span>Cancel anytime</span>
        </div>

        {/* Product mockup — floating dashboard preview */}
        <div className="relative mt-16 sm:mt-20">
          <div className="relative mx-auto max-w-[800px] overflow-hidden rounded-xl border border-white/[0.08] bg-[#111] shadow-2xl shadow-black/50">
            {/* Browser chrome */}
            <div className="flex h-10 items-center gap-2 border-b border-white/[0.06] px-4">
              <div className="flex gap-1.5">
                <div className="h-2.5 w-2.5 rounded-full bg-white/[0.08]" />
                <div className="h-2.5 w-2.5 rounded-full bg-white/[0.08]" />
                <div className="h-2.5 w-2.5 rounded-full bg-white/[0.08]" />
              </div>
              <div className="mx-auto flex h-6 w-48 items-center justify-center rounded-md bg-white/[0.04] text-[11px] text-white/20">
                aividio.com/dashboard
              </div>
            </div>
            {/* Dashboard content */}
            <div className="p-6">
              <div className="grid grid-cols-4 gap-3 mb-4">
                {[
                  { label: "Videos", value: "127" },
                  { label: "Uploaded", value: "89" },
                  { label: "Active Jobs", value: "3" },
                  { label: "Channels", value: "5" },
                ].map((stat) => (
                  <div key={stat.label} className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-3">
                    <div className="text-lg font-semibold text-white/80">{stat.value}</div>
                    <div className="text-[11px] text-white/25 mt-0.5">{stat.label}</div>
                  </div>
                ))}
              </div>
              <div className="space-y-2">
                {[
                  { title: "10 AI Business Ideas That Print Money", progress: 78, stage: "Assembling video" },
                  { title: "How Warren Buffett Really Thinks", progress: 35, stage: "Generating voiceover" },
                  { title: "The Dark Side of Cryptocurrency", progress: 95, stage: "Uploading to YouTube" },
                ].map((job) => (
                  <div key={job.title} className="flex items-center gap-4 rounded-lg border border-white/[0.06] bg-white/[0.02] px-4 py-3">
                    <div className="flex-1 min-w-0">
                      <div className="text-[13px] text-white/60 truncate">{job.title}</div>
                      <div className="text-[11px] text-white/25 mt-0.5">{job.stage}</div>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <div className="w-24 h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                        <div className="h-full rounded-full bg-emerald-500/60" style={{ width: `${job.progress}%` }} />
                      </div>
                      <span className="text-[11px] text-white/30 tabular-nums w-8 text-right">{job.progress}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="pointer-events-none absolute -bottom-1 left-0 right-0 h-32 bg-gradient-to-t from-black to-transparent" />
        </div>
      </div>
    </section>
  )
}

/* ==========================================================================
   Social Proof
   ========================================================================== */

function SocialProofBar() {
  const niches = [
    "Finance", "Tech Reviews", "Education", "Health & Wellness",
    "Business", "Crypto", "Self-Improvement", "True Crime",
    "History", "Science", "Motivation", "News Commentary",
  ]

  return (
    <section className="border-y border-white/[0.04] py-10 sm:py-12 overflow-hidden">
      <div className="mx-auto max-w-[1200px] px-6">
        <p className="text-center text-[12px] font-medium uppercase tracking-[0.15em] text-white/20 mb-8">
          Trusted by creators in every niche
        </p>
        <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-3">
          {niches.map((label) => (
            <span
              key={label}
              className="rounded-full border border-white/[0.06] bg-white/[0.02] px-4 py-1.5 text-[12px] font-medium text-white/30 transition-colors duration-200 hover:border-white/[0.1] hover:text-white/50"
            >
              {label}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ==========================================================================
   Features — Vercel-style bento grid with gap-px borders
   ========================================================================== */

function FeaturesSection() {
  const features = [
    { icon: Wand2, title: "AI Script Generation", desc: "Enter any topic. Get a research-backed, retention-optimized script with hooks, sections, and calls-to-action in seconds." },
    { icon: Mic2, title: "Neural Voice Synthesis", desc: "50+ natural-sounding voices. Clone your own voice with a single sample. ElevenLabs and OpenAI TTS built in." },
    { icon: Layers, title: "Intelligent Editing", desc: "Smart cuts, Ken Burns zoom, transitions, captions, B-roll, and background music — assembled automatically." },
    { icon: Upload, title: "One-Click Publishing", desc: "Publish directly to YouTube with AI-optimized titles, descriptions, and tags. Schedule or go live instantly." },
    { icon: Video, title: "10 Visual Styles", desc: "Oil painting, cinematic, anime, watercolor, dark noir, and more. Each creates a unique visual identity for your channel." },
    { icon: Globe, title: "Multi-Platform Export", desc: "Repurpose for TikTok, Instagram Reels, Facebook, and X. One video, every platform." },
  ]

  return (
    <section id="features" className="py-24 sm:py-32">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="mb-16">
          <p className="text-[12px] font-medium uppercase tracking-[0.2em] text-white/20 mb-4">Features</p>
          <h2 className="text-[clamp(28px,4vw,42px)] font-semibold tracking-[-0.03em] text-white">
            Everything you need to<br />
            <span className="text-white/25">automate video creation.</span>
          </h2>
        </div>

        <div className="grid gap-px rounded-2xl bg-white/[0.04] overflow-hidden sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div key={f.title} className="group bg-[#0a0a0a] p-8 sm:p-10 transition-colors duration-300 hover:bg-[#111]">
              <f.icon className="h-5 w-5 text-white/15 mb-6 transition-colors duration-300 group-hover:text-white/30" strokeWidth={1.5} />
              <h3 className="text-[16px] font-semibold text-white/90 tracking-[-0.01em]">{f.title}</h3>
              <p className="mt-2.5 text-[14px] text-white/35 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ==========================================================================
   How It Works
   ========================================================================== */

function HowItWorksSection() {
  const steps = [
    { number: "01", title: "Describe your video", desc: "Enter any topic or paste a script. Choose your channel, style, voice, and duration. The AI handles the rest.", icon: Sparkles },
    { number: "02", title: "AI produces everything", desc: "Script generation, voiceover synthesis, visual sourcing, smart editing, captions, music — all automated in under 5 minutes.", icon: Zap },
    { number: "03", title: "Review and publish", desc: "Preview your video, make adjustments if needed, then publish directly to YouTube or download in 1080p.", icon: Upload },
  ]

  return (
    <section id="how-it-works" className="border-t border-white/[0.04] py-24 sm:py-32">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="mb-16">
          <p className="text-[12px] font-medium uppercase tracking-[0.2em] text-white/20 mb-4">How it works</p>
          <h2 className="text-[clamp(28px,4vw,42px)] font-semibold tracking-[-0.03em] text-white">
            Three steps to your first video.
          </h2>
        </div>

        <div className="grid gap-8 sm:grid-cols-3 sm:gap-6">
          {steps.map((step) => (
            <div key={step.number} className="relative group">
              <div className="flex items-center gap-3 mb-4">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/[0.08] bg-white/[0.03] transition-colors duration-200 group-hover:border-white/[0.12] group-hover:bg-white/[0.05]">
                  <step.icon className="h-3.5 w-3.5 text-white/30" strokeWidth={2} />
                </div>
                <span className="text-[12px] font-mono text-white/15">{step.number}</span>
              </div>
              <h3 className="text-[18px] font-semibold text-white/90 tracking-[-0.01em]">{step.title}</h3>
              <p className="mt-2 text-[14px] text-white/35 leading-relaxed">{step.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ==========================================================================
   Stats
   ========================================================================== */

function StatsSection() {
  return (
    <section className="border-y border-white/[0.04] py-16 sm:py-20">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
          {[
            { value: "12K+", label: "Creators worldwide" },
            { value: "2.4M", label: "Videos generated" },
            { value: "4.9", label: "Average rating" },
            { value: "<3m", label: "Average generation time" },
          ].map((stat) => (
            <div key={stat.label}>
              <div className="text-[clamp(32px,5vw,48px)] font-semibold tracking-[-0.04em] text-white">{stat.value}</div>
              <div className="text-[13px] text-white/25 mt-1">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ==========================================================================
   Pricing
   ========================================================================== */

function PricingSection() {
  const plans = [
    { name: "Free", price: "$0", period: "", desc: "Get started with AI video creation.", features: ["5 videos per month", "720p export", "Standard voices", "Watermark", "Community support"], cta: "Get started", href: "/signup" },
    { name: "Pro", price: "$29", period: "/mo", desc: "For serious creators and growing channels.", features: ["50 videos per month", "1080p export", "All voices + cloning", "No watermark", "Priority rendering", "Analytics dashboard", "Multi-platform export"], cta: "Start free trial", href: "/signup", highlight: true },
    { name: "Business", price: "$79", period: "/mo", desc: "For agencies and multi-channel operations.", features: ["Unlimited videos", "4K export", "API access", "Custom branding", "Dedicated support", "Batch processing", "Webhook integrations"], cta: "Contact sales", href: "/signup" },
  ]

  return (
    <section id="pricing" className="border-t border-white/[0.04] py-24 sm:py-32">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="mb-16">
          <p className="text-[12px] font-medium uppercase tracking-[0.2em] text-white/20 mb-4">Pricing</p>
          <h2 className="text-[clamp(28px,4vw,42px)] font-semibold tracking-[-0.03em] text-white">Simple, transparent pricing.</h2>
          <p className="mt-3 text-[16px] text-white/35 max-w-md">Start free. Upgrade when you&apos;re ready.</p>
        </div>

        <div className="grid gap-px rounded-2xl bg-white/[0.04] overflow-hidden sm:grid-cols-3 max-w-4xl">
          {plans.map((plan) => (
            <div key={plan.name} className={`p-8 sm:p-10 ${plan.highlight ? "bg-white text-black" : "bg-[#0a0a0a]"}`}>
              <div className={`text-[13px] font-medium ${plan.highlight ? "text-black/40" : "text-white/25"}`}>{plan.name}</div>
              <div className="flex items-baseline mt-2 mb-2">
                <span className={`text-[40px] font-semibold tracking-[-0.04em] ${plan.highlight ? "text-black" : "text-white"}`}>{plan.price}</span>
                {plan.period && <span className={`text-[14px] ml-1 ${plan.highlight ? "text-black/30" : "text-white/20"}`}>{plan.period}</span>}
              </div>
              <p className={`text-[13px] mb-8 ${plan.highlight ? "text-black/40" : "text-white/30"}`}>{plan.desc}</p>
              <ul className="space-y-3 mb-8">
                {plan.features.map((feature) => (
                  <li key={feature} className={`flex items-center gap-2.5 text-[13px] ${plan.highlight ? "text-black/60" : "text-white/40"}`}>
                    <Check className={`h-3.5 w-3.5 shrink-0 ${plan.highlight ? "text-black/25" : "text-white/15"}`} strokeWidth={2} />
                    {feature}
                  </li>
                ))}
              </ul>
              <Link href={plan.href} className={`flex h-9 w-full items-center justify-center rounded-full text-[13px] font-medium transition-all duration-200 ${plan.highlight ? "bg-black text-white hover:bg-black/90" : "bg-white text-black hover:bg-white/90"}`}>
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ==========================================================================
   FAQ
   ========================================================================== */

const FAQ_ITEMS = [
  { question: "How does the AI generate videos?", answer: "AIVidio uses a multi-step pipeline: AI writes a researched script, our visual engine matches each section with imagery (stock footage, AI-generated scenes, or artistic styles like oil painting), a neural voice narrates the script, and our editor assembles everything with transitions, captions, and background music." },
  { question: "Can I edit the script before generating?", answer: "Yes. After the AI generates a script, you get a full editor where you can rewrite sections, adjust timing, change the tone, or add custom segments. You can also provide your own script from scratch." },
  { question: "How long does it take to produce a video?", answer: "A typical 8-10 minute video takes about 3-5 minutes to produce. Stock footage videos render fastest, while AI-generated cinematic scenes take slightly longer. Pro and Business users get priority rendering." },
  { question: "Do I own the videos I create?", answer: "Yes. All videos are yours to use commercially. Pro and Business plans include full commercial rights with no attribution required." },
  { question: "What YouTube niches work best?", answer: "Finance, history, true crime, motivation, technology explainers, top-10 lists, educational content, and news commentary. Any niche that uses narration over visuals is a great fit." },
  { question: "Can I use AIVidio for YouTube monetization?", answer: "Yes. Videos created with AIVidio are eligible for YouTube monetization. The content is unique, original, and meets YouTube's guidelines for AI-assisted content when properly disclosed." },
  { question: "What visual styles are available?", answer: "10 styles: Oil Painting, Cinematic Realism, Anime, Watercolor, Dark Noir, Retro Vintage, Corporate Clean, Sci-Fi, Nature Documentary, and Stock Footage. Each is optimized for specific content types." },
  { question: "Can I cancel anytime?", answer: "Yes. No contracts or cancellation fees. Cancel from your account settings anytime. You retain access until the end of your current billing period." },
]

function FAQItem({ question, answer }: { question: string; answer: string }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border-b border-white/[0.04]">
      <button className="flex w-full items-center justify-between py-5 text-left group" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span className="pr-4 text-[15px] font-medium text-white/80 group-hover:text-white transition-colors duration-200">{question}</span>
        <ChevronDown className={`h-4 w-4 shrink-0 text-white/20 transition-transform duration-300 ${open ? "rotate-180" : ""}`} />
      </button>
      <div className={`grid transition-all duration-300 ease-out ${open ? "grid-rows-[1fr] pb-5" : "grid-rows-[0fr]"}`}>
        <div className="overflow-hidden">
          <p className="text-[14px] leading-relaxed text-white/35">{answer}</p>
        </div>
      </div>
    </div>
  )
}

function FAQSection() {
  return (
    <section id="faq" className="border-t border-white/[0.04] py-24 sm:py-32">
      <div className="mx-auto max-w-[720px] px-6">
        <div className="mb-12">
          <p className="text-[12px] font-medium uppercase tracking-[0.2em] text-white/20 mb-4">FAQ</p>
          <h2 className="text-[clamp(28px,4vw,42px)] font-semibold tracking-[-0.03em] text-white">Frequently asked questions</h2>
        </div>
        <div>
          {FAQ_ITEMS.map((item) => (
            <FAQItem key={item.question} question={item.question} answer={item.answer} />
          ))}
        </div>
      </div>
    </section>
  )
}

/* ==========================================================================
   Final CTA
   ========================================================================== */

function CTASection() {
  return (
    <section className="border-t border-white/[0.04] py-24 sm:py-32">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="relative overflow-hidden rounded-2xl border border-white/[0.06] bg-[#0a0a0a] p-12 sm:p-20">
          <div className="pointer-events-none absolute left-1/2 top-0 h-[300px] w-[500px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/[0.03] blur-[100px]" />
          <div className="relative z-10 max-w-lg">
            <h2 className="text-[clamp(28px,4vw,42px)] font-semibold tracking-[-0.03em] text-white">
              Ready to create<br />your first video?
            </h2>
            <p className="mt-4 text-[16px] text-white/35 max-w-sm">
              Join 12,000+ creators automating their YouTube channels with AI. Start free — no credit card required.
            </p>
            <div className="mt-8">
              <Link href="/signup" className="inline-flex h-11 items-center gap-2 rounded-full bg-white px-6 text-[14px] font-medium text-black transition-all duration-200 hover:bg-white/90 hover:shadow-[0_0_20px_rgba(255,255,255,0.15)]">
                Get started free
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

/* ==========================================================================
   Footer
   ========================================================================== */

const FOOTER_LINKS = {
  Product: [
    { label: "Features", href: "#features" },
    { label: "Pricing", href: "#pricing" },
    { label: "API Docs", href: "#" },
    { label: "Changelog", href: "#" },
  ],
  Resources: [
    { label: "Blog", href: "#" },
    { label: "Tutorials", href: "#" },
    { label: "Help Center", href: "#" },
    { label: "Status", href: "#" },
  ],
  Company: [
    { label: "About", href: "#" },
    { label: "Contact", href: "#" },
    { label: "Privacy", href: "#" },
    { label: "Terms", href: "#" },
  ],
}

function Footer() {
  return (
    <footer className="border-t border-white/[0.04] py-12 sm:py-16">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-5">
          <div className="lg:col-span-2">
            <Link href="/" className="flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-md bg-white/[0.08]">
                <Sparkles className="h-3 w-3 text-white/40" strokeWidth={2.5} />
              </div>
              <span className="text-[14px] font-semibold text-white/40">AIVidio</span>
            </Link>
            <p className="mt-3 max-w-[260px] text-[13px] leading-relaxed text-white/20">
              AI-powered video creation for YouTube. From script to screen in minutes.
            </p>
          </div>
          {Object.entries(FOOTER_LINKS).map(([heading, links]) => (
            <div key={heading}>
              <h4 className="text-[12px] font-medium uppercase tracking-[0.1em] text-white/20 mb-4">{heading}</h4>
              <ul className="space-y-2.5">
                {links.map((link) => (
                  <li key={link.label}>
                    <a href={link.href} className="text-[13px] text-white/30 transition-colors duration-200 hover:text-white/60">{link.label}</a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-white/[0.04] pt-8 sm:flex-row">
          <p className="text-[12px] text-white/15">&copy; 2026 AIVidio. All rights reserved.</p>
          <p className="text-[12px] text-white/10">Built with AI, for AI creators.</p>
        </div>
      </div>
    </footer>
  )
}

/* ==========================================================================
   Landing Page — Full Assembly
   ========================================================================== */

export function LandingPage() {
  return (
    <div className="min-h-screen bg-black">
      <Nav />
      <HeroSection />
      <SocialProofBar />
      <FeaturesSection />
      <HowItWorksSection />
      <StatsSection />
      <PricingSection />
      <FAQSection />
      <CTASection />
      <Footer />
    </div>
  )
}
