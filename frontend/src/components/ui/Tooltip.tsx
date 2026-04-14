import { cloneElement, useId, type ReactElement } from "react";
import { clsx } from "clsx";

interface TooltipProps {
  content: string;
  side?: "top" | "bottom" | "left" | "right";
  children: ReactElement;
  className?: string;
}

const sideClasses: Record<string, string> = {
  top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
  bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
  left: "right-full top-1/2 -translate-y-1/2 mr-2",
  right: "left-full top-1/2 -translate-y-1/2 ml-2",
};

const arrowClasses: Record<string, string> = {
  top: "top-full left-1/2 -translate-x-1/2 border-t-[hsl(var(--studio-obsidian))] border-x-transparent border-b-transparent",
  bottom: "bottom-full left-1/2 -translate-x-1/2 border-b-[hsl(var(--studio-obsidian))] border-x-transparent border-t-transparent",
  left: "left-full top-1/2 -translate-y-1/2 border-l-[hsl(var(--studio-obsidian))] border-y-transparent border-r-transparent",
  right: "right-full top-1/2 -translate-y-1/2 border-r-[hsl(var(--studio-obsidian))] border-y-transparent border-l-transparent",
};

export function Tooltip({
  content,
  side = "top",
  children,
  className,
}: TooltipProps) {
  const tooltipId = useId();

  return (
    <span className={clsx("relative inline-flex group", className)}>
      {cloneElement(children, {
        "aria-describedby": tooltipId,
      })}
      <span
        id={tooltipId}
        role="tooltip"
        className={clsx(
          "absolute z-50 pointer-events-none whitespace-nowrap",
          "bg-[hsl(var(--studio-obsidian))] text-white text-xs font-medium px-2.5 py-1.5 rounded-md shadow-lg",
          "opacity-0 group-hover:opacity-100 group-focus-within:opacity-100",
          "transition-opacity duration-150",
          sideClasses[side]
        )}
      >
        {content}
        <span
          aria-hidden="true"
          className={clsx(
            "absolute w-0 h-0 border-4",
            arrowClasses[side]
          )}
        />
      </span>
    </span>
  );
}
