"use client";

export default function LoadingState({ message = "Loading..." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="animate-spin rounded-full h-8 w-8 border-2 border-warroom-accent border-t-transparent mb-4" />
      <p className="text-sm text-warroom-muted">{message}</p>
    </div>
  );
}

