"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Menu, X } from "lucide-react";

interface LandingLayoutProps {
  children: React.ReactNode;
}

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
      className="text-sm text-[#999] transition-colors duration-150 hover:text-[#ececec]"
    >
      {children}
    </a>
  );
}

export default function LandingLayout({ children }: LandingLayoutProps) {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <div className="min-h-screen bg-[#0d0d0d]">
      {/* Sticky Navigation */}
      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled
            ? "bg-[#0d0d0d]/80 backdrop-blur-xl border-b border-white/[0.06]"
            : "bg-transparent"
        }`}
      >
        <div className="mx-auto max-w-[1200px] px-6">
          <div className="flex h-16 items-center justify-between">
            {/* Logo */}
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

            {/* Desktop Navigation */}
            <div className="hidden items-center gap-8 md:flex">
              <NavLink href="#features">Features</NavLink>
              <NavLink href="#pricing">Pricing</NavLink>
              <NavLink href="#faq">FAQ</NavLink>
            </div>

            {/* Desktop CTA */}
            <div className="hidden items-center gap-3 md:flex">
              <Button variant="ghost" size="sm" asChild>
                <Link href="/login">Sign In</Link>
              </Button>
              <Button size="sm" asChild>
                <Link href="/signup">Get Started</Link>
              </Button>
            </div>

            {/* Mobile Menu Toggle */}
            <button
              className="flex h-10 w-10 items-center justify-center rounded-lg text-[#999] transition-colors hover:bg-white/[0.06] hover:text-[#ececec] md:hidden"
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
        {mobileMenuOpen && (
          <div className="border-t border-white/[0.06] bg-[#0d0d0d]/95 backdrop-blur-xl md:hidden">
            <div className="flex flex-col gap-1 px-6 py-4">
              <NavLink
                href="#features"
                onClick={() => setMobileMenuOpen(false)}
              >
                Features
              </NavLink>
              <NavLink
                href="#pricing"
                onClick={() => setMobileMenuOpen(false)}
              >
                Pricing
              </NavLink>
              <NavLink href="#faq" onClick={() => setMobileMenuOpen(false)}>
                FAQ
              </NavLink>
              <div className="mt-4 flex flex-col gap-2">
                <Button variant="secondary" size="sm" asChild>
                  <Link href="/login">Sign In</Link>
                </Button>
                <Button size="sm" asChild>
                  <Link href="/signup">Get Started</Link>
                </Button>
              </div>
            </div>
          </div>
        )}
      </nav>

      {/* Page Content */}
      <main>{children}</main>
    </div>
  );
}
