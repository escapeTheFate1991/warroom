"use client";

import { useState } from "react";
import { MessageSquare } from "lucide-react";

import SharedAIChatPanel, { type GroundedAIContext } from "@/components/agents/SharedAIChatPanel";

type Props = {
  context: GroundedAIContext;
  buttonLabel?: string;
  panelTitle?: string;
  emptyHint?: string;
  className?: string;
  buttonClassName?: string;
  disabled?: boolean;
};

export default function AskAIButton({
  context,
  buttonLabel = "Ask AI here",
  panelTitle,
  emptyHint,
  className = "",
  buttonClassName = "",
  disabled = false,
}: Props) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <div className={className}>
        <button
          type="button"
          onClick={() => setOpen(true)}
          disabled={disabled}
          className={`inline-flex items-center justify-center gap-1.5 rounded-lg border border-warroom-accent/30 bg-warroom-accent/10 px-3 py-2 text-sm font-medium text-warroom-accent transition hover:bg-warroom-accent/15 disabled:opacity-50 ${buttonClassName}`.trim()}
        >
          <MessageSquare size={14} />
          {buttonLabel}
        </button>
      </div>

      {open && (
        <>
          <div className="fixed inset-0 z-40 bg-black/30" onClick={() => setOpen(false)} />
          <div className="fixed inset-x-4 bottom-6 top-20 z-50 mx-auto max-w-2xl">
            <SharedAIChatPanel
              context={context}
              panelTitle={panelTitle || `Ask AI about ${context.title || context.surface}`}
              emptyHint={emptyHint}
              onClose={() => setOpen(false)}
              className="h-full shadow-2xl"
            />
          </div>
        </>
      )}
    </>
  );
}