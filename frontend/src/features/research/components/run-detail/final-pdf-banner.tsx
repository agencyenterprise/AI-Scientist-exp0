"use client";

import { Download, FileText, FolderArchive } from "lucide-react";
import type { ArtifactMetadata } from "@/types/research";
import { formatBytes } from "@/shared/lib/date-utils";
import { useArtifactDownload } from "@/features/research/hooks/useArtifactDownload";

interface FinalPdfBannerProps {
  artifacts: ArtifactMetadata[];
  conversationId: number;
  runId: string;
}

/**
 * Prominent banner for downloading final research results.
 * Shows final PDF paper and workspace archive when available.
 */
export function FinalPdfBanner({ artifacts, conversationId, runId }: FinalPdfBannerProps) {
  const { downloadArtifact, isDownloading, downloadingArtifactId, error } = useArtifactDownload({
    conversationId,
    runId,
  });
  // Find all paper PDF artifacts, sorted by created_at (most recent first)
  const paperPdfs = artifacts
    .filter(a => a.artifact_type === "paper_pdf")
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  // Find the workspace archive artifact
  const workspaceArchive = artifacts.find(a => a.artifact_type === "workspace_archive");

  // Don't render if no papers and no workspace archive
  if (paperPdfs.length === 0 && !workspaceArchive) {
    return null;
  }

  return (
    <div className="rounded-lg border border-emerald-800 bg-gradient-to-r from-emerald-950/50 to-emerald-900/30 p-6">
      {/* Header */}
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/20">
          <FileText className="h-6 w-6 text-emerald-400" />
        </div>
        <div>
          <h3 className="text-base font-semibold text-emerald-100">Final Results Ready</h3>
          <p className="text-sm text-emerald-300/80">
            Download{" "}
            {paperPdfs.length > 0 && `${paperPdfs.length} paper${paperPdfs.length > 1 ? "s" : ""}`}
            {paperPdfs.length > 0 && workspaceArchive && " and "}
            {workspaceArchive && "experiment archive"}
          </p>
        </div>
      </div>

      {/* Download Cards - Two Column Layout */}
      <div className="grid gap-3 md:grid-cols-2">
        {/* Left Column: Paper PDFs (50%) */}
        {paperPdfs.length > 0 && (
          <div className="space-y-3 rounded-lg border border-emerald-700/50 bg-emerald-950/30 p-4">
            <div className="mb-3 flex items-center gap-2">
              <FileText className="h-5 w-5 text-emerald-400" />
              <div className="text-sm font-semibold text-emerald-100">
                Research Papers ({paperPdfs.length})
              </div>
            </div>
            <div className="flex gap-2 overflow-x-auto">
              {paperPdfs.map(pdf => (
                <button
                  key={pdf.id}
                  onClick={() => downloadArtifact(pdf.id)}
                  disabled={isDownloading}
                  className="flex min-w-0 flex-1 flex-col items-center justify-center rounded border border-emerald-700/30 bg-emerald-900/20 p-3 transition-colors hover:border-emerald-600/50 hover:bg-emerald-900/30 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <FileText className="h-6 w-6 text-emerald-400/70" />
                  <div className="mt-2 w-full text-center">
                    <div className="truncate text-xs text-emerald-100">{pdf.filename}</div>
                    <div className="mt-1 text-xs text-emerald-400/60">
                      {pdf.file_size ? formatBytes(pdf.file_size) : "—"}
                    </div>
                  </div>
                  {downloadingArtifactId === pdf.id ? (
                    <div className="mt-1.5 h-3.5 w-3.5 animate-pulse text-emerald-400">...</div>
                  ) : (
                    <Download className="mt-1.5 h-3.5 w-3.5 text-emerald-400" />
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Right Column: Workspace Archive (50%) */}
        {workspaceArchive && (
          <div className="flex flex-col justify-between rounded-lg border border-emerald-700/50 bg-emerald-950/30 p-4">
            <div className="flex items-start gap-3">
              <FolderArchive className="h-5 w-5 flex-shrink-0 text-emerald-400" />
              <div className="flex-1">
                <div className="text-sm font-semibold text-emerald-100">Experiment Archive</div>
                <div className="mt-1 text-xs text-emerald-400/70">
                  {workspaceArchive.file_size
                    ? formatBytes(workspaceArchive.file_size)
                    : "Unknown size"}{" "}
                  &middot; Complete experiment data
                </div>
                <div className="mt-2 text-xs text-emerald-400/50">
                  Includes code, logs, plots, and all intermediate artifacts
                </div>
              </div>
            </div>
            <button
              onClick={() => downloadArtifact(workspaceArchive.id)}
              disabled={isDownloading}
              className="mt-4 flex items-center justify-center gap-2 rounded border border-emerald-600 bg-emerald-500/20 px-4 py-2.5 text-sm font-medium text-emerald-100 transition-colors hover:bg-emerald-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {downloadingArtifactId === workspaceArchive.id ? (
                <>
                  <div className="h-4 w-4 animate-pulse">...</div>
                  <span>Downloading...</span>
                </>
              ) : (
                <>
                  <Download className="h-4 w-4 text-emerald-100" />
                  <span className="text-emerald-100">Download Archive</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="mt-3 rounded border border-red-800 bg-red-950/30 px-3 py-2 text-sm text-red-400">
          {error}
        </div>
      )}
    </div>
  );
}
