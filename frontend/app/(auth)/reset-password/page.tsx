"use client"

import { useState, Suspense } from "react"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { Logo } from "@/components/logo"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Eye, EyeOff, Check, ArrowLeft } from "lucide-react"

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><div className="text-foreground/30 text-sm">Loading...</div></div>}>
      <ResetPasswordContent />
    </Suspense>
  )
}

function ResetPasswordContent() {
  const searchParams = useSearchParams()
  const token = searchParams.get("token")
  
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)

  const hasUppercase = /[A-Z]/.test(password)
  const hasLowercase = /[a-z]/.test(password)
  const hasDigit = /\d/.test(password)
  const hasMinLength = password.length >= 8
  const passwordsMatch = password === confirmPassword && password.length > 0
  const isValid = hasUppercase && hasLowercase && hasDigit && hasMinLength && passwordsMatch

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isValid || !token) return
    setIsLoading(true)
    await new Promise((r) => setTimeout(r, 1500))
    setIsLoading(false)
    setIsSuccess(true)
  }

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6">
        <div className="w-full max-w-[300px] text-center">
          <div className="mb-6 inline-flex h-10 w-10 items-center justify-center rounded-full bg-foreground/10">
            <span className="text-[14px]">?</span>
          </div>
          <h1 className="text-[20px] font-semibold tracking-tight mb-2">Invalid link</h1>
          <p className="text-[13px] text-foreground/50 mb-6">
            This reset link is invalid or expired.
          </p>
          <Button asChild className="h-9 rounded-full px-5 text-[13px] bg-foreground text-background hover:bg-foreground/90">
            <Link href="/forgot-password">Request new link</Link>
          </Button>
        </div>
      </div>
    )
  }

  if (isSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6">
        <div className="w-full max-w-[300px] text-center">
          <div className="mb-6 inline-flex h-10 w-10 items-center justify-center rounded-full bg-foreground">
            <Check className="h-4 w-4 text-background" />
          </div>
          <h1 className="text-[20px] font-semibold tracking-tight mb-2">Password reset</h1>
          <p className="text-[13px] text-foreground/50 mb-6">
            You can now sign in with your new password.
          </p>
          <Button asChild className="h-9 rounded-full px-5 text-[13px] bg-foreground text-background hover:bg-foreground/90">
            <Link href="/login">Sign in</Link>
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-[300px]">
        <Link
          href="/login"
          className="inline-flex items-center gap-1.5 text-[12px] text-foreground/40 hover:text-foreground transition-colors mb-8"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back
        </Link>

        <Link href="/" className="inline-block mb-8">
          <Logo />
        </Link>

        <h1 className="text-[20px] font-semibold tracking-tight mb-1">
          Reset password
        </h1>
        <p className="text-[13px] text-foreground/50 mb-8">
          Enter your new password.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-[12px] text-foreground/50 mb-1.5">
              New password
            </label>
            <div className="relative">
              <Input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter new password"
                className="h-9 text-[13px] rounded-lg pr-9 border-foreground/10 bg-transparent"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-foreground/30 hover:text-foreground"
              >
                {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          {password.length > 0 && (
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: "8+ chars", valid: hasMinLength },
                { label: "Uppercase", valid: hasUppercase },
                { label: "Lowercase", valid: hasLowercase },
                { label: "Number", valid: hasDigit },
              ].map((req) => (
                <div key={req.label} className="flex items-center gap-1.5">
                  <div className={`w-3 h-3 rounded-full flex items-center justify-center ${req.valid ? "bg-foreground" : "bg-foreground/10"}`}>
                    {req.valid && <Check className="w-2 h-2 text-background" />}
                  </div>
                  <span className={`text-[11px] ${req.valid ? "text-foreground" : "text-foreground/40"}`}>
                    {req.label}
                  </span>
                </div>
              ))}
            </div>
          )}

          <div>
            <label className="block text-[12px] text-foreground/50 mb-1.5">
              Confirm password
            </label>
            <Input
              type={showPassword ? "text" : "password"}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Confirm password"
              className="h-9 text-[13px] rounded-lg border-foreground/10 bg-transparent"
            />
            {confirmPassword.length > 0 && !passwordsMatch && (
              <p className="text-[11px] text-foreground/50 mt-1.5">Passwords do not match</p>
            )}
          </div>

          <Button
            type="submit"
            disabled={!isValid || isLoading}
            className="w-full h-9 rounded-full text-[13px] bg-foreground text-background hover:bg-foreground/90 disabled:opacity-30"
          >
            {isLoading ? "Resetting..." : "Reset password"}
          </Button>
        </form>
      </div>
    </div>
  )
}
