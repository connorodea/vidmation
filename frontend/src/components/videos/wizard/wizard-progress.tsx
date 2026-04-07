"use client";

import { cn } from "@/lib/utils";
import { Check } from "lucide-react";

const STEPS = [
  { number: 1, label: "Topic & Style" },
  { number: 2, label: "Script" },
  { number: 3, label: "Voice & Music" },
  { number: 4, label: "Visuals" },
  { number: 5, label: "Review" },
];

interface WizardProgressProps {
  currentStep: number;
}

export function WizardProgress({ currentStep }: WizardProgressProps) {
  return (
    <nav aria-label="Wizard progress" className="w-full">
      <ol className="flex items-center justify-between">
        {STEPS.map((step, index) => {
          const isCompleted = currentStep > step.number;
          const isCurrent = currentStep === step.number;
          const isUpcoming = currentStep < step.number;

          return (
            <li
              key={step.number}
              className="flex items-center flex-1 last:flex-none"
            >
              <div className="flex flex-col items-center gap-2">
                {/* Step circle */}
                <div
                  className={cn(
                    "flex h-9 w-9 items-center justify-center rounded-full text-sm font-medium transition-all duration-300",
                    isCompleted &&
                      "bg-[#10a37f] text-white",
                    isCurrent &&
                      "bg-[#10a37f]/15 text-[#10a37f] ring-2 ring-[#10a37f]/40",
                    isUpcoming &&
                      "bg-white/[0.04] text-[#666] border border-white/[0.08]"
                  )}
                  aria-current={isCurrent ? "step" : undefined}
                >
                  {isCompleted ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    step.number
                  )}
                </div>

                {/* Step label */}
                <span
                  className={cn(
                    "text-xs font-medium whitespace-nowrap transition-colors duration-300",
                    isCompleted && "text-[#10a37f]",
                    isCurrent && "text-[#ececec]",
                    isUpcoming && "text-[#666]"
                  )}
                >
                  {step.label}
                </span>
              </div>

              {/* Connector line */}
              {index < STEPS.length - 1 && (
                <div
                  className={cn(
                    "h-px flex-1 mx-3 mt-[-20px] transition-colors duration-500",
                    currentStep > step.number + 1
                      ? "bg-[#10a37f]"
                      : currentStep > step.number
                        ? "bg-[#10a37f]/40"
                        : "bg-white/[0.06]"
                  )}
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
