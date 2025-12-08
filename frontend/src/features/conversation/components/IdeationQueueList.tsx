"use client";

import type { IdeationQueueListProps } from "@/features/conversation";
import { IdeationQueueCard } from "./IdeationQueueCard";
import { IdeationQueueEmpty } from "./IdeationQueueEmpty";
import { deriveIdeaStatus } from "@/features/conversation";

/**
 * Card grid container for the Ideation Queue
 * Displays conversations as responsive cards with status badges
 */
export function IdeationQueueList({ conversations, emptyMessage }: IdeationQueueListProps) {
  if (conversations.length === 0) {
    return <IdeationQueueEmpty hasFilters={Boolean(emptyMessage)} />;
  }

  return (
    <div className="grid grid-cols-1 gap-4">
      {conversations.map(conversation => (
        <IdeationQueueCard
          key={conversation.id}
          id={conversation.id}
          title={conversation.ideaTitle || conversation.title || "Untitled Idea"}
          abstract={conversation.ideaAbstract ?? null}
          status={deriveIdeaStatus(conversation)}
          createdAt={conversation.createdAt}
          updatedAt={conversation.updatedAt}
        />
      ))}
    </div>
  );
}
