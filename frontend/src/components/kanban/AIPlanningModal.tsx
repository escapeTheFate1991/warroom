"use client";

import { useState } from "react";
import { X, Brain, ChevronRight, Check, Loader2, RefreshCw, AlertTriangle } from "lucide-react";
import { API, authFetch } from "@/lib/api";


interface PlanTask {
  title: string;
  description: string;
  priority: string;
  category: string;
  tags: string[];
  execution_order: number;
  depends_on_title: string | null;
  estimated_hours: number | null;
}

interface PlanAnalysis {
  project_type: string;
  key_challenges: string[];
  success_metrics: string[];
}

interface Plan {
  plan_id: string;
  tasks: PlanTask[];
  analysis: PlanAnalysis;
}

type Phase = "input" | "generating" | "review" | "creating" | "done";

const PRIORITY_COLORS: Record<string, string> = {
  critical: "bg-red-500/20 text-red-400 border-red-500/30",
  high: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  medium: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  low: "bg-blue-500/20 text-blue-400 border-blue-500/30",
};

const CATEGORY_COLORS: Record<string, string> = {
  backend: "bg-emerald-500/20 text-emerald-400",
  frontend: "bg-purple-500/20 text-purple-400",
  devops: "bg-cyan-500/20 text-cyan-400",
  design: "bg-pink-500/20 text-pink-400",
  research: "bg-amber-500/20 text-amber-400",
  testing: "bg-lime-500/20 text-lime-400",
  documentation: "bg-slate-500/20 text-slate-400",
};

interface AIPlanningModalProps {
  onClose: () => void;
  onTasksCreated: () => void;
}

export default function AIPlanningModal({ onClose, onTasksCreated }: AIPlanningModalProps) {
  const [phase, setPhase] = useState<Phase>("input");
  const [description, setDescription] = useState("");
  const [plan, setPlan] = useState<Plan | null>(null);
  const [selectedTasks, setSelectedTasks] = useState<Set<number>>(new Set());
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [error, setError] = useState<string | null>(null);

  const generatePlan = async () => {
    if (!description.trim()) return;
    setPhase("generating");
    setError(null);

    try {
      const resp = await authFetch(`${API}/api/ai-planning/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: description.trim() }),
      });

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.detail || `Failed to generate plan (${resp.status})`);
      }

      const data: Plan = await resp.json();
      setPlan(data);
      setSelectedTasks(new Set(data.tasks.map((_, i) => i)));
      setPhase("review");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to generate plan");
      setPhase("input");
    }
  };

  const executePlan = async () => {
    if (!plan) return;
    const indices = Array.from(selectedTasks).sort((a, b) => a - b);
    if (indices.length === 0) return;

    setPhase("creating");
    setProgress({ current: 0, total: indices.length });

    try {
      const resp = await authFetch(`${API}/api/ai-planning/plans/${plan.plan_id}/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ selected_task_indices: indices }),
      });

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to create tasks");
      }

      const result = await resp.json();
      setProgress({ current: result.created_task_ids.length, total: indices.length });
      setPhase("done");

      // Refresh the board after a short delay
      setTimeout(() => {
        onTasksCreated();
        onClose();
      }, 1500);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create tasks");
      setPhase("review");
    }
  };

  const toggleTask = (index: number) => {
    setSelectedTasks((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  const toggleAll = () => {
    if (!plan) return;
    if (selectedTasks.size === plan.tasks.length) {
      setSelectedTasks(new Set());
    } else {
      setSelectedTasks(new Set(plan.tasks.map((_, i) => i)));
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-warroom-surface border border-warroom-border rounded-xl w-full max-w-3xl mx-4 max-h-[85vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-warroom-border">
          <div className="flex items-center gap-2">
            <Brain size={20} className="text-warroom-accent" />
            <h2 className="text-base font-semibold text-warroom-text">AI Project Planner</h2>
          </div>
          <button onClick={onClose} className="text-warroom-muted hover:text-warroom-text transition p-1">
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Error banner */}
          {error && (
            <div className="mb-4 flex items-center gap-2 bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-2.5 rounded-lg text-sm">
              <AlertTriangle size={16} />
              {error}
            </div>
          )}

          {/* INPUT PHASE */}
          {(phase === "input" || phase === "generating") && (
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-warroom-muted block mb-2">
                  Describe your project
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. Build a user authentication system with OAuth2, JWT tokens, password reset flow, and role-based access control..."
                  className="w-full h-40 bg-warroom-bg border border-warroom-border rounded-lg p-4 text-sm text-warroom-text placeholder:text-warroom-muted/50 resize-none focus:outline-none focus:border-warroom-accent/50 transition"
                  disabled={phase === "generating"}
                />
              </div>
              <div className="flex justify-end">
                <button
                  onClick={generatePlan}
                  disabled={!description.trim() || phase === "generating"}
                  className="flex items-center gap-2 bg-warroom-accent text-black font-medium px-5 py-2.5 rounded-lg hover:bg-warroom-accent/90 transition disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {phase === "generating" ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      Generating Plan...
                    </>
                  ) : (
                    <>
                      <Brain size={16} />
                      Generate Plan
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* REVIEW PHASE */}
          {phase === "review" && plan && (
            <div className="space-y-6">
              {/* Analysis Card */}
              <div className="bg-warroom-bg border border-warroom-border rounded-lg p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-warroom-accent">
                    Project Analysis
                  </span>
                  <span className="text-xs bg-warroom-accent/20 text-warroom-accent px-2 py-0.5 rounded-full">
                    {plan.analysis.project_type}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs font-medium text-warroom-muted mb-1">Key Challenges</p>
                    <ul className="space-y-1">
                      {plan.analysis.key_challenges.map((c, i) => (
                        <li key={i} className="text-xs text-warroom-text flex items-start gap-1.5">
                          <AlertTriangle size={10} className="text-warroom-warning mt-0.5 shrink-0" />
                          {c}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-warroom-muted mb-1">Success Metrics</p>
                    <ul className="space-y-1">
                      {plan.analysis.success_metrics.map((m, i) => (
                        <li key={i} className="text-xs text-warroom-text flex items-start gap-1.5">
                          <Check size={10} className="text-warroom-success mt-0.5 shrink-0" />
                          {m}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>

              {/* Task List */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-warroom-muted">
                    Tasks ({selectedTasks.size}/{plan.tasks.length} selected)
                  </span>
                  <button
                    onClick={toggleAll}
                    className="text-xs text-warroom-accent hover:text-warroom-accent/80 transition"
                  >
                    {selectedTasks.size === plan.tasks.length ? "Deselect All" : "Select All"}
                  </button>
                </div>

                <div className="space-y-2">
                  {plan.tasks.map((task, i) => (
                    <div
                      key={i}
                      onClick={() => toggleTask(i)}
                      className={`bg-warroom-bg border rounded-lg p-3 cursor-pointer transition ${
                        selectedTasks.has(i)
                          ? "border-warroom-accent/40 bg-warroom-accent/5"
                          : "border-warroom-border opacity-50"
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        {/* Checkbox */}
                        <div
                          className={`mt-0.5 w-4 h-4 rounded border flex items-center justify-center shrink-0 transition ${
                            selectedTasks.has(i)
                              ? "bg-warroom-accent border-warroom-accent"
                              : "border-warroom-border"
                          }`}
                        >
                          {selectedTasks.has(i) && <Check size={10} className="text-black" />}
                        </div>

                        {/* Order number */}
                        <div className="w-6 h-6 rounded-full bg-warroom-border/50 flex items-center justify-center shrink-0">
                          <span className="text-[10px] font-bold text-warroom-muted">
                            {task.execution_order}
                          </span>
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-warroom-text">{task.title}</p>
                          <p className="text-xs text-warroom-muted mt-0.5 line-clamp-2">
                            {task.description}
                          </p>
                          <div className="flex items-center gap-2 mt-2 flex-wrap">
                            <span
                              className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium border ${
                                PRIORITY_COLORS[task.priority] || ""
                              }`}
                            >
                              {task.priority}
                            </span>
                            <span
                              className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                                CATEGORY_COLORS[task.category] || "bg-warroom-border/50 text-warroom-muted"
                              }`}
                            >
                              {task.category}
                            </span>
                            {task.estimated_hours && (
                              <span className="text-[10px] text-warroom-muted">
                                ~{task.estimated_hours}h
                              </span>
                            )}
                            {task.depends_on_title && (
                              <span className="text-[10px] text-warroom-muted flex items-center gap-0.5">
                                <ChevronRight size={8} />
                                depends on: {task.depends_on_title}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* CREATING PHASE */}
          {phase === "creating" && (
            <div className="flex flex-col items-center justify-center py-12 space-y-4">
              <Loader2 size={40} className="text-warroom-accent animate-spin" />
              <p className="text-sm text-warroom-muted">
                Creating tasks on the board...
              </p>
              <div className="w-48 bg-warroom-border/30 rounded-full h-1.5">
                <div
                  className="bg-warroom-accent h-1.5 rounded-full transition-all"
                  style={{ width: progress.total ? `${(progress.current / progress.total) * 100}%` : "0%" }}
                />
              </div>
            </div>
          )}

          {/* DONE PHASE */}
          {phase === "done" && (
            <div className="flex flex-col items-center justify-center py-12 space-y-3">
              <div className="w-12 h-12 rounded-full bg-warroom-success/20 flex items-center justify-center">
                <Check size={24} className="text-warroom-success" />
              </div>
              <p className="text-sm font-medium text-warroom-text">
                {progress.current} task{progress.current !== 1 ? "s" : ""} created!
              </p>
              <p className="text-xs text-warroom-muted">Refreshing board...</p>
            </div>
          )}
        </div>

        {/* Footer — only in review phase */}
        {phase === "review" && plan && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-warroom-border">
            <button
              onClick={() => {
                setPhase("input");
                setPlan(null);
                setError(null);
              }}
              className="flex items-center gap-1.5 text-sm text-warroom-muted hover:text-warroom-text transition"
            >
              <RefreshCw size={14} />
              Regenerate
            </button>
            <div className="flex items-center gap-3">
              <button
                onClick={onClose}
                className="text-sm text-warroom-muted hover:text-warroom-text transition px-4 py-2"
              >
                Cancel
              </button>
              <button
                onClick={executePlan}
                disabled={selectedTasks.size === 0}
                className="flex items-center gap-2 bg-warroom-accent text-black font-medium px-5 py-2 rounded-lg hover:bg-warroom-accent/90 transition disabled:opacity-40 disabled:cursor-not-allowed text-sm"
              >
                <Check size={14} />
                Create {selectedTasks.size} Task{selectedTasks.size !== 1 ? "s" : ""}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
