"use client";

import { useMemo, useState, useCallback } from "react";
import type { ResearchRun } from "@/shared/lib/api-adapters";

interface UseResearchFilterReturn {
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  statusFilter: string;
  setStatusFilter: (status: string) => void;
  filteredResearchRuns: ResearchRun[];
}

export function useResearchFilter(researchRuns: ResearchRun[]): UseResearchFilterReturn {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const handleSetSearchTerm = useCallback((term: string) => {
    setSearchTerm(term);
  }, []);

  const handleSetStatusFilter = useCallback((status: string) => {
    setStatusFilter(status);
  }, []);

  const filteredResearchRuns = useMemo(() => {
    let filtered = researchRuns;

    // Filter by status
    if (statusFilter !== "all") {
      filtered = filtered.filter(run => run.status === statusFilter);
    }

    // Filter by search term
    if (searchTerm.trim()) {
      const lowerSearch = searchTerm.toLowerCase();
      filtered = filtered.filter(run => {
        const title = run.ideaTitle?.toLowerCase() || "";
        const hypothesis = run.ideaHypothesis?.toLowerCase() || "";
        const runId = run.runId?.toLowerCase() || "";
        const createdBy = run.createdByName?.toLowerCase() || "";
        const stage = run.currentStage?.toLowerCase() || "";

        return (
          title.includes(lowerSearch) ||
          hypothesis.includes(lowerSearch) ||
          runId.includes(lowerSearch) ||
          createdBy.includes(lowerSearch) ||
          stage.includes(lowerSearch)
        );
      });
    }

    return filtered;
  }, [researchRuns, searchTerm, statusFilter]);

  return {
    searchTerm,
    setSearchTerm: handleSetSearchTerm,
    statusFilter,
    setStatusFilter: handleSetStatusFilter,
    filteredResearchRuns,
  };
}
