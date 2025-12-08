"use client";

import { memo, useState } from "react";
import { useRouter } from "next/navigation";
import { Clock, ChevronDown, ChevronUp } from "lucide-react";
import { formatRelativeTime } from "@/shared/lib/date-utils";
import { cn } from "@/shared/lib/utils";
import type { IdeationQueueCardProps } from "../types/ideation-queue.types";
import { IdeationQueueRunsList } from "./IdeationQueueRunsList";

/**
 * Card component for displaying a single idea in the Ideation Queue
 * Supports expand/collapse to show research runs
 * Memoized for performance in list rendering
 */
function IdeationQueueCardComponent({
  id,
  title,
  abstract,
  createdAt,
  updatedAt,
}: IdeationQueueCardProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const router = useRouter();

  const handleCardClick = () => {
    router.push(`/conversations/${id}`);
  };

  const handleExpandToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsExpanded((prev) => !prev);
  };

  return (
    <article
      onClick={handleCardClick}
      className={cn(
        "group cursor-pointer rounded-xl border border-slate-800 bg-slate-900/50 p-4",
        "transition-all hover:border-slate-700 hover:bg-slate-900/80"
      )}
    >
      {/* Header: Title */}
      <div className="mb-3 flex flex-col gap-2">
        <h3 className="line-clamp-2 text-sm font-semibold text-slate-100">
          {title}
        </h3>
      </div>

      {/* Body: Abstract preview */}
      {abstract && (
        <p className="mb-3 line-clamp-3 text-xs leading-relaxed text-slate-400">
          {abstract}
        </p>
      )}

      {/* Footer: Dates + Expand toggle */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3 text-[10px] uppercase tracking-wide text-slate-500">
          <span className="inline-flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Created {formatRelativeTime(createdAt)}
          </span>
          <span>Updated {formatRelativeTime(updatedAt)}</span>
        </div>

        <button
          onClick={handleExpandToggle}
          type="button"
          aria-label={isExpanded ? "Hide research runs" : "Show research runs"}
          aria-expanded={isExpanded}
          className={cn(
            "inline-flex items-center gap-1 rounded px-2 py-1",
            "text-[10px] uppercase tracking-wide text-slate-400",
            "transition-colors hover:bg-slate-800 hover:text-slate-300"
          )}
        >
          {isExpanded ? "Hide Runs" : "Show Runs"}
          {isExpanded ? (
            <ChevronUp className="h-3 w-3" />
          ) : (
            <ChevronDown className="h-3 w-3" />
          )}
        </button>
      </div>

      {/* Expandable Runs Section */}
      {isExpanded && <IdeationQueueRunsList conversationId={id} />}
    </article>
  );
}

// Memoize to prevent re-renders when parent filters change
export const IdeationQueueCard = memo(IdeationQueueCardComponent);
