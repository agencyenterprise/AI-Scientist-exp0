"use client";

import { useDashboard } from "@/features/dashboard/contexts/DashboardContext";
import { useConversationsFilter } from "@/features/conversation/hooks/useConversationsFilter";
import { IdeationQueueHeader } from "@/features/conversation/components/IdeationQueueHeader";
import { IdeationQueueList } from "@/features/conversation/components/IdeationQueueList";
import { IdeationQueueSkeleton } from "@/features/conversation/components/IdeationQueueSkeleton";

export default function ConversationsPage() {
  const { conversations, isLoading } = useDashboard();
  const { searchTerm, setSearchTerm, filteredConversations } =
    useConversationsFilter(conversations);

  const hasActiveSearch = searchTerm.trim() !== "";

  return (
    <div className="flex flex-col gap-6 p-6">
      <IdeationQueueHeader
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        totalCount={conversations.length}
        filteredCount={filteredConversations.length}
      />

      {isLoading ? (
        <IdeationQueueSkeleton />
      ) : (
        <IdeationQueueList
          conversations={filteredConversations}
          emptyMessage={hasActiveSearch ? "No ideas match your search" : undefined}
        />
      )}
    </div>
  );
}
