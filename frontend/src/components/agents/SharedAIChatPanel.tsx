"use client";

export interface GroundedAIContext {
  surface?: string;
  entityType?: string;
  entityId?: string;
  entityName?: string;
  title?: string;
  summary?: string;
  facts?: { label: string; value: string | number }[];
  contextData?: Record<string, unknown>;
}

interface SharedAIChatPanelProps {
  context: GroundedAIContext;
  panelTitle?: string;
  emptyHint?: string;
  onClose?: () => void;
  className?: string;
}

export default function SharedAIChatPanel({ context, onClose }: SharedAIChatPanelProps) {
  return (
    <div className="flex flex-col items-center justify-center h-64 text-warroom-muted">
      <p className="text-sm">AI Chat — coming soon</p>
      <p className="text-xs mt-1">Context: {context.entityName}</p>
      {onClose && (
        <button onClick={onClose} className="mt-4 text-xs text-warroom-accent hover:underline">
          Close
        </button>
      )}
    </div>
  );
}
