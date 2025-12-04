"use client";

import type { StageProgress } from "@/types/research";
import { cn } from "@/shared/lib/utils";

interface ResearchPipelineStagesProps {
  stageProgress: StageProgress[];
}

// Define pipeline stages with their metadata
// These match the actual backend stage slugs used in the research pipeline
const PIPELINE_STAGES = [
  {
    id: 1,
    key: "initial_implementation",
    title: "Baseline Implementation",
    description: "Generate working baseline implementation with basic functional correctness",
  },
  {
    id: 2,
    key: "baseline_tuning",
    title: "Baseline Tuning",
    description: "Hyperparameter optimization to improve baseline performance",
  },
  {
    id: 3,
    key: "creative_research",
    title: "Creative Research",
    description: "Novel improvements, plotting, and visualization generation",
  },
  {
    id: 4,
    key: "ablation_studies",
    title: "Ablation Studies",
    description: "Component analysis to validate individual contributions",
  },
] as const;

/**
 * Helper function to extract stage slug from backend stage name
 *
 * Backend format: {stage_number}_{stage_slug}_{substage_number}_{substage_name}
 * Examples:
 *   "1_initial_implementation_1_preliminary" → "initial_implementation"
 *   "2_baseline_tuning_2_optimization" → "baseline_tuning"
 *   "3_creative_research_1_exploration" → "creative_research"
 */
const extractStageSlug = (stageName: string): string | null => {
  const parts = stageName.split('_');

  // Need at least 4 parts: stage_number + slug + substage_number + substage_name
  if (parts.length < 4) return null;

  // Skip first part (stage number), collect parts until we hit next number (substage number)
  const slugParts: string[] = [];
  for (let i = 1; i < parts.length; i++) {
    // Stop when we hit a number (substage number)
    if (/^\d+$/.test(parts[i])) break;
    slugParts.push(parts[i]);
  }

  return slugParts.length > 0 ? slugParts.join('_') : null;
};

interface StageInfo {
  status: "pending" | "in_progress" | "completed";
  progressPercent: number;
  currentIteration: number;
  maxIterations: number;
  details: StageProgress | null;
}

/**
 * Pipeline stages section showing all stages with progress bars
 */
export function ResearchPipelineStages({ stageProgress }: ResearchPipelineStagesProps) {
  /**
   * Get aggregated stage information for a given main stage
   * Handles multiple substages within a main stage by using the latest progress
   */
  const getStageInfo = (stageKey: string): StageInfo => {
    // Find all progress events that match this main stage (across all substages)
    const stageProgresses = stageProgress.filter((progress) => {
      const slug = extractStageSlug(progress.stage);
      return slug === stageKey;
    });

    // No progress data yet for this stage
    if (stageProgresses.length === 0) {
      return {
        status: "pending",
        progressPercent: 0,
        currentIteration: 0,
        maxIterations: 0,
        details: null,
      };
    }

    // Use the most recent progress event (array is ordered by created_at)
    const latestProgress = stageProgresses[stageProgresses.length - 1];
    const progressPercent = Math.round(latestProgress.progress * 100);

    // Determine status based on progress value
    let status: "pending" | "in_progress" | "completed";
    if (latestProgress.progress >= 1.0) {
      status = "completed";
    } else if (latestProgress.progress > 0) {
      status = "in_progress";
    } else {
      status = "pending";
    }

    return {
      status,
      progressPercent,
      currentIteration: latestProgress.iteration,
      maxIterations: latestProgress.max_iterations,
      details: latestProgress,
    };
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 w-full">
      <h2 className="mb-6 text-xl font-semibold text-white">Pipeline Stages</h2>

      <div className="flex flex-col gap-6">
        {PIPELINE_STAGES.map((stage) => {
          const info = getStageInfo(stage.key);

          return (
            <div key={stage.id} className="flex flex-col gap-3">
              {/* Stage header with title, description, and status */}
              <div className="flex items-start justify-between gap-4">
                <div className="flex flex-col gap-1">
                  <h3 className="text-base font-semibold text-white">
                    Stage {stage.id}: {stage.title}
                  </h3>
                  <p className="text-sm text-slate-400">{stage.description}</p>
                </div>

                {/* Status Badge */}
                {info.status === "completed" && (
                  <span className="text-sm font-medium uppercase tracking-wide text-slate-400 whitespace-nowrap">
                    COMPLETED
                  </span>
                )}
                {info.status === "in_progress" && (
                  <span className="text-sm font-medium uppercase tracking-wide text-blue-400 whitespace-nowrap">
                    IN PROGRESS
                  </span>
                )}
              </div>

              {/* Iteration and metrics info (shown when stage is in progress) */}
              {info.status === "in_progress" && info.details && (
                <div className="flex gap-4 text-xs text-slate-500">
                  <span>
                    Iteration: {info.currentIteration}/{info.maxIterations}
                  </span>
                  {info.details.best_metric && (
                    <span>Best: {info.details.best_metric}</span>
                  )}
                  {info.details.good_nodes > 0 && (
                    <span className="text-emerald-400">
                      {info.details.good_nodes} good
                    </span>
                  )}
                  {info.details.buggy_nodes > 0 && (
                    <span className="text-red-400">
                      {info.details.buggy_nodes} buggy
                    </span>
                  )}
                </div>
              )}

              {/* Progress bar */}
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
                <div
                  className={cn(
                    "h-full rounded-full transition-all duration-500",
                    info.status === "completed" || info.status === "in_progress"
                      ? "bg-blue-500"
                      : "bg-slate-700"
                  )}
                  style={{ width: `${info.progressPercent}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
