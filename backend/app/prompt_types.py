"""
Prompt types enumeration for the AGI Judd's Idea Catalog.

This module contains enums for different types of prompts used throughout the application.
"""

from enum import Enum


class PromptTypes(str, Enum):
    """Enumeration of available prompt types."""

    PROJECT_DRAFT_CHAT = "project_draft_chat"
    PROJECT_DRAFT_GENERATION = "project_draft_generation"
