"use client";

import { useDashboard } from "@/features/dashboard/contexts/DashboardContext";
import { useConversationsFilter } from "@/features/conversation/hooks/useConversationsFilter";
import { IdeationQueueHeader } from "@/features/conversation/components/IdeationQueueHeader";
import { IdeationQueueList } from "@/features/conversation/components/IdeationQueueList";

export default function ConversationsPage() {
  const { conversations } = useDashboard();
  const {
    searchTerm,
    setSearchTerm,
    statusFilter,
    setStatusFilter,
    filteredConversations,
  } = useConversationsFilter(conversations);

  const hasActiveFilters = searchTerm.trim() !== "" || statusFilter !== "all";

  return (
    <div className="flex flex-col gap-6 p-6">
      <IdeationQueueHeader
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        totalCount={conversations.length}
        filteredCount={filteredConversations.length}
      />

      <IdeationQueueList
        conversations={filteredConversations}
        emptyMessage={hasActiveFilters ? "No ideas match your filters" : undefined}
      />
    </div>
  );
}
