"use client";

import { useState, useMemo, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

// ---------------------------------------------------------------------------
// Password strength
// ---------------------------------------------------------------------------

interface StrengthResult {
  score: number; // 0-4
  label: string;
  color: string;
}

function evaluatePassword(password: string): StrengthResult {
  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++;
  if (/\d/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;

  // Cap at 4
  score = Math.min(score, 4);

  const map: Record<number, { label: string; color: string }> = {
    0: { label: "Too weak", color: "#ef4444" },
    1: { label: "Weak", color: "#ef4444" },
    2: { label: "Fair", color: "#f59e0b" },
    3: { label: "Good", color: "#10a37f" },
    4: { label: "Strong", color: "#10a37f" },
  };

  return { score, ...map[score] };
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function SignupPage() {
  const router = useRouter();
  const { signup } = useAuth();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const strength = useMemo(() => evaluatePassword(password), [password]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (strength.score < 2) {
      setError(
        "Please choose a stronger password (at least 8 characters with a mix of cases and numbers)"
      );
      return;
    }

    setIsSubmitting(true);

    try {
      await signup(name, email, password);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0d0d0d] px-4 py-12">
      <div className="w-full max-w-[400px]">
        {/* Logo */}
        <div className="mb-10 flex flex-col items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#10a37f]">
            <span className="text-base font-bold text-white tracking-tight">
              Ai
            </span>
          </div>
          <h1 className="text-xl font-semibold text-[#ececec]">
            Create your account
          </h1>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-white/[0.06] bg-[#1a1a1a] p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Error */}
            {error && (
              <div className="rounded-xl border border-[#ef4444]/20 bg-[#ef4444]/[0.06] px-4 py-3 text-sm text-[#ef4444]">
                {error}
              </div>
            )}

            {/* Name */}
            <div className="space-y-2">
              <label
                htmlFor="name"
                className="block text-sm font-medium text-[#999]"
              >
                Full name
              </label>
              <Input
                id="name"
                type="text"
                placeholder="Jane Doe"
                autoComplete="name"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={isSubmitting}
              />
            </div>

            {/* Email */}
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

            {/* Password */}
            <div className="space-y-2">
              <label
                htmlFor="password"
                className="block text-sm font-medium text-[#999]"
              >
                Password
              </label>
              <Input
                id="password"
                type="password"
                placeholder="At least 8 characters"
                autoComplete="new-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isSubmitting}
              />
              {/* Strength indicator */}
              {password.length > 0 && (
                <div className="space-y-1.5 pt-1">
                  <div className="flex gap-1">
                    {Array.from({ length: 4 }).map((_, i) => (
                      <div
                        key={i}
                        className="h-1 flex-1 rounded-full transition-colors duration-200"
                        style={{
                          backgroundColor:
                            i < strength.score
                              ? strength.color
                              : "rgba(255,255,255,0.06)",
                        }}
                      />
                    ))}
                  </div>
                  <p
                    className="text-xs transition-colors duration-200"
                    style={{ color: strength.color }}
                  >
                    {strength.label}
                  </p>
                </div>
              )}
            </div>

            {/* Confirm password */}
            <div className="space-y-2">
              <label
                htmlFor="confirm-password"
                className="block text-sm font-medium text-[#999]"
              >
                Confirm password
              </label>
              <Input
                id="confirm-password"
                type="password"
                placeholder="Re-enter your password"
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={isSubmitting}
              />
            </div>

            {/* Submit */}
            <Button
              type="submit"
              className="w-full h-11"
              size="lg"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Creating account...
                </>
              ) : (
                "Create Account"
              )}
            </Button>
          </form>
        </div>

        {/* Footer link */}
        <p className="mt-6 text-center text-sm text-[#666]">
          Already have an account?{" "}
          <Link
            href="/login"
            className="text-[#10a37f] hover:underline underline-offset-2 transition-colors"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
