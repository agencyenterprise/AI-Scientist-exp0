"use client";

import { ModelSelector } from "@/features/model-selector/components/ModelSelector";
import { PromptTypes } from "@/shared/lib/prompt-types";

interface ChatGptUrlInputProps {
  url: string;
  onUrlChange: (value: string) => void;
  disabled?: boolean;
  error?: string | null;
  isExtracting?: boolean;
  // Model selector props
  onModelChange: (model: string, provider: string) => void;
  onModelDefaults: (model: string, provider: string) => void;
  selectedModel: string;
  selectedProvider: string;
}

export function ChatGptUrlInput({
  url,
  onUrlChange,
  disabled = false,
  error = null,
  isExtracting = false,
  onModelChange,
  onModelDefaults,
  selectedModel,
  selectedProvider,
}: ChatGptUrlInputProps) {
  const isDisabled = disabled || isExtracting;

  return (
    <div className="rounded-2xl border border-slate-800/70 bg-slate-950/60 p-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <label
          className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400"
          htmlFor="chatgpt-url"
        >
          Paste chatgpt share link
        </label>
        <p className="text-xs text-slate-500">
          We&apos;ll extract the title and summary automatically.
        </p>
      </div>
      <div className="mt-3 flex flex-col gap-3 md:flex-row md:items-center">
        <div className="relative flex-1">
          <input
            id="chatgpt-url"
            placeholder="https://chatgpt.com/share/..."
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 pr-32 text-sm text-slate-100 placeholder:text-slate-500 outline-none transition focus:border-sky-500/50 focus:ring-2 focus:ring-sky-400/20 disabled:opacity-50 [&:-webkit-autofill]:bg-slate-900 [&:-webkit-autofill]:[-webkit-text-fill-color:rgb(241,245,249)] [&:-webkit-autofill]:shadow-[inset_0_0_0px_1000px_rgb(15,23,42)] [&:-webkit-autofill]:[-webkit-box-shadow:0_0_0px_1000px_rgb(15,23,42)_inset]"
            value={url}
            onChange={event => onUrlChange(event.target.value)}
            disabled={isDisabled}
          />
          {isExtracting && (
            <span className="pointer-events-none absolute right-2 top-1/2 inline-flex -translate-y-1/2 items-center gap-1 rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.3em] text-sky-200">
              <svg
                className="h-3.5 w-3.5 animate-spin"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              Extracting…
            </span>
          )}
        </div>
      </div>
      <p
        className={`mt-2 text-xs ${isExtracting ? "text-sky-200" : error ? "text-rose-400" : "text-slate-500"}`}
      >
        {isExtracting
          ? "Extracting the hypothesis from ChatGPT — this usually takes under 30 seconds. We'll spin up a new run as soon as it's ready."
          : error
            ? error
            : "Paste a shared ChatGPT conversation URL to automatically extract and structure your hypothesis."}
      </p>

      <div className="mt-3 flex items-center gap-2">
        <span className="text-xs text-slate-400">Model:</span>
        <ModelSelector
          promptType={PromptTypes.IDEA_CHAT}
          onModelChange={onModelChange}
          onDefaultsChange={onModelDefaults}
          selectedModel={selectedModel}
          selectedProvider={selectedProvider}
          disabled={isDisabled}
          showMakeDefault={true}
          showCapabilities={false}
        />
      </div>
    </div>
  );
}
