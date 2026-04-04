"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-medium transition-all duration-150 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#10a37f] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0d0d0d] disabled:pointer-events-none disabled:opacity-40 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-[#10a37f] text-white hover:bg-[#1a7f64] active:scale-[0.98]",
        secondary:
          "border border-white/[0.08] bg-transparent text-[#ececec] hover:border-white/[0.15] hover:bg-white/[0.04]",
        ghost:
          "text-[#999] hover:text-[#ececec] hover:bg-white/[0.06]",
        destructive:
          "bg-[#ef4444]/10 text-[#ef4444] hover:bg-[#ef4444]/20 active:scale-[0.98]",
        link:
          "text-[#10a37f] underline-offset-4 hover:underline p-0 h-auto",
      },
      size: {
        sm: "h-8 px-3 text-xs rounded-lg",
        default: "h-10 px-4 text-sm",
        lg: "h-12 px-6 text-sm",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
