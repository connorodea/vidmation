"use client"

import { useState } from "react"
import Link from "next/link"
import { Logo } from "@/components/logo"
import { Button } from "@/components/ui/button"
import { Check } from "lucide-react"
import { cn } from "@/lib/utils"

const tiers = [
  {
    name: "Free",
    price: "$0",
    description: "Perfect for trying out AIVidio",
    features: [
      "3 videos per month",
      "720p resolution",
      "Basic styles only",
      "AIVidio watermark",
      "Email support",
    ],
    cta: "Get Started",
    href: "/signup",
  },
  {
    name: "Pro",
    price: "$29",
    description: "For creators who want more",
    features: [
      "30 videos per month",
      "1080p resolution",
      "All 10 visual styles",
      "No watermark",
      "Batch video generation",
      "Priority rendering",
      "Content calendar",
      "Voice cloning",
    ],
    cta: "Start Free Trial",
    href: "/signup?plan=pro",
    highlighted: true,
  },
  {
    name: "Business",
    price: "$79",
    description: "For teams and agencies",
    features: [
      "Unlimited videos",
      "4K resolution",
      "All Pro features",
      "API access",
      "White-label exports",
      "Webhooks",
      "Priority support",
      "Custom integrations",
    ],
    cta: "Contact Sales",
    href: "/signup?plan=business",
  },
]

const faqs = [
  {
    q: "Can I cancel anytime?",
    a: "Yes, you can cancel your subscription at any time. You'll continue to have access until the end of your billing period.",
  },
  {
    q: "What payment methods do you accept?",
    a: "We accept all major credit cards (Visa, Mastercard, American Express) through Stripe.",
  },
  {
    q: "Is there a free trial?",
    a: "Yes, Pro and Business plans come with a 7-day free trial. No credit card required to start.",
  },
  {
    q: "What happens if I exceed my video limit?",
    a: "You can purchase additional videos as one-time add-ons, or upgrade to a higher tier for more capacity.",
  },
]

export default function PricingPage() {
  const [annual, setAnnual] = useState(false)

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-xl border-b border-foreground/5">
        <div className="max-w-6xl mx-auto px-6 h-12 flex items-center justify-between">
          <Link href="/">
            <Logo size="sm" />
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-[12px] text-foreground/50 hover:text-foreground transition-colors">
              Sign in
            </Link>
            <Button asChild size="sm" className="h-7 px-3 text-[11px] rounded-lg bg-foreground text-background hover:bg-foreground/90">
              <Link href="/signup">Get Started</Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="pt-24 pb-20">
        {/* Hero */}
        <section className="max-w-4xl mx-auto px-6 text-center mb-16">
          <h1 className="text-[40px] font-semibold tracking-tight text-foreground mb-3">
            Simple pricing
          </h1>
          <p className="text-[15px] text-foreground/50 max-w-lg mx-auto">
            Choose the plan that fits your needs. Upgrade or downgrade anytime.
          </p>

          {/* Billing toggle */}
          <div className="flex items-center justify-center gap-3 mt-8">
            <span className={cn("text-[12px]", !annual ? "text-foreground" : "text-foreground/40")}>
              Monthly
            </span>
            <button
              onClick={() => setAnnual(!annual)}
              className={cn(
                "relative w-10 h-5 rounded-full transition-colors",
                annual ? "bg-foreground" : "bg-foreground/20"
              )}
            >
              <span
                className={cn(
                  "absolute top-0.5 left-0.5 w-4 h-4 bg-background rounded-full transition-transform",
                  annual && "translate-x-5"
                )}
              />
            </button>
            <span className={cn("text-[12px]", annual ? "text-foreground" : "text-foreground/40")}>
              Annual
              <span className="ml-1.5 text-[10px] text-foreground/60">Save 20%</span>
            </span>
          </div>
        </section>

        {/* Pricing Cards */}
        <section className="max-w-5xl mx-auto px-6 mb-24">
          <div className="grid md:grid-cols-3 gap-px bg-foreground/10 rounded-2xl overflow-hidden">
            {tiers.map((tier) => (
              <div
                key={tier.name}
                className={cn(
                  "relative p-6 bg-background",
                  tier.highlighted && "bg-foreground text-background"
                )}
              >
                {tier.highlighted && (
                  <div className="absolute -top-px left-0 right-0 h-0.5 bg-background" />
                )}
                <div className="mb-6">
                  <h3 className={cn(
                    "text-[14px] font-semibold mb-1",
                    tier.highlighted ? "text-background" : "text-foreground"
                  )}>
                    {tier.name}
                  </h3>
                  <p className={cn(
                    "text-[11px]",
                    tier.highlighted ? "text-background/60" : "text-foreground/50"
                  )}>
                    {tier.description}
                  </p>
                </div>
                <div className="mb-6">
                  <span className={cn(
                    "text-[36px] font-semibold tracking-tight",
                    tier.highlighted ? "text-background" : "text-foreground"
                  )}>
                    {tier.price === "$0" ? "$0" : annual ? `$${parseInt(tier.price.slice(1)) * 10}` : tier.price}
                  </span>
                  <span className={cn(
                    "text-[12px] ml-1",
                    tier.highlighted ? "text-background/60" : "text-foreground/50"
                  )}>
                    /{annual && tier.price !== "$0" ? "year" : "month"}
                  </span>
                </div>
                <Button
                  asChild
                  className={cn(
                    "w-full h-9 text-[12px] rounded-lg mb-6",
                    tier.highlighted
                      ? "bg-background text-foreground hover:bg-background/90"
                      : "bg-foreground text-background hover:bg-foreground/90"
                  )}
                >
                  <Link href={tier.href}>{tier.cta}</Link>
                </Button>
                <ul className="space-y-2.5">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2">
                      <Check className={cn(
                        "w-3.5 h-3.5 mt-0.5 flex-shrink-0",
                        tier.highlighted ? "text-background/60" : "text-foreground/40"
                      )} />
                      <span className={cn(
                        "text-[11px]",
                        tier.highlighted ? "text-background/80" : "text-foreground/70"
                      )}>
                        {feature}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        {/* FAQ */}
        <section className="max-w-2xl mx-auto px-6">
          <h2 className="text-[24px] font-semibold tracking-tight text-center mb-10">
            Frequently asked questions
          </h2>
          <div className="space-y-6">
            {faqs.map((faq) => (
              <div key={faq.q} className="border-b border-foreground/10 pb-6">
                <h3 className="text-[13px] font-medium text-foreground mb-2">{faq.q}</h3>
                <p className="text-[12px] text-foreground/50 leading-relaxed">{faq.a}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-foreground/5 py-8">
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-between">
          <p className="text-[11px] text-foreground/40">
            2026 AIVidio. All rights reserved.
          </p>
          <div className="flex items-center gap-6">
            <Link href="/privacy" className="text-[11px] text-foreground/40 hover:text-foreground transition-colors">
              Privacy
            </Link>
            <Link href="/terms" className="text-[11px] text-foreground/40 hover:text-foreground transition-colors">
              Terms
            </Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
