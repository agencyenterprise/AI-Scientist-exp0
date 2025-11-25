import { useState, useEffect, useCallback, useMemo } from "react";
import type { ProjectDraft, ProjectDraftVersion, ProjectDraftVersionsCleanResponse } from "@/types";
import { config } from "@/lib/config";
import {
  getComparisonVersion,
  getNextVersion,
  canNavigateToPrevious,
  canNavigateToNext,
  getPreviousVersionNumber,
  getNextVersionNumber,
} from "../utils/versionUtils";

interface UseVersionManagementProps {
  conversationId: string;
  isLocked: boolean;
  projectDraft: ProjectDraft | null;
}

interface UseVersionManagementReturn {
  showDiffs: boolean;
  setShowDiffs: (show: boolean) => void;
  allVersions: ProjectDraftVersion[];
  selectedVersionForComparison: number | null;
  setSelectedVersionForComparison: (version: number | null) => void;
  comparisonVersion: ProjectDraftVersion | null;
  nextVersion: ProjectDraftVersion | null;
  canNavigatePrevious: boolean;
  canNavigateNext: boolean;
  handlePreviousVersion: () => void;
  handleNextVersion: () => void;
  loadVersions: () => Promise<void>;
}

export function useVersionManagement({
  conversationId,
  isLocked,
  projectDraft,
}: UseVersionManagementProps): UseVersionManagementReturn {
  const [showDiffs, setShowDiffs] = useState(true);
  const [allVersions, setAllVersions] = useState<ProjectDraftVersion[]>([]);
  const [selectedVersionForComparison, setSelectedVersionForComparison] = useState<number | null>(
    null
  );

  // Get comparison version for diff (either selected or default to previous)
  const comparisonVersion = useMemo((): ProjectDraftVersion | null => {
    return getComparisonVersion(projectDraft, allVersions, selectedVersionForComparison);
  }, [projectDraft, allVersions, selectedVersionForComparison]);

  // Get the "next" version after the comparison version (the "to" version in the diff)
  const nextVersion = useMemo((): ProjectDraftVersion | null => {
    return getNextVersion(comparisonVersion, allVersions);
  }, [comparisonVersion, allVersions]);

  // Check if navigation is available
  const canNavigatePrevious = canNavigateToPrevious(comparisonVersion);
  const canNavigateNext = canNavigateToNext(comparisonVersion, projectDraft);

  // Navigation functions for version comparison
  const handlePreviousVersion = (): void => {
    const previousVersionNumber = getPreviousVersionNumber(comparisonVersion);
    if (previousVersionNumber !== null) {
      setSelectedVersionForComparison(previousVersionNumber);
    }
  };

  const handleNextVersion = (): void => {
    const nextVersionNumber = getNextVersionNumber(comparisonVersion, projectDraft);
    if (nextVersionNumber !== null) {
      setSelectedVersionForComparison(nextVersionNumber);
    }
  };

  // Load project draft versions
  const loadVersions = useCallback(async (): Promise<void> => {
    if (isLocked) return; // Don't load versions for locked conversations

    try {
      const response = await fetch(
        `${config.apiUrl}/conversations/${conversationId}/project-draft/versions`,
        {
          credentials: "include",
        }
      );
      if (response.ok) {
        const result: ProjectDraftVersionsCleanResponse = await response.json();
        setAllVersions(result.versions);
      }
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error("Failed to load versions:", error);
    }
  }, [conversationId, isLocked]);

  // Reset version selection when switching out of diff mode or when conversation changes
  useEffect(() => {
    if (!showDiffs) {
      setSelectedVersionForComparison(null);
    }
  }, [showDiffs]);

  useEffect(() => {
    setSelectedVersionForComparison(null);
  }, [conversationId]);

  return {
    showDiffs,
    setShowDiffs,
    allVersions,
    selectedVersionForComparison,
    setSelectedVersionForComparison,
    comparisonVersion,
    nextVersion,
    canNavigatePrevious,
    canNavigateNext,
    handlePreviousVersion,
    handleNextVersion,
    loadVersions,
  };
}
