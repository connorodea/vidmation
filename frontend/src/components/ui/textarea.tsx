import * as React from "react";
import { cn } from "@/lib/utils";

const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => {
  return (
    <textarea
      className={cn(
        "flex min-h-[80px] w-full rounded-xl border border-white/[0.08] bg-[#1a1a1a] px-3.5 py-3 text-sm text-[#ececec] placeholder:text-[#666] transition-colors duration-150 ease-out resize-none focus-visible:outline-none focus-visible:border-[#10a37f] focus-visible:ring-1 focus-visible:ring-[#10a37f]/30 disabled:cursor-not-allowed disabled:opacity-40",
        className
      )}
      ref={ref}
      {...props}
    />
  );
});
Textarea.displayName = "Textarea";

export { Textarea };
