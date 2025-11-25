"""
Models module for the AGI Judd's Idea Catalog.

This module exports all Pydantic models for data validation and API contracts.
"""

# Auth models
from app.models.auth import (
    AuthStatus,
    AuthUser,
    GoogleOAuthCallbackRequest,
    ServiceKey,
    User,
    UserSession,
)

# Chat models
from app.models.chat import ChatMessage, ChatRequest, ChatResponse

# Conversation models
from app.models.conversations import (
    ChatMessageData,
    ConversationResponse,
    ConversationUpdate,
    ImportChatCreateNew,
    ImportChatGPTConversation,
    ImportChatPrompt,
    ImportChatUpdateExisting,
    ImportedChat,
    ImportedChatMessage,
    ParseErrorResult,
    ParseResult,
    ParseSuccessResult,
    SlackImportRequest,
)
from app.models.imported_conversation_summary import ImportedConversationSummaryUpdate

# LLM prompt models
from app.models.llm_prompts import (
    LLMDefault,
    LLMDefaultsResponse,
    LLMDefaultsUpdateRequest,
    LLMDefaultsUpdateResponse,
    LLMModel,
    LLMPromptCreateRequest,
    LLMPromptDeleteRequest,
    LLMPromptDeleteResponse,
    LLMPromptResponse,
    LLMProvidersResponse,
)

# Project draft models
from app.models.project_drafts import (
    ProjectDraft,
    ProjectDraftCreateRequest,
    ProjectDraftRefinementRequest,
    ProjectDraftRefinementResponse,
    ProjectDraftRefinementSuggestion,
    ProjectDraftResponse,
    ProjectDraftVersion,
    ProjectDraftVersionsResponse,
)

# Project models
from app.models.projects import Project, ProjectCreate, ProjectResponse

__all__ = [
    # Conversation models
    "ImportedChatMessage",
    "ImportedChat",
    "ConversationResponse",
    "ConversationUpdate",
    "ConversationSummaryUpdate",
    "ImportChatGPTConversation",
    "ImportChatPrompt",
    "ImportChatCreateNew",
    "ImportChatUpdateExisting",
    "SlackImportRequest",
    "ChatMessageData",
    "ParseSuccessResult",
    "ParseErrorResult",
    "ParseResult",
    # Project draft models
    "ProjectDraftVersion",
    "ProjectDraft",
    "ProjectDraftCreateRequest",
    "ProjectDraftRefinementRequest",
    "ProjectDraftRefinementSuggestion",
    "ProjectDraftResponse",
    "ProjectDraftVersionsResponse",
    "ProjectDraftRefinementResponse",
    # LLM prompt models
    "LLMDefault",
    "LLMDefaultsResponse",
    "LLMDefaultsUpdateRequest",
    "LLMDefaultsUpdateResponse",
    "LLMModel",
    "LLMPromptCreateRequest",
    "LLMPromptDeleteRequest",
    "LLMPromptDeleteResponse",
    "LLMPromptResponse",
    "LLMProvidersResponse",
    # Chat models
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    # Project models
    "Project",
    "ProjectCreate",
    "ProjectResponse",
    # Auth models
    "User",
    "UserSession",
    "ServiceKey",
    "AuthUser",
    "AuthStatus",
    "GoogleOAuthCallbackRequest",
    # Imported conversation summary models
    "ImportedConversationSummaryUpdate",
]
