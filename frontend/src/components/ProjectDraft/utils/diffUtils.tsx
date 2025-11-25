import React, { ReactElement } from "react";
import { diff_match_patch } from "diff-match-patch";
import type { ProjectDraftVersion } from "@/types";

/**
 * Interface for diff result with React elements
 */
export interface DiffContent {
  elements: ReactElement[];
}

/**
 * Generate diff content for title comparison between two versions
 */
export function generateTitleDiff(
  fromVersion: ProjectDraftVersion,
  toVersion: ProjectDraftVersion
): ReactElement[] {
  const dmp = new diff_match_patch();
  const diffs = dmp.diff_main(fromVersion.title, toVersion.title);
  dmp.diff_cleanupSemantic(diffs);

  return diffs.map((diff, index) => {
    const [operation, text] = diff;

    if (operation === 0) {
      // No change
      return (
        <span key={index} className="text-gray-900">
          {text}
        </span>
      );
    } else if (operation === -1) {
      // Deletion
      return (
        <span key={index} className="bg-red-100 text-red-800 px-1 rounded">
          <span className="line-through">{text}</span>
        </span>
      );
    } else {
      // Addition
      return (
        <span key={index} className="bg-green-100 text-green-800 px-1 rounded">
          <span className="font-medium">{text}</span>
        </span>
      );
    }
  });
}

/**
 * Generate diff content for description comparison between two versions
 */
export function generateDescriptionDiff(
  fromVersion: ProjectDraftVersion,
  toVersion: ProjectDraftVersion
): ReactElement[] {
  const dmp = new diff_match_patch();
  const diffs = dmp.diff_main(fromVersion.description, toVersion.description);
  dmp.diff_cleanupSemantic(diffs);

  return diffs.flatMap((diff, index) => {
    const [operation, text] = diff;
    const lines = text.split("\n");

    return lines.map((line, lineIndex) => {
      const key = `${index}-${lineIndex}`;
      const isLastLine = lineIndex === lines.length - 1;

      if (operation === 0) {
        // No change
        return (
          <span key={key} className="text-gray-900">
            {line}
            {!isLastLine && <br />}
          </span>
        );
      } else if (operation === -1) {
        // Deletion
        return (
          <span key={key} className="bg-red-100 text-red-800 px-1 rounded">
            <span className="line-through">{line}</span>
            {!isLastLine && <br />}
          </span>
        );
      } else {
        // Addition
        return (
          <span key={key} className="bg-green-100 text-green-800 px-1 rounded">
            <span className="font-medium">{line}</span>
            {!isLastLine && <br />}
          </span>
        );
      }
    });
  });
}

/**
 * Check if two versions can be compared for diffs
 */
export function canCompareVersions(
  fromVersion: ProjectDraftVersion | null,
  toVersion: ProjectDraftVersion | null
): boolean {
  return !!(fromVersion && toVersion && fromVersion.version_id !== toVersion.version_id);
}
