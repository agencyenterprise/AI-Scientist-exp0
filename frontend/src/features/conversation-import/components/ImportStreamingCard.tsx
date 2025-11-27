"use client";

import React from "react";

import { ImportState } from "../types/types";
import { ImportProgressIndicator } from "./ImportProgressIndicator";

export interface ImportStreamingCardProps {
  streamingContent: string;
  currentState: ImportState | "";
  summaryProgress: number | null;
  isUpdateMode: boolean;
  textareaRef?: React.RefObject<HTMLTextAreaElement | null>;
  // Optional: customize appearance
  showHeader?: boolean;
  title?: string;
  onClose?: () => void;
  className?: string;
}

/**
 * Reusable streaming card component that displays import progress.
 * Can be used in modals, inline cards, or any other context.
 */
export function ImportStreamingCard({
  streamingContent,
  currentState,
  summaryProgress,
  isUpdateMode,
  textareaRef,
  showHeader = false,
  title,
  onClose,
  className = "",
}: ImportStreamingCardProps) {
  const headerTitle = title || (isUpdateMode ? "Updating Conversation" : "Importing Conversation");

  return (
    <div className={`p-6 ${className}`}>
      {showHeader && (
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-foreground">{headerTitle}</h3>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="text-muted-foreground hover:text-foreground disabled:opacity-50 p-1 rounded"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          )}
        </div>
      )}

      <div className="mb-4">
        {isUpdateMode ? (
          <div className="bg-muted border border-border rounded-md p-8 text-center">
            <div className="space-y-4">
              <div className="text-sm text-muted-foreground">
                Updating conversation with latest content...
              </div>
              <div className="text-xs text-muted-foreground">
                Your existing project draft will be preserved.
              </div>
            </div>
          </div>
        ) : (
          <textarea
            ref={textareaRef}
            value={streamingContent}
            readOnly
            className="w-full h-64 p-3 bg-muted border border-border rounded-md text-sm font-mono resize-none text-foreground"
            placeholder="Analyzing conversation and generating project draft..."
          />
        )}
      </div>

      <ImportProgressIndicator
        state={currentState}
        progress={summaryProgress}
        isUpdateMode={isUpdateMode}
      />
    </div>
  );
}
