"use client"

import { useState } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Logo } from "@/components/logo"
import { ArrowLeft, Check } from "lucide-react"

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isSubmitted, setIsSubmitted] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    await new Promise((resolve) => setTimeout(resolve, 1500))
    setIsSubmitted(true)
    setIsLoading(false)
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6">
      <div className="w-full max-w-[300px]">
        {isSubmitted ? (
          <div className="text-center">
            <div className="mb-6 inline-flex h-10 w-10 items-center justify-center rounded-full bg-foreground">
              <Check className="h-4 w-4 text-background" />
            </div>
            <h1 className="text-[20px] font-semibold tracking-tight">Check your email</h1>
            <p className="mt-2 text-[13px] text-foreground/50">
              If an account exists for {email}, we&apos;ve sent a reset link.
            </p>
            <Link href="/login">
              <Button variant="outline" className="mt-8 h-9 rounded-full px-4 text-[13px] border-foreground/10">
                <ArrowLeft className="mr-2 h-3.5 w-3.5" />
                Back to login
              </Button>
            </Link>
          </div>
        ) : (
          <>
            <div className="mb-8">
              <Link href="/" className="inline-block mb-8">
                <Logo />
              </Link>
              <h1 className="text-[20px] font-semibold tracking-tight">Forgot password?</h1>
              <p className="mt-1 text-[13px] text-foreground/50">
                Enter your email for a reset link.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-[12px] text-foreground/50 mb-1.5">
                  Email
                </label>
                <Input
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="h-9 text-[13px] rounded-lg border-foreground/10 bg-transparent"
                  required
                />
              </div>

              <Button
                type="submit"
                disabled={isLoading}
                className="w-full h-9 rounded-full text-[13px] bg-foreground text-background hover:bg-foreground/90"
              >
                {isLoading ? "Sending..." : "Send reset link"}
              </Button>
            </form>

            <p className="mt-6 text-center text-[12px] text-foreground/40">
              Remember your password?{" "}
              <Link href="/login" className="text-foreground hover:underline">
                Sign in
              </Link>
            </p>
          </>
        )}
      </div>
    </div>
  )
}
