"use client";

import type { ConversationDetail } from "@/types";
import React, { useEffect, useState } from "react";

import { useConversationActions } from "../hooks/useConversationActions";
import { DeleteConfirmModal } from "./DeleteConfirmModal";
import { TitleEditor } from "./TitleEditor";
import { type ViewMode } from "./ViewModeTabs";

interface ConversationHeaderProps {
  conversation: ConversationDetail;
  onConversationDeleted?: () => void;
  onTitleUpdated?: (updatedConversation: ConversationDetail) => void;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
}

export function ConversationHeader({
  conversation,
  onConversationDeleted,
  onTitleUpdated,
  viewMode,
}: ConversationHeaderProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [pendingView, setPendingView] = useState<ViewMode | null>(null);

  const { isDeleting, isUpdatingTitle, deleteConversation, updateTitle } = useConversationActions();

  useEffect(() => {
    if (pendingView && viewMode === pendingView) {
      setPendingView(null);
    }
  }, [viewMode, pendingView]);

  const handleDeleteConversation = async (): Promise<void> => {
    const success = await deleteConversation(conversation.id);
    if (success) {
      setShowDeleteConfirm(false);
      onConversationDeleted?.();
    }
  };

  const handleStartEdit = (): void => {
    setEditTitle(conversation.title);
    setIsEditingTitle(true);
  };

  const handleCancelEdit = (): void => {
    setIsEditingTitle(false);
    setEditTitle("");
  };

  const handleSaveTitle = async (): Promise<void> => {
    if (!editTitle.trim()) return;

    const trimmedTitle = editTitle.trim();
    if (trimmedTitle === conversation.title) {
      handleCancelEdit();
      return;
    }

    const updatedConversation = await updateTitle(conversation.id, trimmedTitle);
    if (updatedConversation) {
      setIsEditingTitle(false);
      setEditTitle("");
      onTitleUpdated?.(updatedConversation);
    }
  };

  return (
    <div className="flex flex-row items-center justify-between gap-4 mb-4 md:mb-6">
      <TitleEditor
        title={conversation.title}
        isEditing={isEditingTitle}
        editValue={editTitle}
        isUpdating={isUpdatingTitle}
        isDeleting={isDeleting}
        onEditValueChange={setEditTitle}
        onStartEdit={handleStartEdit}
        onSave={handleSaveTitle}
        onCancel={handleCancelEdit}
        onDelete={() => setShowDeleteConfirm(true)}
      />

      <DeleteConfirmModal
        isOpen={showDeleteConfirm}
        title={conversation.title}
        isDeleting={isDeleting}
        onConfirm={handleDeleteConversation}
        onCancel={() => setShowDeleteConfirm(false)}
      />
    </div>
  );
}
