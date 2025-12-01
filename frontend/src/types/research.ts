/**
 * Types for research pipeline runs
 */

// API Response types (snake_case from backend)
export interface ResearchRunListItemApi {
  run_id: string;
  status: string;
  idea_title: string;
  idea_hypothesis: string | null;
  current_stage: string | null;
  progress: number | null;
  gpu_type: string | null;
  best_metric: string | null;
  created_by_name: string;
  created_at: string;
  updated_at: string;
  artifacts_count: number;
  error_message: string | null;
  conversation_id: number;
}

export interface ResearchRunListResponseApi {
  items: ResearchRunListItemApi[];
  total: number;
}

// Frontend types (camelCase)
export interface ResearchRun {
  runId: string;
  status: string;
  ideaTitle: string;
  ideaHypothesis: string | null;
  currentStage: string | null;
  progress: number | null;
  gpuType: string | null;
  bestMetric: string | null;
  createdByName: string;
  createdAt: string;
  updatedAt: string;
  artifactsCount: number;
  errorMessage: string | null;
  conversationId: number;
}

export interface ResearchRunListResponse {
  items: ResearchRun[];
  total: number;
}

// Status type for UI styling
export type ResearchRunStatus = "pending" | "running" | "completed" | "failed";
