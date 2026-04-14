import { clsx } from "clsx";
import { Check } from "lucide-react";

interface Step {
  label: string;
  description?: string;
}

interface StepIndicatorProps {
  steps: Step[];
  currentStep: number;
  variant?: "horizontal" | "vertical";
  className?: string;
}

export function StepIndicator({
  steps,
  currentStep,
  variant = "horizontal",
  className,
}: StepIndicatorProps) {
  const isHorizontal = variant === "horizontal";

  return (
    <nav
      aria-label="Progress"
      className={clsx(
        isHorizontal ? "flex items-center" : "flex flex-col",
        className
      )}
    >
      {steps.map((step, index) => {
        const isCompleted = index < currentStep;
        const isCurrent = index === currentStep;
        const isUpcoming = index > currentStep;

        return (
          <div
            key={index}
            className={clsx(
              isHorizontal ? "flex items-center flex-1" : "flex items-start",
              index === steps.length - 1 && isHorizontal && "flex-none"
            )}
          >
            {/* Step Circle + Label */}
            <div className={clsx(
              "flex items-center gap-3",
              !isHorizontal && "mb-8"
            )}>
              <div
                className={clsx(
                  "flex items-center justify-center rounded-full text-xs font-bold transition-all duration-200",
                  "h-8 w-8 shrink-0",
                  isCompleted && "bg-primary-500 text-white",
                  isCurrent && "ring-2 ring-primary-500 bg-primary-500/20 text-primary-500",
                  isUpcoming && "bg-[var(--color-border)] text-[var(--color-text-tertiary)]"
                )}
                aria-current={isCurrent ? "step" : undefined}
              >
                {isCompleted ? (
                  <Check className="h-4 w-4" />
                ) : (
                  index + 1
                )}
              </div>
              <div className="min-w-0">
                <span className={clsx(
                  "text-sm font-medium whitespace-nowrap",
                  isCurrent ? "text-primary-500" : isCompleted ? "text-[var(--color-text)]" : "text-[var(--color-text-tertiary)]"
                )}>
                  {step.label}
                </span>
                {step.description && (
                  <p className="text-xs text-[var(--color-text-tertiary)] mt-0.5">
                    {step.description}
                  </p>
                )}
                <span className="sr-only">
                  Step {index + 1} of {steps.length}: {step.label} — {isCompleted ? "completed" : isCurrent ? "current" : "upcoming"}
                </span>
              </div>
            </div>

            {/* Connector Line */}
            {index < steps.length - 1 && (
              <div
                className={clsx(
                  "transition-colors duration-200",
                  isHorizontal
                    ? "h-0.5 flex-1 mx-3"
                    : "w-0.5 h-6 ml-4 mb-2",
                  isCompleted ? "bg-primary-500" : "bg-[var(--color-border)]"
                )}
                aria-hidden="true"
              />
            )}
          </div>
        );
      })}
    </nav>
  );
}
