"use client"

import { useState, useMemo } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Logo } from "@/components/logo"
import { Spinner } from "@/components/ui/spinner"
import { Eye, EyeOff, Check, X } from "lucide-react"

export default function SignupPage() {
  const router = useRouter()
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const passwordRequirements = useMemo(() => ({
    minLength: password.length >= 8,
    hasUpper: /[A-Z]/.test(password),
    hasLower: /[a-z]/.test(password),
    hasDigit: /[0-9]/.test(password),
  }), [password])

  const isPasswordValid = Object.values(passwordRequirements).every(Boolean)

  const [error, setError] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isPasswordValid) return
    setError("")
    setIsLoading(true)

    try {
      const res = await fetch("/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || "Signup failed")
      }

      const tokens = await res.json()
      localStorage.setItem("access_token", tokens.access_token)
      localStorage.setItem("refresh_token", tokens.refresh_token)
      router.push("/dashboard")
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Signup failed")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4">
      <div className="w-full max-w-[320px]">
        <div className="mb-8 flex justify-center">
          <Link href="/">
            <Logo size="lg" />
          </Link>
        </div>

        <div className="mb-8 text-center">
          <h1 className="text-[24px] font-semibold tracking-tight text-foreground">
            Create account
          </h1>
          <p className="mt-2 text-[13px] text-foreground/50">
            Get started with 5 free videos
          </p>
          {error && (
            <p className="mt-3 text-[13px] text-destructive">{error}</p>
          )}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label className="text-[12px] text-foreground/70">Name</Label>
            <Input
              type="text"
              placeholder="John Doe"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="h-10 rounded-lg border-foreground/10 bg-background px-3 text-[13px]"
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-[12px] text-foreground/70">Email</Label>
            <Input
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="h-10 rounded-lg border-foreground/10 bg-background px-3 text-[13px]"
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-[12px] text-foreground/70">Password</Label>
            <div className="relative">
              <Input
                type={showPassword ? "text" : "password"}
                placeholder="Create a password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="h-10 rounded-lg border-foreground/10 bg-background px-3 pr-10 text-[13px]"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-foreground/40 hover:text-foreground"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {password && (
              <div className="mt-2 grid grid-cols-2 gap-1.5">
                {[
                  { key: "minLength", label: "8+ chars" },
                  { key: "hasUpper", label: "Uppercase" },
                  { key: "hasLower", label: "Lowercase" },
                  { key: "hasDigit", label: "Number" },
                ].map(({ key, label }) => (
                  <div
                    key={key}
                    className={`flex items-center gap-1.5 text-[10px] ${
                      passwordRequirements[key as keyof typeof passwordRequirements]
                        ? "text-foreground"
                        : "text-foreground/30"
                    }`}
                  >
                    {passwordRequirements[key as keyof typeof passwordRequirements] ? (
                      <Check className="h-3 w-3" />
                    ) : (
                      <X className="h-3 w-3" />
                    )}
                    {label}
                  </div>
                ))}
              </div>
            )}
          </div>

          <Button
            type="submit"
            className="h-10 w-full rounded-lg bg-foreground text-[13px] font-medium text-background hover:bg-foreground/90"
            disabled={isLoading || !isPasswordValid}
          >
            {isLoading ? <Spinner className="h-4 w-4" /> : "Create account"}
          </Button>
        </form>

        <div className="my-6 flex items-center gap-4">
          <div className="h-px flex-1 bg-foreground/10" />
          <span className="text-[11px] text-foreground/40">or</span>
          <div className="h-px flex-1 bg-foreground/10" />
        </div>

        <div className="space-y-2">
          <Button variant="outline" className="h-10 w-full rounded-lg border-foreground/10 text-[12px]">
            <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24">
              <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
              <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
              <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
            Continue with Google
          </Button>
          <Button variant="outline" className="h-10 w-full rounded-lg border-foreground/10 text-[12px]">
            <svg className="mr-2 h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
            </svg>
            Continue with GitHub
          </Button>
        </div>

        <p className="mt-6 text-center text-[11px] text-foreground/40">
          By signing up, you agree to our{" "}
          <Link href="#" className="text-foreground/60 hover:text-foreground">Terms</Link>
          {" "}and{" "}
          <Link href="#" className="text-foreground/60 hover:text-foreground">Privacy Policy</Link>
        </p>

        <p className="mt-6 text-center text-[12px] text-foreground/50">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-foreground hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
