"use client";

import { createContext, useContext } from "react";
import type { ResearchRun } from "@/shared/lib/api-adapters";

export type SortKey = "updated" | "created" | "title" | "status";
export type SortDir = "asc" | "desc";

interface ResearchContextType {
  researchRuns: ResearchRun[];
  refreshResearchRuns: () => Promise<void>;
  sortKey: SortKey;
  setSortKey: (key: SortKey) => void;
  sortDir: SortDir;
  setSortDir: (dir: SortDir) => void;
}

export const ResearchContext = createContext<ResearchContextType | null>(null);

export function useResearch() {
  const context = useContext(ResearchContext);
  if (!context) {
    throw new Error("useResearch must be used within ResearchLayout");
  }
  return context;
}
