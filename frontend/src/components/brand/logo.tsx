"use client";

import Image from "next/image";
import { cn } from "@/lib/utils";

interface LogoProps {
  size?: "sm" | "md" | "lg" | "xl";
  showText?: boolean;
  variant?: "light" | "dark";
  className?: string;
}

const sizes = {
  sm: { width: 90, height: 24, iconSize: 24 },
  md: { width: 120, height: 32, iconSize: 32 },
  lg: { width: 160, height: 42, iconSize: 42 },
  xl: { width: 200, height: 52, iconSize: 52 },
};

export function Logo({
  size = "md",
  showText = true,
  variant = "dark",
  className,
}: LogoProps) {
  const s = sizes[size];
  const invert = variant === "dark";

  if (!showText) {
    return (
      <div className={cn("flex items-center", className)}>
        <Image
          src="/aividio-monogram.png"
          alt="AIVIDIO"
          width={s.iconSize}
          height={s.iconSize}
          className={cn(invert && "invert brightness-200")}
          priority
        />
      </div>
    );
  }

  return (
    <div className={cn("flex items-center", className)}>
      <Image
        src="/aividio-logo.png"
        alt="AIVIDIO"
        width={s.width}
        height={s.height}
        className={cn(invert && "invert brightness-200")}
        priority
      />
    </div>
  );
}
