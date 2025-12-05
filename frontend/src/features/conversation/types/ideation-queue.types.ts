import type { ComponentType } from "react";
import type { Conversation } from "@/shared/lib/api-adapters";

/**
 * Status types for ideation queue items
 * Ordered by workflow progression for sorting
 */
export type IdeaStatus =
  | "no_idea" // No ideaTitle/ideaAbstract present
  | "pending_launch" // Has idea but no research run (MVP: default if has idea)
  | "in_research" // Active research run (future: from backend)
  | "completed" // Research completed (future: from backend)
  | "failed"; // Research failed (future: from backend)

/**
 * Filter options including "all" for showing everything
 */
export type StatusFilterOption = "all" | IdeaStatus;

/**
 * Configuration for status badge styling (OCP-compliant)
 */
export interface IdeaStatusConfig {
  label: string;
  className: string;
  icon: ComponentType<{ className?: string }>;
}

/**
 * Configuration for filter button styling (OCP-compliant)
 */
export interface StatusFilterConfig {
  label: string;
  activeClass: string;
}

/**
 * Sort options for ideation queue
 */
export type IdeationSortKey =
  | "newest"
  | "oldest"
  | "title_asc"
  | "title_desc"
  | "status";

/**
 * Props for IdeationQueueCard component (ISP-compliant: focused interface)
 */
export interface IdeationQueueCardProps {
  id: number;
  title: string;
  abstract: string | null;
  status: IdeaStatus;
  createdAt: string;
  updatedAt: string;
}

/**
 * Props for IdeationQueueFilters component
 */
export interface IdeationQueueFiltersProps {
  activeFilter: StatusFilterOption;
  onFilterChange: (filter: StatusFilterOption) => void;
}

/**
 * Props for IdeationQueueHeader component
 */
export interface IdeationQueueHeaderProps {
  searchTerm: string;
  onSearchChange: (term: string) => void;
  statusFilter: StatusFilterOption;
  onStatusFilterChange: (filter: StatusFilterOption) => void;
  totalCount: number;
  filteredCount: number;
}

/**
 * Props for IdeationQueueList component
 */
export interface IdeationQueueListProps {
  conversations: Conversation[];
  emptyMessage?: string;
}

/**
 * Props for IdeationQueueEmpty component
 */
export interface IdeationQueueEmptyProps {
  hasFilters?: boolean;
}

/**
 * Extended return type for useConversationsFilter hook
 */
export interface UseConversationsFilterReturn {
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  statusFilter: StatusFilterOption;
  setStatusFilter: (filter: StatusFilterOption) => void;
  filteredConversations: Conversation[];
}
