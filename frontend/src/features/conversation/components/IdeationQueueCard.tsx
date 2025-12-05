"use client";

import { memo } from "react";
import Link from "next/link";
import { Clock } from "lucide-react";
import { formatRelativeTime } from "@/shared/lib/date-utils";
import type { IdeationQueueCardProps } from "../types/ideation-queue.types";
import { getIdeaStatusBadge } from "../utils/ideation-queue-utils";

/**
 * Card component for displaying a single idea in the Ideation Queue
 * Memoized for performance in list rendering
 */
function IdeationQueueCardComponent({
  id,
  title,
  abstract,
  status,
  createdAt,
  updatedAt,
}: IdeationQueueCardProps) {
  return (
    <Link href={`/conversations/${id}`}>
      <article className="group rounded-xl border border-slate-800 bg-slate-900/50 p-4 transition-all hover:border-slate-700 hover:bg-slate-900/80">
        {/* Header: Status badge + Title */}
        <div className="mb-3 flex flex-col gap-2">
          <div className="flex-shrink-0">{getIdeaStatusBadge(status)}</div>
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

        {/* Footer: Dates */}
        <div className="flex flex-wrap items-center gap-3 text-[10px] uppercase tracking-wide text-slate-500">
          <span className="inline-flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Created {formatRelativeTime(createdAt)}
          </span>
          <span>Updated {formatRelativeTime(updatedAt)}</span>
        </div>
      </article>
    </Link>
  );
}

// Memoize to prevent re-renders when parent filters change
export const IdeationQueueCard = memo(IdeationQueueCardComponent);
