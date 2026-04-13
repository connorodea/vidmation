"use client"

import Image from "next/image"
import { cn } from "@/lib/utils"

interface LogoProps {
  className?: string
  size?: "sm" | "md" | "lg"
  inverted?: boolean
}

export function Logo({ className, size = "md", inverted = false }: LogoProps) {
  const sizes = {
    sm: { width: 80, height: 20 },
    md: { width: 100, height: 25 },
    lg: { width: 120, height: 30 },
  }

  return (
    <Image
      src="/logo.png"
      alt="AIVIDIO"
      width={sizes[size].width}
      height={sizes[size].height}
      className={cn(
        "object-contain",
        inverted && "invert",
        className
      )}
      style={{ width: 'auto', height: sizes[size].height }}
      priority
    />
  )
}
