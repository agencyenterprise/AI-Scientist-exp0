"use client";

import { Search, FlaskConical } from "lucide-react";

interface ResearchBoardHeaderProps {
  searchTerm: string;
  onSearchChange: (term: string) => void;
  statusFilter: string;
  onStatusFilterChange: (status: string) => void;
  totalCount: number;
  filteredCount: number;
}

export function ResearchBoardHeader({
  searchTerm,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  totalCount,
  filteredCount,
}: ResearchBoardHeaderProps) {
  const showingFiltered =
    (searchTerm.trim() || statusFilter !== "all") && filteredCount !== totalCount;

  return (
    <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-emerald-500/40 bg-emerald-500/15">
          <FlaskConical className="h-6 w-6 text-emerald-400" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold text-white sm:text-3xl">Research Runs</h1>
          <p className="text-sm text-slate-400">
            {showingFiltered
              ? `Showing ${filteredCount} of ${totalCount} runs`
              : `${totalCount} research run${totalCount !== 1 ? "s" : ""}`}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <select
          value={statusFilter}
          onChange={e => onStatusFilterChange(e.target.value)}
          className="rounded-xl border border-slate-700 bg-slate-900/50 px-3 py-2.5 text-sm text-white transition-colors focus:border-emerald-500/50 focus:outline-none focus:ring-1 focus:ring-emerald-500/50"
        >
          <option value="all">All Status</option>
          <option value="pending">Pending</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>

        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search runs..."
            value={searchTerm}
            onChange={e => onSearchChange(e.target.value)}
            className="w-full rounded-xl border border-slate-700 bg-slate-900/50 py-2.5 pl-10 pr-4 text-sm text-white placeholder-slate-500 transition-colors focus:border-emerald-500/50 focus:outline-none focus:ring-1 focus:ring-emerald-500/50 sm:w-72"
          />
        </div>
      </div>
    </div>
  );
}
