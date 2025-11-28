import React, { ReactElement } from "react";
import type { Idea, IdeaVersion } from "@/types";
import { isIdeaGenerating } from "../utils/versionUtils";
import { FileText, Pencil, Undo2 } from "lucide-react";
import { VersionNavigationPanel } from "./VersionNavigationPanel";

interface ProjectDraftHeaderProps {
  projectDraft: Idea;
  showDiffs: boolean;
  setShowDiffs: (show: boolean) => void;
  comparisonVersion: IdeaVersion | null;
  nextVersion: IdeaVersion | null;
  titleDiffContent: ReactElement[] | null;
  onEditTitle?: () => void;
  // Version navigation props
  allVersions: IdeaVersion[];
  canNavigatePrevious: boolean;
  canNavigateNext: boolean;
  newVersionAnimation: boolean;
  onPreviousVersion: () => void;
  onNextVersion: () => void;
  onRevertChanges: () => Promise<void>;
}

export function ProjectDraftHeader({
  projectDraft,
  showDiffs,
  setShowDiffs,
  comparisonVersion,
  nextVersion,
  titleDiffContent,
  onEditTitle,
  allVersions,
  canNavigatePrevious,
  canNavigateNext,
  newVersionAnimation,
  onPreviousVersion,
  onNextVersion,
  onRevertChanges,
}: ProjectDraftHeaderProps): React.JSX.Element {
  const isGenerating = isIdeaGenerating(projectDraft);
  const hasMultipleVersions = allVersions.length > 1;
  const canRevert = comparisonVersion && nextVersion && !isGenerating;

  return (
    <div className="flex-shrink-0 py-4">
      <div className="flex items-center justify-between mb-2">
        <label className="text-sm font-medium text-muted-foreground">Title</label>
        <div className="flex items-center gap-2">
          {/* Version navigation (always visible when multiple versions exist) */}
          {!isGenerating && hasMultipleVersions && comparisonVersion && (
            <VersionNavigationPanel
              comparisonVersion={comparisonVersion}
              totalVersions={allVersions.length}
              canNavigatePrevious={canNavigatePrevious}
              canNavigateNext={canNavigateNext}
              onPreviousVersion={onPreviousVersion}
              onNextVersion={onNextVersion}
              newVersionAnimation={newVersionAnimation}
            />
          )}

          {/* Revert button (visible when can compare versions) */}
          {canRevert && (
            <button
              onClick={onRevertChanges}
              className="p-1.5 text-red-400/70 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
              title="Revert to this version"
              aria-label="Revert changes"
            >
              <Undo2 className="w-3.5 h-3.5" />
            </button>
          )}

          {/* Show diffs toggle (icon-only) */}
          {!isGenerating && comparisonVersion && nextVersion && (
            <button
              onClick={() => setShowDiffs(!showDiffs)}
              className={`p-1.5 rounded transition-colors ${
                showDiffs
                  ? "text-primary bg-primary/10"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
              title={showDiffs ? "Hide changes" : "Show changes"}
              aria-label={showDiffs ? "Hide changes" : "Show changes"}
            >
              <FileText className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex-1">
          <h3
            className={`text-base font-semibold ${
              isGenerating ? "text-primary" : "text-foreground"
            }`}
          >
            {showDiffs && comparisonVersion && nextVersion && titleDiffContent
              ? titleDiffContent
              : projectDraft.active_version?.title || ""}
          </h3>
        </div>
        {/* Edit title button */}
        {onEditTitle && !isGenerating && (
          <button
            onClick={onEditTitle}
            className="p-1 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors ml-2"
            aria-label="Edit title"
          >
            <Pencil className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}
