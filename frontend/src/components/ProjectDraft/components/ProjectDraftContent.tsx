import React, { ReactElement } from "react";
import ReactMarkdown from "react-markdown";
import type { ProjectDraft, ProjectDraftVersion } from "@/types";
import { isProjectDraftGenerating } from "../utils/versionUtils";

interface ProjectDraftContentProps {
  projectDraft: ProjectDraft;
  isEditing: boolean;
  editDescription: string;
  setEditDescription: (description: string) => void;
  showDiffs: boolean;
  comparisonVersion: ProjectDraftVersion | null;
  nextVersion: ProjectDraftVersion | null;
  descriptionDiffContent: ReactElement[] | null;
  onKeyDown: (event: React.KeyboardEvent, action: () => void) => void;
  onSave: () => Promise<void>;
  onCancelEdit: () => void;
}

export function ProjectDraftContent({
  projectDraft,
  isEditing,
  editDescription,
  setEditDescription,
  showDiffs,
  comparisonVersion,
  nextVersion,
  descriptionDiffContent,
  onKeyDown,
  onSave,
  onCancelEdit,
}: ProjectDraftContentProps): React.JSX.Element {
  const isGenerating = isProjectDraftGenerating(projectDraft);

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Description Section */}
      <div className="flex items-center justify-between mb-2">
        <label className="text-sm font-medium text-gray-700">Description</label>
      </div>

      {isEditing ? (
        <div className="flex-1 flex flex-col min-h-0">
          <textarea
            value={editDescription}
            onChange={e => setEditDescription(e.target.value)}
            onKeyDown={e => onKeyDown(e, onSave)}
            className="flex-1 min-h-[45vh] sm:min-h-[20rem] px-3 py-2 text-sm border border-[var(--border)] rounded-md resize-none overflow-auto focus:outline-none focus:ring-2 focus:ring-[var(--ring)] focus:border-transparent bg-[var(--surface)] text-[var(--foreground)]"
            placeholder="Enter project description..."
          />
          <div className="flex justify-end space-x-2 mt-2">
            <button
              onClick={onCancelEdit}
              className="px-3 py-1 text-xs text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded border border-gray-200 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={onSave}
              className="px-3 py-1 text-xs text-[var(--primary-foreground)] bg-[var(--primary)] hover:bg-[var(--primary-hover)] rounded transition-colors"
            >
              Save
            </button>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          <div className="flex-1 overflow-y-auto px-1">
            {isGenerating ? (
              <div className="space-y-2">
                <div className="animate-pulse">
                  <div className="h-3 bg-[var(--primary-300)] rounded w-full"></div>
                  <div className="h-3 bg-[var(--primary-300)] rounded w-5/6 mt-2"></div>
                  <div className="h-3 bg-[var(--primary-300)] rounded w-4/5"></div>
                  <div className="h-3 bg-[var(--primary-300)] rounded w-3/4"></div>
                </div>
              </div>
            ) : showDiffs && comparisonVersion && nextVersion && descriptionDiffContent ? (
              <div className="whitespace-pre-wrap break-words text-sm leading-relaxed px-1">
                {descriptionDiffContent}
              </div>
            ) : (
              <ReactMarkdown
                className="text-gray-900"
                components={{
                  h1: ({ children }) => (
                    <h1 className="text-lg font-bold mb-2 mt-3 first:mt-0">{children}</h1>
                  ),
                  h2: ({ children }) => (
                    <h2 className="text-base font-semibold mb-1 mt-2 first:mt-0">{children}</h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-base font-medium mb-1 mt-2 first:mt-0">{children}</h3>
                  ),
                  p: ({ children }) => <p className="mb-1 last:mb-0">{children}</p>,
                  ul: ({ children }) => (
                    <ul className="list-disc ml-4 mb-1 space-y-0.5">{children}</ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="list-decimal ml-4 mb-1 space-y-0.5">{children}</ol>
                  ),
                  li: ({ children }) => <li>{children}</li>,
                  code: ({ children }) => (
                    <code className="bg-gray-200 px-1 py-0.5 rounded text-xs font-mono">
                      {children}
                    </code>
                  ),
                  pre: ({ children }) => (
                    <pre className="bg-gray-200 p-2 rounded text-xs font-mono overflow-x-auto mb-1">
                      {children}
                    </pre>
                  ),
                  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                  em: ({ children }) => <em className="italic">{children}</em>,
                  a: ({ href, children }) => (
                    <a
                      href={href}
                      className="text-[var(--primary)] hover:underline"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {children}
                    </a>
                  ),
                }}
              >
                {projectDraft.active_version?.description || ""}
              </ReactMarkdown>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
