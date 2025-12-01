"use client";

import { useResearch } from "@/features/research/contexts/ResearchContext";
import { useResearchFilter } from "@/features/research/hooks/useResearchFilter";
import { ResearchBoardHeader } from "@/features/research/components/ResearchBoardHeader";
import { ResearchBoardTable } from "@/features/research/components/ResearchBoardTable";
import { useAuthContext } from "@/shared/contexts/AuthContext";

export default function ResearchPage() {
  const { user } = useAuthContext();
  const { researchRuns } = useResearch();
  const {
    searchTerm,
    setSearchTerm,
    statusFilter,
    setStatusFilter,
    onlyMine,
    setOnlyMine,
    selectedUser,
    setSelectedUser,
    uniqueUsers,
    filteredResearchRuns,
  } = useResearchFilter(researchRuns, { currentUserName: user?.name });

  return (
    <div className="flex flex-col gap-6 p-6">
      <ResearchBoardHeader
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        onlyMine={onlyMine}
        onOnlyMineChange={setOnlyMine}
        selectedUser={selectedUser}
        onSelectedUserChange={setSelectedUser}
        uniqueUsers={uniqueUsers}
        totalCount={researchRuns.length}
        filteredCount={filteredResearchRuns.length}
      />

      <ResearchBoardTable researchRuns={filteredResearchRuns} />
    </div>
  );
}
