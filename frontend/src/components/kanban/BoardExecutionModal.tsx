"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { X, Play, Square, CheckCircle2, Circle, Loader2, XCircle, Ban } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface QueueItem {
  task_id: number;
  title: string;
  status: "pending" | "running" | "done" | "failed" | "cancelled";
  order: number;
  output?: string;
}

interface ExecutionStatus {
  active: boolean;
  execution_id: string | null;
  current_task_index: number;
  total_tasks: number;
  queue: QueueItem[];
}

interface BoardExecutionModalProps {
  onClose: () => void;
  onComplete: () => void;
}

const STATUS_ICON: Record<string, React.ReactNode> = {
  done: <CheckCircle2 size={16} className="text-green-400" />,
  running: <Loader2 size={16} className="text-amber-400 animate-spin" />,
  pending: <Circle size={16} className="text-warroom-muted/50" />,
  failed: <XCircle size={16} className="text-red-400" />,
  cancelled: <Ban size={16} className="text-warroom-muted/40" />,
};

const STATUS_TEXT_COLOR: Record<string, string> = {
  done: "text-green-400",
  running: "text-amber-400",
  pending: "text-warroom-muted",
  failed: "text-red-400",
  cancelled: "text-warroom-muted/50",
};

export default function BoardExecutionModal({ onClose, onComplete }: BoardExecutionModalProps) {
  const [status, setStatus] = useState<ExecutionStatus | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedOutput, setSelectedOutput] = useState<QueueItem | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const outputRef = useRef<HTMLDivElement>(null);
  const prevActiveRef = useRef(false);

  const fetchStatus = useCallback(async () => {
    try {
      const resp = await fetch(`${API}/api/task-execution/status`);
      const data: ExecutionStatus = await resp.json();
      setStatus(data);

      // Detect execution just completed
      if (prevActiveRef.current && !data.active) {
        onComplete();
        stopPolling();
      }
      prevActiveRef.current = data.active;
    } catch {
      console.error("Failed to fetch execution status");
    }
  }, [onComplete]);

  const startPolling = useCallback(() => {
    if (pollRef.current) return;
    pollRef.current = setInterval(fetchStatus, 2000);
  }, [fetchStatus]);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    startPolling();
    return stopPolling;
  }, [fetchStatus, startPolling, stopPolling]);

  // Auto-scroll output
  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [status]);

  const startExecution = async () => {
    setStarting(true);
    setError(null);
    try {
      const resp = await fetch(`${API}/api/task-execution/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.detail || "Failed to start execution");
      }
      await fetchStatus();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to start execution");
    } finally {
      setStarting(false);
    }
  };

  const cancelExecution = async () => {
    try {
      await fetch(`${API}/api/task-execution/cancel`, { method: "POST" });
      await fetchStatus();
    } catch {
      console.error("Failed to cancel execution");
    }
  };

  const completedCount = status?.queue.filter((q) => q.status === "done").length ?? 0;
  const totalCount = status?.total_tasks ?? 0;
  const progressPct = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;

  // Find the currently running or most recent task with output
  const currentTask = status?.queue.find((q) => q.status === "running");
  const displayTask = selectedOutput || currentTask || status?.queue.findLast((q) => q.output);

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-warroom-surface border border-warroom-border rounded-lg w-full max-w-2xl mx-4 max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-warroom-border">
          <h3 className="text-lg font-semibold">🚀 Execute Board</h3>
          <button
            onClick={onClose}
            className="text-warroom-muted hover:text-warroom-text transition p-1"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-400 text-sm">
              {error}
            </div>
          )}

          {!status?.active && status?.queue.length === 0 && (
            /* Idle state */
            <div className="text-center space-y-4 py-8">
              <p className="text-warroom-muted text-sm">
                Execute all tasks assigned to AI Agent in dependency order.
              </p>
              <button
                onClick={startExecution}
                disabled={starting}
                className="inline-flex items-center gap-2 bg-warroom-accent/20 text-warroom-accent px-5 py-2.5 rounded-lg hover:bg-warroom-accent/30 transition disabled:opacity-50 font-medium"
              >
                {starting ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Play size={16} />
                )}
                {starting ? "Starting…" : "▶️ Start Execution"}
              </button>
            </div>
          )}

          {(status?.active || (status && status.queue.length > 0)) && (
            <>
              {/* Progress bar */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs text-warroom-muted">
                  <span>
                    {completedCount} of {totalCount} tasks complete
                  </span>
                  <span>{Math.round(progressPct)}%</span>
                </div>
                <div className="h-2 bg-warroom-border rounded-full overflow-hidden">
                  <div
                    className="h-full bg-warroom-accent rounded-full transition-all duration-500"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
              </div>

              {/* Task queue */}
              <div className="space-y-1">
                <h4 className="text-xs font-semibold text-warroom-muted uppercase tracking-wider mb-2">
                  Task Queue
                </h4>
                {status?.queue.map((item, idx) => (
                  <button
                    key={item.task_id}
                    onClick={() =>
                      setSelectedOutput(
                        selectedOutput?.task_id === item.task_id ? null : item
                      )
                    }
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition ${
                      displayTask?.task_id === item.task_id
                        ? "bg-warroom-accent/10 border border-warroom-accent/20"
                        : "hover:bg-warroom-border/30"
                    }`}
                  >
                    <span className="text-xs text-warroom-muted/50 w-5 text-right">
                      {idx + 1}
                    </span>
                    {STATUS_ICON[item.status]}
                    <span
                      className={`flex-1 text-sm truncate ${STATUS_TEXT_COLOR[item.status]}`}
                    >
                      {item.title}
                    </span>
                    <span className="text-[10px] text-warroom-muted capitalize">
                      {item.status}
                    </span>
                  </button>
                ))}
              </div>

              {/* Live output */}
              {displayTask?.output && (
                <div className="space-y-1.5">
                  <h4 className="text-xs font-semibold text-warroom-muted uppercase tracking-wider">
                    Output — {displayTask.title}
                  </h4>
                  <div
                    ref={outputRef}
                    className="bg-black/40 border border-warroom-border rounded-lg p-4 max-h-48 overflow-y-auto font-mono text-xs text-warroom-text/80 whitespace-pre-wrap leading-relaxed"
                  >
                    {displayTask.output}
                  </div>
                </div>
              )}

              {currentTask && !displayTask?.output && (
                <div className="space-y-1.5">
                  <h4 className="text-xs font-semibold text-warroom-muted uppercase tracking-wider">
                    Live Output
                  </h4>
                  <div className="bg-black/40 border border-warroom-border rounded-lg p-4 h-32 flex items-center justify-center">
                    <div className="flex items-center gap-2 text-warroom-muted text-sm">
                      <Loader2 size={14} className="animate-spin" />
                      Running: {currentTask.title}…
                    </div>
                  </div>
                </div>
              )}

              {/* Cancel / Restart buttons */}
              <div className="flex justify-end gap-3 pt-2">
                {status?.active && (
                  <button
                    onClick={cancelExecution}
                    className="flex items-center gap-2 bg-red-500/10 text-red-400 px-4 py-2 rounded-lg hover:bg-red-500/20 transition text-sm"
                  >
                    <Square size={14} />
                    Cancel
                  </button>
                )}
                {!status?.active && status.queue.length > 0 && (
                  <button
                    onClick={startExecution}
                    disabled={starting}
                    className="flex items-center gap-2 bg-warroom-accent/20 text-warroom-accent px-4 py-2 rounded-lg hover:bg-warroom-accent/30 transition text-sm disabled:opacity-50"
                  >
                    <Play size={14} />
                    Run Again
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
