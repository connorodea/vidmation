"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Loader2, CheckCircle2 } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const res = await fetch(`${API_BASE}/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      if (!res.ok) {
        const err = await res
          .json()
          .catch(() => ({ detail: "Request failed" }));
        throw new Error(err.detail || "Could not send reset link");
      }

      setSubmitted(true);
    } catch (err) {
      // Always show success to prevent email enumeration
      setSubmitted(true);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0d0d0d] px-4">
      <div className="w-full max-w-[400px]">
        {/* Logo */}
        <div className="mb-10 flex flex-col items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#10a37f]">
            <span className="text-base font-bold text-white tracking-tight">
              Ai
            </span>
          </div>
          <h1 className="text-xl font-semibold text-[#ececec]">
            Reset your password
          </h1>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-white/[0.06] bg-[#1a1a1a] p-8">
          {submitted ? (
            /* Success state */
            <div className="flex flex-col items-center gap-4 py-2 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#10a37f]/10">
                <CheckCircle2 className="h-6 w-6 text-[#10a37f]" />
              </div>
              <div className="space-y-1.5">
                <p className="text-sm font-medium text-[#ececec]">
                  Check your email
                </p>
                <p className="text-sm text-[#666] leading-relaxed">
                  If an account exists for{" "}
                  <span className="text-[#999]">{email}</span>, we sent a link
                  to reset your password.
                </p>
              </div>
              <Link
                href="/login"
                className="mt-2 inline-flex items-center gap-1.5 text-sm text-[#10a37f] hover:underline underline-offset-2 transition-colors"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Back to sign in
              </Link>
            </div>
          ) : (
            /* Form state */
            <>
              <p className="mb-6 text-sm text-[#666] leading-relaxed">
                Enter the email address associated with your account and
                we&apos;ll send you a link to reset your password.
              </p>
              <form onSubmit={handleSubmit} className="space-y-5">
                {error && (
                  <div className="rounded-xl border border-[#ef4444]/20 bg-[#ef4444]/[0.06] px-4 py-3 text-sm text-[#ef4444]">
                    {error}
                  </div>
                )}

                <div className="space-y-2">
                  <label
                    htmlFor="email"
                    className="block text-sm font-medium text-[#999]"
                  >
                    Email address
                  </label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={isSubmitting}
                  />
                </div>

                <Button
                  type="submit"
                  className="w-full h-11"
                  size="lg"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Sending...
                    </>
                  ) : (
                    "Send Reset Link"
                  )}
                </Button>
              </form>
            </>
          )}
        </div>

        {/* Footer link */}
        {!submitted && (
          <p className="mt-6 text-center">
            <Link
              href="/login"
              className="inline-flex items-center gap-1.5 text-sm text-[#666] hover:text-[#999] transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Back to sign in
            </Link>
          </p>
        )}
      </div>
    </div>
  );
}
