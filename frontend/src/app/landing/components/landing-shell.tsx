"use client";

import Link from "next/link";
import Image from "next/image";
import { useState, useEffect } from "react";
import { Menu, X } from "lucide-react";

function NavLink({
  href,
  children,
  onClick,
}: {
  href: string;
  children: React.ReactNode;
  onClick?: () => void;
}) {
  return (
    <a
      href={href}
      onClick={onClick}
      className="text-[13px] font-medium text-[#a1a1a1] transition-colors duration-150 hover:text-[#fafafa]"
    >
      {children}
    </a>
  );
}

export function LandingShell({ children }: { children: React.ReactNode }) {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <div className="min-h-screen bg-black">
      {/* Sticky Navigation */}
      <nav
        className={`fixed left-0 right-0 top-0 z-50 transition-all duration-300 ${
          scrolled
            ? "border-b border-white/[0.06] bg-black/80 backdrop-blur-xl"
            : "bg-transparent"
        }`}
      >
        <div className="mx-auto max-w-[1200px] px-6">
          <div className="flex h-16 items-center justify-between">
            {/* Logo */}
            <Link href="/landing" className="flex items-center">
              <Image
                src="/aividio-logo.png"
                alt="AIVIDIO"
                width={120}
                height={32}
                className="invert brightness-200"
                priority
              />
            </Link>

            {/* Desktop Navigation — center */}
            <div className="hidden items-center gap-8 md:flex">
              <NavLink href="#features">Features</NavLink>
              <NavLink href="#how-it-works">How it Works</NavLink>
              <NavLink href="#pricing">Pricing</NavLink>
            </div>

            {/* Desktop CTA — right */}
            <div className="hidden items-center gap-4 md:flex">
              <Link
                href="/login"
                className="text-[13px] font-medium text-[#a1a1a1] transition-colors duration-150 hover:text-[#fafafa]"
              >
                Log in
              </Link>
              <Link
                href="/signup"
                className="glow-green-sm inline-flex h-9 items-center rounded-full bg-[#10a37f] px-5 text-[13px] font-semibold text-white transition-all duration-150 hover:bg-[#0d8c6d] active:scale-[0.98]"
              >
                Get Started Free
              </Link>
            </div>

            {/* Mobile Menu Toggle */}
            <button
              className="flex h-10 w-10 items-center justify-center rounded-lg text-[#a1a1a1] transition-colors hover:bg-white/[0.06] hover:text-[#fafafa] md:hidden"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
            >
              {mobileMenuOpen ? (
                <X className="h-5 w-5" />
              ) : (
                <Menu className="h-5 w-5" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        <div
          className={`overflow-hidden border-t border-white/[0.06] bg-black/95 backdrop-blur-xl transition-all duration-300 md:hidden ${
            mobileMenuOpen ? "max-h-80 opacity-100" : "max-h-0 opacity-0 border-transparent"
          }`}
        >
          <div className="flex flex-col gap-1 px-6 py-4">
            <NavLink
              href="#features"
              onClick={() => setMobileMenuOpen(false)}
            >
              Features
            </NavLink>
            <NavLink
              href="#how-it-works"
              onClick={() => setMobileMenuOpen(false)}
            >
              How it Works
            </NavLink>
            <NavLink
              href="#pricing"
              onClick={() => setMobileMenuOpen(false)}
            >
              Pricing
            </NavLink>
            <div className="mt-4 flex flex-col gap-2">
              <Link
                href="/login"
                className="flex h-10 items-center justify-center rounded-xl border border-white/[0.08] text-sm font-medium text-[#fafafa] transition-colors hover:bg-white/[0.04]"
              >
                Log in
              </Link>
              <Link
                href="/signup"
                className="flex h-10 items-center justify-center rounded-xl bg-[#10a37f] text-sm font-semibold text-white transition-colors hover:bg-[#0d8c6d]"
              >
                Get Started Free
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Page Content */}
      <main>{children}</main>
    </div>
  );
}
