"use client";

import { useResearch } from "@/features/research/contexts/ResearchContext";
import { useResearchFilter } from "@/features/research/hooks/useResearchFilter";
import { ResearchBoardHeader } from "@/features/research/components/ResearchBoardHeader";
import { ResearchBoardTable } from "@/features/research/components/ResearchBoardTable";

export default function ResearchPage() {
  const { researchRuns } = useResearch();
  const { searchTerm, setSearchTerm, statusFilter, setStatusFilter, filteredResearchRuns } =
    useResearchFilter(researchRuns);

  return (
    <div className="flex flex-col gap-6 p-6">
      <ResearchBoardHeader
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        totalCount={researchRuns.length}
        filteredCount={filteredResearchRuns.length}
      />

      <ResearchBoardTable researchRuns={filteredResearchRuns} />
    </div>
  );
}
