import ReactMarkdown from "react-markdown";
import { Pencil, Plus, Trash2 } from "lucide-react";

import { markdownComponents } from "../utils/markdownComponents";

interface ExperimentsSectionProps {
  experiments: string[];
  onEditAll?: () => void;
  onEditItem?: (index: number) => void;
  onAddItem?: () => void;
  onDeleteItem?: (index: number) => void;
  isDeleting?: boolean;
}

export function ExperimentsSection({
  experiments,
  onEditAll,
  onEditItem,
  onAddItem,
  onDeleteItem,
  isDeleting = false,
}: ExperimentsSectionProps) {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs font-semibold text-primary uppercase tracking-widest">
          Experiments
        </h3>
        <div className="flex items-center gap-1">
          {onAddItem && (
            <button
              onClick={onAddItem}
              disabled={isDeleting}
              className="p-1 text-muted-foreground hover:text-primary hover:bg-primary/10 rounded transition-colors disabled:opacity-50"
              aria-label="Add experiment"
              title="Add new experiment"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          )}
          {onEditAll && (
            <button
              onClick={onEditAll}
              className="p-1 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors"
              aria-label="Edit all experiments"
            >
              <Pencil className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
      <div className="space-y-3">
        {experiments.map((experiment, idx) => (
          <article
            key={idx}
            className="group overflow-hidden rounded-xl border border-border bg-muted/50 p-4 transition hover:border-primary/40"
          >
            <div className="flex items-start gap-3">
              <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-primary text-primary-foreground text-xs font-bold flex-shrink-0 shadow-sm">
                {idx + 1}
              </span>
              <div className="flex-1 text-sm text-foreground leading-relaxed">
                <ReactMarkdown components={markdownComponents}>{experiment}</ReactMarkdown>
              </div>
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                {onEditItem && (
                  <button
                    onClick={() => onEditItem(idx)}
                    className="p-1 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors"
                    aria-label={`Edit experiment ${idx + 1}`}
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                )}
                {onDeleteItem && experiments.length > 1 && (
                  <button
                    onClick={() => onDeleteItem(idx)}
                    disabled={isDeleting}
                    className="p-1 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded transition-colors disabled:opacity-50"
                    aria-label={`Delete experiment ${idx + 1}`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
