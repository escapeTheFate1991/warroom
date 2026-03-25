"use client";

export default function LoadingState({ message = "Loading content..." }: { message?: string }) {
  return (
    <div className="space-y-4">
      {/* Show content structure immediately instead of spinner */}
      <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4 animate-pulse">
        <div className="flex gap-3">
          <div className="w-10 h-10 bg-warroom-border rounded-lg" />
          <div className="flex-1 space-y-2">
            <div className="h-4 bg-warroom-border rounded w-3/4" />
            <div className="h-3 bg-warroom-border rounded w-1/2" />
          </div>
        </div>
      </div>
      <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4 animate-pulse">
        <div className="flex gap-3">
          <div className="w-10 h-10 bg-warroom-border rounded-lg" />
          <div className="flex-1 space-y-2">
            <div className="h-4 bg-warroom-border rounded w-2/3" />
            <div className="h-3 bg-warroom-border rounded w-1/3" />
          </div>
        </div>
      </div>
      <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4 animate-pulse">
        <div className="flex gap-3">
          <div className="w-10 h-10 bg-warroom-border rounded-lg" />
          <div className="flex-1 space-y-2">
            <div className="h-4 bg-warroom-border rounded w-5/6" />
            <div className="h-3 bg-warroom-border rounded w-2/5" />
          </div>
        </div>
      </div>
      <p className="text-sm text-warroom-muted text-center mt-4">{message}</p>
    </div>
  );
}

