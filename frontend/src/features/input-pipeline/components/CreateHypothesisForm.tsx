"use client";

import {
  ConflictResolution,
  ImportStreamingCard,
  ModelLimitConflict,
  useConversationImport,
} from "@/features/conversation-import";
import { ChatGptUrlInput } from "@/features/input-pipeline/components/ChatGptUrlInput";
import { HypothesisForm } from "@/features/input-pipeline/components/HypothesisForm";
import { hypothesisFormSchema } from "@/features/input-pipeline/schemas/hypothesisSchema";
import { useRouter } from "next/navigation";
import { FormEvent, useState, useTransition } from "react";

export function CreateHypothesisForm() {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  // Manual form state
  const [title, setTitle] = useState("");
  const [idea, setIdea] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  // Conversation import hook for ChatGPT URL
  const importState = useConversationImport({
    autoRedirect: true,
    onSuccess: id => {
      router.push(`/conversations/${id}`);
      router.refresh();
    },
  });

  const hasManualInput = title.trim() || idea.trim();
  const hasChatGptUrl = importState.state.url.trim();
  const isDisabled = pending || importState.status.isImporting;

  const submitManualForm = async () => {
    const validation = hypothesisFormSchema.safeParse({ title, idea });
    if (!validation.success) {
      setFormError(validation.error.issues[0]?.message || "Validation failed");
      return;
    }

    startTransition(async () => {
      setFormError(null);

      const response = await fetch("/api/hypotheses", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ title, idea }),
      });

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        const message = (data && (data.message || data.error)) || "Failed to create hypothesis";
        setFormError(message);
        return;
      }

      setTitle("");
      setIdea("");
      router.push(data?.ideation?.redirectUrl || "/");
      router.refresh();
    });
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    // Clear previous errors
    setFormError(null);

    // Prioritize ChatGPT URL if filled
    if (hasChatGptUrl) {
      importState.actions.startImport();
      return;
    }

    // Otherwise submit manual form
    if (hasManualInput) {
      submitManualForm();
      return;
    }

    // Nothing filled
    setFormError("Please fill in the hypothesis details or paste a ChatGPT URL");
  };

  // Clear the other input when one is being used
  const handleTitleChange = (value: string) => {
    setTitle(value);
    if (value.trim()) {
      importState.actions.setUrl("");
    }
  };

  const handleIdeaChange = (value: string) => {
    setIdea(value);
    if (value.trim()) {
      importState.actions.setUrl("");
    }
  };

  const handleUrlChange = (value: string) => {
    importState.actions.setUrl(value);
    if (value.trim()) {
      setTitle("");
      setIdea("");
      setFormError(null);
    }
  };

  // Handle cancel/reset from streaming view
  const handleCancelImport = () => {
    importState.actions.reset();
  };

  // Show streaming card when importing
  if (importState.status.isImporting) {
    return (
      <div className="space-y-4">
        <ImportStreamingCard
          streamingContent={importState.state.streamingContent}
          currentState={importState.state.currentState}
          summaryProgress={importState.state.summaryProgress}
          isUpdateMode={importState.state.isUpdateMode}
          textareaRef={importState.streamingRef}
          showHeader={true}
          title="Importing ChatGPT Conversation"
          onClose={handleCancelImport}
          className="rounded-2xl border border-slate-800/70 bg-slate-950/60"
        />
      </div>
    );
  }

  // Show conflict resolution when there's a duplicate URL conflict
  if (importState.status.hasConflict) {
    return (
      <div className="rounded-2xl border border-slate-800/70 bg-slate-950/60">
        <ConflictResolution
          conflicts={importState.conflict.items}
          selectedConflictId={importState.conflict.selectedId}
          onSelectConflict={importState.actions.selectConflict}
          onGoToSelected={importState.actions.resolveConflictGoTo}
          onUpdateSelected={importState.actions.resolveConflictUpdate}
          onCreateNew={importState.actions.resolveConflictCreateNew}
          onCancel={importState.actions.cancelConflict}
          onClose={handleCancelImport}
        />
      </div>
    );
  }

  // Show model limit conflict when conversation is too large
  if (importState.status.hasModelLimitConflict) {
    return (
      <div className="rounded-2xl border border-slate-800/70 bg-slate-950/60">
        <ModelLimitConflict
          message={importState.modelLimit.message}
          suggestion={importState.modelLimit.suggestion}
          onProceed={importState.actions.proceedWithSummarization}
          onCancel={importState.actions.cancelModelLimit}
          onClose={handleCancelImport}
        />
      </div>
    );
  }

  // Default: show the form
  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <HypothesisForm
        title={title}
        idea={idea}
        onTitleChange={handleTitleChange}
        onIdeaChange={handleIdeaChange}
        disabled={isDisabled}
      />

      <div className="relative py-4">
        <div className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-gradient-to-r from-transparent via-slate-800/80 to-transparent" />
        <span className="relative mx-auto flex w-fit items-center gap-2 rounded-full border border-slate-800/80 bg-slate-950 px-4 py-1 text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-400">
          or
        </span>
      </div>

      <ChatGptUrlInput
        url={importState.state.url}
        onUrlChange={handleUrlChange}
        disabled={isDisabled}
        error={importState.state.error || null}
        isExtracting={importState.status.isImporting}
        onModelChange={importState.actions.setModel}
        onModelDefaults={importState.actions.setModelDefaults}
        selectedModel={importState.model.selected}
        selectedProvider={importState.model.provider}
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <button
          type="submit"
          className="inline-flex items-center justify-center rounded-full bg-gradient-to-r from-sky-500 via-blue-500 to-cyan-400 px-6 py-3 text-sm font-semibold text-white shadow-[0_18px_40px_-18px_rgba(56,189,248,0.65)] transition hover:from-sky-400 hover:via-blue-400 hover:to-cyan-300 focus:outline-none focus:ring-2 focus:ring-sky-300 focus:ring-offset-2 focus:ring-offset-slate-950 disabled:opacity-40"
          disabled={isDisabled}
        >
          {importState.status.isImporting
            ? "Importing..."
            : pending
              ? "Launching..."
              : "Launch hypothesis"}
        </button>
        {formError && <span className="text-sm text-rose-400">{formError}</span>}
      </div>
    </form>
  );
}
