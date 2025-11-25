import { useState, useEffect, useCallback, useRef } from "react";
import type {
  ConversationDetail,
  Project,
  ProjectDraft,
  ProjectDraftGetResponse,
  ProjectGetResponse,
} from "@/types";
import { config, constants } from "@/lib/config";
import { isProjectDraftGenerating } from "../utils/versionUtils";

interface UseProjectDraftStateProps {
  conversation: ConversationDetail;
}

interface UseProjectDraftStateReturn {
  projectDraft: ProjectDraft | null;
  setProjectDraft: (draft: ProjectDraft) => void;
  project: Project | null;
  setProject: (project: Project) => void;
  isLoading: boolean;
  isEditing: boolean;
  setIsEditing: (editing: boolean) => void;
  editTitle: string;
  setEditTitle: (title: string) => void;
  editDescription: string;
  setEditDescription: (description: string) => void;
  isUpdating: boolean;
  isCreateModalOpen: boolean;
  setIsCreateModalOpen: (open: boolean) => void;
  isCreatingProject: boolean;
  setIsCreatingProject: (creating: boolean) => void;
  containerRef: React.RefObject<HTMLDivElement | null>;
  handleEdit: () => void;
  handleSave: () => Promise<void>;
  handleCancelEdit: () => void;
  handleKeyDown: (event: React.KeyboardEvent, action: () => void) => void;
  handleCreateProject: () => void;
  handleCloseCreateModal: () => void;
  handleConfirmCreateProject: () => Promise<void>;
  updateProjectDraft: (title: string, description: string) => Promise<void>;
}

export function useProjectDraftState({
  conversation,
}: UseProjectDraftStateProps): UseProjectDraftStateReturn {
  const [projectDraft, setProjectDraft] = useState<ProjectDraft | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const isLocked = conversation.is_locked;

  const updateProjectDraft = useCallback(
    async (title: string, description: string): Promise<void> => {
      setIsUpdating(true);
      try {
        const response = await fetch(
          `${config.apiUrl}/conversations/${conversation.id}/project-draft`,
          {
            method: "PATCH",
            headers: {
              "Content-Type": "application/json",
            },
            credentials: "include",
            body: JSON.stringify({
              title: title,
              description: description,
            } satisfies import("@/types").ApiComponents["schemas"]["ProjectDraftCreateRequest"]),
          }
        );

        if (response.ok) {
          const result: ProjectDraftGetResponse = await response.json();
          setProjectDraft(result.project_draft);
          return;
        }
        const errorResult = await response.json();
        throw new Error(errorResult.error || "Failed to update project draft");
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error("Failed to update project draft:", error);
        throw error;
      } finally {
        setIsUpdating(false);
      }
    },
    [conversation.id]
  );

  const handleEdit = (): void => {
    setEditTitle(projectDraft?.active_version?.title || "");
    setEditDescription(projectDraft?.active_version?.description || "");
    setIsEditing(true);
  };

  const handleSave = async (): Promise<void> => {
    const trimmedTitle = editTitle.trim();
    const trimmedDescription = editDescription.trim();

    if (!trimmedTitle || !trimmedDescription) return;

    try {
      await updateProjectDraft(trimmedTitle, trimmedDescription);
      setIsEditing(false);
      setEditTitle("");
      setEditDescription("");
    } catch {
      // Error handling is done in updateProjectDraft
    }
  };

  const handleCancelEdit = (): void => {
    setIsEditing(false);
    setEditTitle("");
    setEditDescription("");
  };

  const handleKeyDown = (event: React.KeyboardEvent, action: () => void): void => {
    if (event.key === "Enter" && event.ctrlKey) {
      action();
    } else if (event.key === "Escape") {
      handleCancelEdit();
    }
  };

  const handleCreateProject = (): void => {
    setIsCreateModalOpen(true);
  };

  const handleCloseCreateModal = (): void => {
    setIsCreateModalOpen(false);
  };

  const handleConfirmCreateProject = async (): Promise<void> => {
    if (!projectDraft?.active_version) return;

    setIsCreatingProject(true);
    try {
      const response = await fetch(`${config.apiUrl}/conversations/${conversation.id}/project`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({
          title: projectDraft.active_version.title,
          description: projectDraft.active_version.description,
        }),
      });

      if (response.ok) {
        const result: ProjectGetResponse = await response.json();
        setProject(result.project);
        setIsCreateModalOpen(false);
        return;
      }
      const errorResult = await response.json();
      throw new Error(errorResult.error || "Failed to create project");
    } catch (error) {
      // Re-throw error so the modal can display it
      throw error;
    } finally {
      setIsCreatingProject(false);
    }
  };

  // Load initial data
  useEffect(() => {
    const loadData = async (): Promise<void> => {
      try {
        // Always load project draft, even when locked (read-only display)
        const draftResponse = await fetch(
          `${config.apiUrl}/conversations/${conversation.id}/project-draft`,
          {
            credentials: "include",
          }
        );
        if (draftResponse.ok) {
          const draftResult: ProjectDraftGetResponse = await draftResponse.json();
          setProjectDraft(draftResult.project_draft);
        }

        // Additionally load project details when locked (for Linear link/title)
        if (isLocked) {
          const projectResponse = await fetch(
            `${config.apiUrl}/conversations/${conversation.id}/project`,
            {
              credentials: "include",
            }
          );
          if (projectResponse.ok) {
            const projectResult: ProjectGetResponse = await projectResponse.json();
            setProject(projectResult.project);
          }
        }
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error("Failed to load data:", error);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [conversation.id, isLocked]);

  // Poll for project draft updates when project is being generated
  useEffect(() => {
    if (isLocked) {
      return;
    }

    const checkAndPoll = async () => {
      try {
        const response = await fetch(
          `${config.apiUrl}/conversations/${conversation.id}/project-draft`,
          {
            credentials: "include",
          }
        );
        if (response.ok) {
          const result: ProjectDraftGetResponse = await response.json();
          const draft = result.project_draft;
          setProjectDraft(draft);

          // Only continue polling if draft is still being generated
          if (isProjectDraftGenerating(draft)) {
            return true; // Continue polling
          }
        }
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error("Polling error:", error);
      }
      return false; // Stop polling
    };

    const pollInterval = setInterval(async () => {
      const shouldContinue = await checkAndPoll();
      if (!shouldContinue) {
        clearInterval(pollInterval);
      }
    }, constants.POLL_INTERVAL_MS);

    return () => {
      clearInterval(pollInterval);
    };
  }, [conversation.id, isLocked]);

  // Scroll to bottom when component mounts or project draft loads
  useEffect(() => {
    if (containerRef.current && !isLoading) {
      // Scroll to bottom after a brief delay to ensure content is rendered
      setTimeout(() => {
        if (containerRef.current) {
          containerRef.current.scrollTop = containerRef.current.scrollHeight;
        }
      }, 100);
    }
  }, [isLoading, projectDraft]);

  return {
    projectDraft,
    setProjectDraft,
    project,
    setProject,
    isLoading,
    isEditing,
    setIsEditing,
    editTitle,
    setEditTitle,
    editDescription,
    setEditDescription,
    isUpdating,
    isCreateModalOpen,
    setIsCreateModalOpen,
    isCreatingProject,
    setIsCreatingProject,
    containerRef,
    handleEdit,
    handleSave,
    handleCancelEdit,
    handleKeyDown,
    handleCreateProject,
    handleCloseCreateModal,
    handleConfirmCreateProject,
    updateProjectDraft,
  };
}
