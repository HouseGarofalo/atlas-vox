import { useState, useRef, useCallback, useEffect, useId, type ReactNode, type MouseEvent, type TouchEvent } from "react";
import { ChevronDown, ChevronRight, Maximize2, Minimize2, GripHorizontal } from "lucide-react";
import { clsx } from "clsx";

interface CollapsiblePanelProps {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
  icon?: ReactNode;
  badge?: ReactNode;
  actions?: ReactNode;
  className?: string;
  noPadding?: boolean;
  /** Enable drag-to-resize on the bottom edge */
  resizable?: boolean;
  /** Default height when resizable (px). Omit for auto. */
  defaultHeight?: number;
  /** Min height when resizing (px) */
  minHeight?: number;
  /** Max height when resizing (px) */
  maxHeight?: number;
  /** Unique key for persisting panel state */
  id?: string;
}

export function CollapsiblePanel({
  title,
  children,
  defaultOpen = true,
  icon,
  badge,
  actions,
  className,
  noPadding,
  resizable = false,
  defaultHeight,
  minHeight = 100,
  maxHeight = 800,
  id,
}: CollapsiblePanelProps) {
  const panelId = useId();
  const [open, setOpen] = useState(() => {
    if (id) {
      const saved = sessionStorage.getItem(`panel-${id}`);
      if (saved !== null) return saved === "true";
    }
    return defaultOpen;
  });
  const [expanded, setExpanded] = useState(false);
  const [height, setHeight] = useState<number | undefined>(defaultHeight);
  const [isResizing, setIsResizing] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const startY = useRef(0);
  const startHeight = useRef(0);

  // Persist open state
  useEffect(() => {
    if (id) {
      sessionStorage.setItem(`panel-${id}`, String(open));
    }
  }, [id, open]);

  const toggleOpen = useCallback(() => {
    setOpen((prev) => !prev);
  }, []);

  const toggleExpanded = useCallback((e: MouseEvent) => {
    e.stopPropagation();
    setExpanded((prev) => !prev);
  }, []);

  // --- Resize handlers ---
  const onResizeStart = useCallback((clientY: number) => {
    if (!contentRef.current) return;
    setIsResizing(true);
    startY.current = clientY;
    startHeight.current = contentRef.current.offsetHeight;
  }, []);

  const onResizeMove = useCallback(
    (clientY: number) => {
      if (!isResizing) return;
      const delta = clientY - startY.current;
      const newHeight = Math.max(minHeight, Math.min(maxHeight, startHeight.current + delta));
      setHeight(newHeight);
    },
    [isResizing, minHeight, maxHeight]
  );

  const onResizeEnd = useCallback(() => {
    setIsResizing(false);
  }, []);

  // Mouse resize
  const handleMouseDown = useCallback(
    (e: MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      onResizeStart(e.clientY);
    },
    [onResizeStart]
  );

  useEffect(() => {
    if (!isResizing) return;
    const onMove = (e: globalThis.MouseEvent) => onResizeMove(e.clientY);
    const onUp = () => onResizeEnd();
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [isResizing, onResizeMove, onResizeEnd]);

  // Touch resize
  const handleTouchStart = useCallback(
    (e: TouchEvent) => {
      e.stopPropagation();
      onResizeStart(e.touches[0].clientY);
    },
    [onResizeStart]
  );

  useEffect(() => {
    if (!isResizing) return;
    const onMove = (e: globalThis.TouchEvent) => {
      e.preventDefault();
      onResizeMove(e.touches[0].clientY);
    };
    const onEnd = () => onResizeEnd();
    window.addEventListener("touchmove", onMove, { passive: false });
    window.addEventListener("touchend", onEnd);
    return () => {
      window.removeEventListener("touchmove", onMove);
      window.removeEventListener("touchend", onEnd);
    };
  }, [isResizing, onResizeMove, onResizeEnd]);

  return (
    <div
      className={clsx(
        "rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg)] transition-all",
        expanded && "fixed inset-3 sm:inset-4 z-50 overflow-auto shadow-2xl flex flex-col",
        isResizing && "select-none",
        className
      )}
    >
      {/* Backdrop when expanded */}
      {expanded && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
          onClick={() => setExpanded(false)}
        />
      )}

      {/* Header */}
      <div
        className={clsx(
          "relative z-50 flex items-center gap-2 px-3 sm:px-4 py-2.5 sm:py-3 cursor-pointer select-none",
          "hover:bg-[var(--color-hover)] transition-colors rounded-t-[var(--radius)]",
          open && !noPadding && "border-b border-[var(--color-border)]",
          !open && "rounded-b-[var(--radius)]"
        )}
        onClick={toggleOpen}
        role="button"
        aria-expanded={open}
        aria-controls={panelId}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            toggleOpen();
          }
        }}
      >
        <span className="text-[var(--color-text-secondary)] transition-transform duration-150">
          {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </span>
        {icon && <span className="flex-shrink-0">{icon}</span>}
        <h3 className="flex-1 text-sm font-semibold truncate">{title}</h3>
        {badge && <span className="flex-shrink-0">{badge}</span>}
        {actions && (
          <div className="flex items-center gap-1 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
            {actions}
          </div>
        )}
        <button
          onClick={toggleExpanded}
          className="rounded p-1 text-[var(--color-text-secondary)] hover:bg-gray-100 dark:hover:bg-gray-800 flex-shrink-0 transition-colors"
          aria-label={expanded ? "Minimize panel" : "Maximize panel"}
          title={expanded ? "Minimize" : "Maximize"}
        >
          {expanded ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
        </button>
      </div>

      {/* Content */}
      {open && (
        <div
          id={panelId}
          ref={contentRef}
          className={clsx(
            !noPadding && "p-3 sm:p-4",
            expanded && "flex-1 overflow-auto",
            resizable && height !== undefined && !expanded && "overflow-auto"
          )}
          style={
            resizable && height !== undefined && !expanded
              ? { height, maxHeight }
              : undefined
          }
        >
          {children}
        </div>
      )}

      {/* Resize handle */}
      {open && resizable && !expanded && (
        <div
          className="flex items-center justify-center h-4 cursor-ns-resize border-t border-[var(--color-border)] hover:bg-[var(--color-hover)] transition-colors rounded-b-[var(--radius)] group"
          onMouseDown={handleMouseDown}
          onTouchStart={handleTouchStart}
          role="separator"
          aria-orientation="horizontal"
          aria-label="Resize panel"
          tabIndex={0}
          onKeyDown={(e) => {
            if (!contentRef.current) return;
            const step = 20;
            const current = contentRef.current.offsetHeight;
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setHeight(Math.min(maxHeight, current + step));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setHeight(Math.max(minHeight, current - step));
            }
          }}
        >
          <GripHorizontal className="h-3 w-3 text-[var(--color-text-tertiary)] group-hover:text-[var(--color-text-secondary)] transition-colors" />
        </div>
      )}
    </div>
  );
}
