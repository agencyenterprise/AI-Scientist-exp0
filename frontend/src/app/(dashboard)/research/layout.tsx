"use client";

import { ResearchContext, SortDir, SortKey } from "@/features/research/contexts/ResearchContext";
import { useCallback, useEffect, useState } from "react";

import { ProtectedRoute } from "@/shared/components/ProtectedRoute";
import { apiFetch } from "@/shared/lib/api-client";
import type { ResearchRun } from "@/shared/lib/api-adapters";
import { convertApiResearchRunList } from "@/shared/lib/api-adapters";
import type { ResearchRunListResponseApi } from "@/types/research";

interface ResearchLayoutProps {
  children: React.ReactNode;
}

export default function ResearchLayout({ children }: ResearchLayoutProps) {
  const [researchRuns, setResearchRuns] = useState<ResearchRun[]>([]);
  const [sortKey, setSortKey] = useState<SortKey>("created");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const loadResearchRuns = useCallback(async (): Promise<void> => {
    try {
      const apiResponse = await apiFetch<ResearchRunListResponseApi>(
        "/research-runs?limit=500&offset=0"
      );
      const data = convertApiResearchRunList(apiResponse);
      setResearchRuns(data.items);
    } catch {
      // silence error in prod/CI
    }
  }, []);

  useEffect(() => {
    loadResearchRuns();
  }, [loadResearchRuns]);

  const researchContextValue = {
    researchRuns,
    refreshResearchRuns: loadResearchRuns,
    sortKey,
    setSortKey,
    sortDir,
    setSortDir,
  };

  return (
    <ProtectedRoute>
      <ResearchContext.Provider value={researchContextValue}>{children}</ResearchContext.Provider>
    </ProtectedRoute>
  );
}
