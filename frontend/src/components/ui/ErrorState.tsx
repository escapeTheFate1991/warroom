"use client";

import { AlertTriangle } from "lucide-react";

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export default function ErrorState({ message = "Something went wrong", onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <AlertTriangle className="w-10 h-10 text-red-400 mb-4" />
      <h3 className="text-lg font-medium text-warroom-text mb-2">Error</h3>
      <p className="text-sm text-warroom-muted mb-6">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-warroom-accent text-white rounded-lg text-sm hover:opacity-90 transition-opacity"
        >
          Try Again
        </button>
      )}
    </div>
  );
}

