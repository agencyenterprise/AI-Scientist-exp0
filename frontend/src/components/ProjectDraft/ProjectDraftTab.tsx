"use client";

import { useState } from "react";

import { ProjectDraft } from "./ProjectDraft";
import { ProjectDraftConversation } from "./ProjectDraftConversation";
import { PromptEditModal } from "./PromptEditModal";
import { useProjectDraftState } from "./hooks/useProjectDraftState";
import { PromptTypes } from "@/lib/prompt-types";
import type { ConversationDetail, ProjectDraft as ProjectDraftType } from "@/types";

interface ProjectDraftTabProps {
  conversation: ConversationDetail;
  onConversationLocked?: () => void;
  mobileView: "chat" | "draft";
  onMobileViewChange: (view: "chat" | "draft") => void;
}

export function ProjectDraftTab({
  conversation,
  onConversationLocked,
  mobileView,
  onMobileViewChange,
}: ProjectDraftTabProps) {
  const [isPromptModalOpen, setIsPromptModalOpen] = useState(false);
  const [updatedProjectDraft, setUpdatedProjectDraft] = useState<ProjectDraftType | null>(null);

  // Get current project draft state for read-only detection
  const projectDraftState = useProjectDraftState({ conversation });

  const handleProjectDraftUpdate = (updatedDraft: ProjectDraftType): void => {
    // Pass the updated project draft to the ProjectDraft component
    setUpdatedProjectDraft(updatedDraft);
    // Clear the update after a brief moment to allow for future updates
    setTimeout(() => setUpdatedProjectDraft(null), 100);
  };

  const handleOpenPromptModal = (): void => {
    setIsPromptModalOpen(true);
  };

  const handleClosePromptModal = (): void => {
    setIsPromptModalOpen(false);
  };

  return (
    <div className="h-full min-h-0 flex flex-col">
      {/* Mobile toggle inside Project tab header area */}
      <div className="md:hidden bg-[var(--surface)] px-3">
        <div
          role="tablist"
          aria-label="Project view"
          className="flex items-center justify-end gap-4 -mb-px"
        >
          <button
            type="button"
            role="tab"
            aria-selected={mobileView === "chat"}
            aria-controls="project-tab-chat"
            onClick={() => onMobileViewChange("chat")}
            className={`py-2 text-sm font-medium border-b-2 transition-colors ${
              mobileView === "chat"
                ? "text-[var(--primary-700)] border-[var(--primary)]"
                : "text-[var(--foreground)]/70 hover:text-[var(--foreground)] border-transparent"
            }`}
          >
            Chat
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mobileView === "draft"}
            aria-controls="project-tab-draft"
            onClick={() => onMobileViewChange("draft")}
            className={`py-2 text-sm font-medium border-b-2 transition-colors ${
              mobileView === "draft"
                ? "text-[var(--primary-700)] border-[var(--primary)]"
                : "text-[var(--foreground)]/70 hover:text-[var(--foreground)] border-transparent"
            }`}
          >
            Project Draft
          </button>
        </div>
      </div>

      {/* Columns container */}
      <div className="flex-1 min-h-0 flex flex-col md:flex-row">
        {/* Left Panel - Chat */}
        <div
          className={`w-full md:w-1/2 h-full overflow-hidden border-t border-[var(--border)] md:border-t-0 ${
            mobileView === "chat" ? "block" : "hidden"
          } md:block`}
        >
          <ProjectDraftConversation
            conversationId={conversation.id}
            isLocked={conversation.is_locked}
            currentProjectDraft={projectDraftState.projectDraft}
            project={projectDraftState.project}
            onProjectDraftUpdate={handleProjectDraftUpdate}
            onOpenPromptModal={handleOpenPromptModal}
            onConversationLocked={onConversationLocked}
            conversationCapabilities={{
              hasImages: Boolean(conversation.has_images ?? false),
              hasPdfs: Boolean(conversation.has_pdfs ?? false),
            }}
            isVisible={mobileView === "chat"}
          />
        </div>

        {/* Right Panel - Project */}
        <div
          className={`w-full md:w-1/2 md:border-l flex flex-col overflow-hidden border-t border-[var(--border)] md:border-t-0 ${
            mobileView === "draft" ? "block" : "hidden"
          } md:block`}
        >
          <ProjectDraft
            conversation={conversation}
            externalUpdate={updatedProjectDraft}
            onConversationLocked={onConversationLocked}
          />
        </div>
      </div>

      {/* Single shared banner spanning below both columns */}
      {conversation.is_locked && projectDraftState.project && (
        <div className="px-3 sm:px-6 py-3 flex-shrink-0 border-t border-[var(--border)] bg-[var(--surface)]">
          <div className="w-full rounded-lg border border-green-200 bg-green-50 p-4 flex flex-col sm:flex-row items-center justify-center gap-3 text-center">
            <div className="flex items-center gap-3 justify-center">
              <svg
                className="w-6 h-6 text-green-600 flex-shrink-0 mt-0.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <div className="text-center">
                <div className="text-sm font-semibold text-green-800">
                  Project created:{" "}
                  <a
                    href={projectDraftState.project.linear_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-semibold inline-flex items-center hover:underline"
                  >
                    {projectDraftState.project.title}
                    <svg
                      className="w-3 h-3 ml-1"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                      />
                    </svg>
                  </a>
                </div>
                <div className="text-xs text-green-900/80 mt-0.5">
                  This conversation is locked. View the Linear project for ongoing updates.
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Prompt Edit Modal */}
      <PromptEditModal
        isOpen={isPromptModalOpen}
        onClose={handleClosePromptModal}
        promptType={PromptTypes.PROJECT_DRAFT_CHAT}
      />
    </div>
  );
}
