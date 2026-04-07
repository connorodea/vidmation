"use client";

import { useState } from "react";
import Link from "next/link";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";

/* ---------- Data ---------- */

interface PricingTier {
  name: string;
  monthlyPrice: number;
  annualPrice: number;
  period: string;
  description: string;
  features: string[];
  cta: string;
  ctaHref: string;
  popular: boolean;
}

const TIERS: PricingTier[] = [
  {
    name: "Free",
    monthlyPrice: 0,
    annualPrice: 0,
    period: "forever",
    description: "Try AIVIDIO risk-free",
    features: [
      "3 videos per month",
      "720p export quality",
      "AIVIDIO watermark",
      "2 visual styles",
      "5 voice options",
      "Community support",
    ],
    cta: "Get Started",
    ctaHref: "/signup",
    popular: false,
  },
  {
    name: "Pro",
    monthlyPrice: 29,
    annualPrice: 23,
    period: "/month",
    description: "For creators ready to scale",
    features: [
      "30 videos per month",
      "1080p export quality",
      "No watermark",
      "All 10 visual styles",
      "35+ voice options",
      "Batch mode (10 at once)",
      "YouTube auto-upload",
      "Priority rendering",
    ],
    cta: "Start Free Trial",
    ctaHref: "/signup?plan=pro",
    popular: true,
  },
  {
    name: "Business",
    monthlyPrice: 79,
    annualPrice: 63,
    period: "/month",
    description: "For teams and agencies",
    features: [
      "Unlimited videos",
      "4K export quality",
      "No watermark",
      "All 10 visual styles",
      "35+ voice options",
      "API access",
      "White-label export",
      "Priority support",
      "Custom voice cloning",
      "Team collaboration",
    ],
    cta: "Contact Sales",
    ctaHref: "/signup?plan=business",
    popular: false,
  },
];

/* ---------- Card Component ---------- */

function PricingTierCard({
  tier,
  annual,
}: {
  tier: PricingTier;
  annual: boolean;
}) {
  const price = annual ? tier.annualPrice : tier.monthlyPrice;
  const displayPrice = price === 0 ? "$0" : `$${price}`;

  return (
    <div
      className={`relative flex flex-col rounded-2xl border p-8 transition-all duration-200 ${
        tier.popular
          ? "pricing-popular bg-[#10a37f]/[0.03]"
          : "border-white/[0.06] bg-[#111] hover:border-white/[0.1]"
      }`}
    >
      {/* Popular badge */}
      {tier.popular && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-[#10a37f] px-4 py-1 text-[11px] font-bold tracking-wide text-white">
          Most Popular
        </span>
      )}

      {/* Plan header */}
      <div>
        <h3 className="text-lg font-semibold text-[#fafafa]">{tier.name}</h3>
        <p className="mt-1 text-sm text-[#a1a1a1]">{tier.description}</p>
      </div>

      {/* Price */}
      <div className="mt-6 flex items-baseline gap-1">
        <span className="text-4xl font-bold tracking-tight text-[#fafafa]">
          {displayPrice}
        </span>
        <span className="text-sm text-[#666]">{tier.period}</span>
      </div>
      {annual && price > 0 && (
        <p className="mt-1 text-xs text-[#10a37f]">
          Save ${(tier.monthlyPrice - tier.annualPrice) * 12}/year
        </p>
      )}

      {/* CTA */}
      <Button
        variant={tier.popular ? "default" : "secondary"}
        className={`mt-6 w-full ${tier.popular ? "glow-green-button" : ""}`}
        asChild
      >
        <Link href={tier.ctaHref}>{tier.cta}</Link>
      </Button>

      {/* Divider */}
      <div className="my-6 h-px bg-white/[0.06]" />

      {/* Features */}
      <ul className="flex flex-col gap-3">
        {tier.features.map((feature) => (
          <li key={feature} className="flex items-start gap-3">
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-[#10a37f]" />
            <span className="text-sm text-[#a1a1a1]">{feature}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ---------- Pricing Section ---------- */

export function PricingSection() {
  const [annual, setAnnual] = useState(false);

  return (
    <section id="pricing" className="py-24 sm:py-32">
      <div className="mx-auto max-w-[1200px] px-6">
        {/* Section header */}
        <div className="mx-auto max-w-[600px] text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#10a37f]">
            Pricing
          </p>
          <h2 className="mt-4 text-3xl font-bold tracking-tight text-[#fafafa] sm:text-4xl lg:text-[42px]">
            Simple, transparent pricing
          </h2>
          <p className="mt-4 text-base text-[#a1a1a1] sm:text-lg">
            No hidden fees. No credit system. Just videos.
          </p>

          {/* Annual toggle */}
          <div className="mt-8 inline-flex items-center gap-3 rounded-full border border-white/[0.06] bg-[#111] px-4 py-2">
            <span
              className={`text-sm transition-colors ${
                !annual ? "font-medium text-[#fafafa]" : "text-[#666]"
              }`}
            >
              Monthly
            </span>
            <button
              onClick={() => setAnnual(!annual)}
              className={`relative h-6 w-11 rounded-full transition-colors duration-200 ${
                annual ? "bg-[#10a37f]" : "bg-[#333]"
              }`}
              aria-label="Toggle annual billing"
            >
              <div
                className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform duration-200 ${
                  annual ? "translate-x-[22px]" : "translate-x-0.5"
                }`}
              />
            </button>
            <span
              className={`text-sm transition-colors ${
                annual ? "font-medium text-[#fafafa]" : "text-[#666]"
              }`}
            >
              Annual
            </span>
            {annual && (
              <span className="rounded-full bg-[#10a37f]/10 px-2.5 py-0.5 text-[11px] font-semibold text-[#10a37f]">
                Save 20%
              </span>
            )}
          </div>
        </div>

        {/* Pricing cards */}
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {TIERS.map((tier) => (
            <PricingTierCard key={tier.name} tier={tier} annual={annual} />
          ))}
        </div>
      </div>
    </section>
  );
}
