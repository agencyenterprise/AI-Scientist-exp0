"use client";

import { Terminal } from "lucide-react";
import { format } from "date-fns";
import type { LogEntry } from "@/types/research";
import { getLogLevelColor } from "../../utils/research-utils";

interface ResearchLogsListProps {
  logs: LogEntry[];
  maxVisible?: number;
}

/**
 * Logs section for research run detail page
 */
export function ResearchLogsList({ logs, maxVisible = 100 }: ResearchLogsListProps) {
  if (logs.length === 0) {
    return null;
  }

  const visibleLogs = logs.slice(0, maxVisible);
  const hiddenCount = logs.length - maxVisible;

  return (
    <div className="flex h-full flex-col rounded-xl border border-slate-800 bg-slate-900/50 p-6">
      <div className="mb-4 flex items-center gap-2">
        <Terminal className="h-5 w-5 text-slate-400" />
        <h2 className="text-lg font-semibold text-white">Logs</h2>
        <span className="text-sm text-slate-400">({logs.length})</span>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto rounded-lg bg-slate-950 p-4 font-mono text-sm">
        {visibleLogs.map(log => (
          <div key={log.id} className="flex gap-3 py-1">
            <span className="flex-shrink-0 text-slate-600">
              {format(new Date(log.created_at), "HH:mm:ss")}
            </span>
            <span
              className={`flex-shrink-0 uppercase ${getLogLevelColor(log.level)}`}
              style={{ width: "50px" }}
            >
              {log.level}
            </span>
            <span className="text-slate-300">{log.message}</span>
          </div>
        ))}
        {hiddenCount > 0 && (
          <p className="mt-2 text-slate-500">... and {hiddenCount} more entries</p>
        )}
      </div>
    </div>
  );
}
