/**
 * Prompt types enumeration for the AGI Judd's Idea Catalog frontend.
 *
 * This module contains enums for different types of prompts used throughout the frontend application.
 */

export const PromptTypes = {
  PROJECT_DRAFT_CHAT: "project_draft_chat",
  PROJECT_DRAFT_GENERATION: "project_draft_generation",
  IMPORTED_CHAT_SUMMARY: "imported_chat_summary",
} as const;

export type PromptType = (typeof PromptTypes)[keyof typeof PromptTypes];
