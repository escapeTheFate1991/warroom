"use client";

import { useState, useEffect, useCallback } from "react";
import { Plus, GripVertical, CheckCircle2, Circle, Clock, Archive, Trash2, X, Lock, CheckCheck, Link, Unlink, Brain, Play } from "lucide-react";
import AIPlanningModal from "./AIPlanningModal";
import BoardExecutionModal from "./BoardExecutionModal";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface Task {
  id: number;
  title: string;
  description: string;
  status: string;
  assignee: string;
  priority: string;
  tags: string[];
  created_at: string;
  completed_at: string | null;
}

interface DepEntry {
  id: number;     // row id in task_dependencies table
  task_id: number; // the referenced task id
}

interface TaskDeps {
  depends_on: DepEntry[];
  blocks: DepEntry[];
}

const COLUMNS = [
  { id: "backlog", label: "Backlog", icon: Archive, color: "text-warroom-muted" },
  { id: "todo", label: "To Do", icon: Circle, color: "text-warroom-warning" },
  { id: "in-progress", label: "In Progress", icon: Clock, color: "text-warroom-accent" },
  { id: "done", label: "Done", icon: CheckCircle2, color: "text-warroom-success" },
];

const PRIORITY_COLORS: Record<string, string> = {
  critical: "bg-red-500/20 text-red-400",
  high: "bg-orange-500/20 text-orange-400",
  medium: "bg-yellow-500/20 text-yellow-400",
  low: "bg-blue-500/20 text-blue-400",
};

export default function KanbanPanel() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [draggedTask, setDraggedTask] = useState<number | null>(null);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [mouseDownPosition, setMouseDownPosition] = useState<{ x: number; y: number } | null>(null);
  const [showAIPlanning, setShowAIPlanning] = useState(false);
  const [showExecution, setShowExecution] = useState(false);

  // Dependency state
  const [allDeps, setAllDeps] = useState<Record<number, TaskDeps>>({});
  const [selectedTaskDeps, setSelectedTaskDeps] = useState<TaskDeps | null>(null);
  const [addingDep, setAddingDep] = useState(false);
  const [depDropdownValue, setDepDropdownValue] = useState<number | "">("");

  const fetchTasks = useCallback(async () => {
    try {
      const resp = await fetch(`${API}/api/kanban/tasks`);
      const data = await resp.json();
      setTasks(Array.isArray(data) ? data : data.tasks || []);
    } catch {
      console.error("Failed to fetch tasks");
    }
  }, []);

  const fetchAllDeps = useCallback(async (taskList: Task[]) => {
    // Fetch deps for all tasks in parallel for card indicators
    const depsMap: Record<number, TaskDeps> = {};
    await Promise.all(
      taskList.map(async (t) => {
        try {
          const resp = await fetch(`${API}/api/tasks/${t.id}/dependencies`);
          if (resp.ok) {
            depsMap[t.id] = await resp.json();
          }
        } catch { /* ignore */ }
      })
    );
    setAllDeps(depsMap);
  }, []);

  useEffect(() => { fetchTasks(); }, [fetchTasks]);

  // Refresh deps whenever tasks change
  useEffect(() => {
    if (tasks.length > 0) fetchAllDeps(tasks);
  }, [tasks, fetchAllDeps]);

  const fetchSelectedDeps = useCallback(async (taskId: number) => {
    try {
      const resp = await fetch(`${API}/api/tasks/${taskId}/dependencies`);
      if (resp.ok) {
        setSelectedTaskDeps(await resp.json());
      }
    } catch {
      setSelectedTaskDeps(null);
    }
  }, []);

  // Fetch deps when a task is selected
  useEffect(() => {
    if (selectedTask) {
      fetchSelectedDeps(selectedTask.id);
      setAddingDep(false);
      setDepDropdownValue("");
    } else {
      setSelectedTaskDeps(null);
    }
  }, [selectedTask, fetchSelectedDeps]);

  const updateTaskStatus = async (taskId: number, newStatus: string) => {
    await fetch(`${API}/api/kanban/tasks/${taskId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus }),
    });
    fetchTasks();
  };

  const handleDrop = (status: string) => {
    if (draggedTask !== null) {
      updateTaskStatus(draggedTask, status);
      setDraggedTask(null);
    }
  };

  const deleteTask = async (taskId: number) => {
    if (!window.confirm("Are you sure you want to delete this task? This will also stop any agent working on it.")) return;
    try {
      await fetch(`${API}/api/kanban/tasks/${taskId}`, { method: "DELETE" });
      fetch(`${API}/api/kanban/tasks/${taskId}/agent`, { method: "DELETE" }).catch(() => {});
      fetchTasks();
      if (selectedTask?.id === taskId) setSelectedTask(null);
    } catch {
      console.error("Failed to delete task");
    }
  };

  const addDependency = async (taskId: number, dependsOn: number) => {
    try {
      const resp = await fetch(`${API}/api/tasks/${taskId}/dependencies`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ depends_on: dependsOn }),
      });
      if (!resp.ok) {
        const err = await resp.json();
        alert(err.detail || "Failed to add dependency");
        return;
      }
      fetchSelectedDeps(taskId);
      fetchAllDeps(tasks);
      setAddingDep(false);
      setDepDropdownValue("");
    } catch {
      alert("Failed to add dependency");
    }
  };

  const removeDependency = async (taskId: number, depRowId: number) => {
    try {
      await fetch(`${API}/api/tasks/${taskId}/dependencies/${depRowId}`, { method: "DELETE" });
      fetchSelectedDeps(taskId);
      fetchAllDeps(tasks);
    } catch {
      console.error("Failed to remove dependency");
    }
  };

  const handleMouseDown = (e: React.MouseEvent, task: Task) => {
    setMouseDownPosition({ x: e.clientX, y: e.clientY });
  };

  const handleMouseUp = (e: React.MouseEvent, task: Task) => {
    if (!mouseDownPosition) return;
    const deltaX = Math.abs(e.clientX - mouseDownPosition.x);
    const deltaY = Math.abs(e.clientY - mouseDownPosition.y);
    if (deltaX < 5 && deltaY < 5) {
      setSelectedTask(task);
    }
    setMouseDownPosition(null);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  };

  const taskById = (id: number) => tasks.find((t) => t.id === id);

  /** Check if a task has unmet dependencies (depends on tasks not in "done") */
  const hasUnmetDeps = (taskId: number): boolean => {
    const deps = allDeps[taskId];
    if (!deps || deps.depends_on.length === 0) return false;
    return deps.depends_on.some((d) => {
      const t = taskById(d.task_id);
      return !t || t.status !== "done";
    });
  };

  /** Check if all dependencies are met */
  const allDepsMet = (taskId: number): boolean => {
    const deps = allDeps[taskId];
    if (!deps || deps.depends_on.length === 0) return false; // no deps = no indicator
    return deps.depends_on.every((d) => {
      const t = taskById(d.task_id);
      return t && t.status === "done";
    });
  };

  // Tasks available to add as a dependency (exclude self and already-depended-on)
  const availableDepTargets = selectedTask && selectedTaskDeps
    ? tasks.filter((t) => {
        if (t.id === selectedTask.id) return false;
        if (selectedTaskDeps.depends_on.some((d) => d.task_id === t.id)) return false;
        return true;
      })
    : [];

  return (
    <div className="flex flex-col h-full">
      <div className="h-14 border-b border-warroom-border flex items-center px-6 justify-between">
        <h2 className="text-sm font-semibold">Task Board</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowExecution(true)}
            className="flex items-center gap-1.5 text-xs bg-green-500/20 text-green-400 px-3 py-1.5 rounded-lg hover:bg-green-500/30 transition"
          >
            <Play size={14} /> Execute
          </button>
          <button
            onClick={() => setShowAIPlanning(true)}
            className="flex items-center gap-1.5 text-xs bg-purple-500/20 text-purple-400 px-3 py-1.5 rounded-lg hover:bg-purple-500/30 transition"
          >
            <Brain size={14} /> AI Plan
          </button>
          <button className="flex items-center gap-1.5 text-xs bg-warroom-accent/20 text-warroom-accent px-3 py-1.5 rounded-lg hover:bg-warroom-accent/30 transition">
            <Plus size={14} /> New Task
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-x-auto p-4">
        <div className="flex gap-4 h-full min-w-max">
          {COLUMNS.map((col) => {
            const Icon = col.icon;
            const columnTasks = tasks.filter((t) => t.status === col.id);
            return (
              <div
                key={col.id}
                className="w-72 flex flex-col"
                onDragOver={(e) => e.preventDefault()}
                onDrop={() => handleDrop(col.id)}
              >
                <div className="flex items-center gap-2 mb-3 px-1">
                  <Icon size={16} className={col.color} />
                  <span className="text-xs font-semibold uppercase tracking-wider text-warroom-muted">
                    {col.label}
                  </span>
                  <span className="text-xs text-warroom-muted/50 ml-auto">{columnTasks.length}</span>
                </div>
                <div className="flex-1 space-y-2 overflow-y-auto">
                  {columnTasks.map((task) => {
                    const unmet = hasUnmetDeps(task.id);
                    const ready = allDepsMet(task.id);
                    return (
                      <div
                        key={task.id}
                        draggable
                        onDragStart={() => setDraggedTask(task.id)}
                        onMouseDown={(e) => handleMouseDown(e, task)}
                        onMouseUp={(e) => handleMouseUp(e, task)}
                        className="bg-warroom-surface border border-warroom-border rounded-lg p-3 cursor-grab active:cursor-grabbing hover:border-warroom-accent/30 transition group"
                      >
                        <div className="flex items-start gap-2">
                          <GripVertical size={14} className="text-warroom-muted/30 mt-0.5 opacity-0 group-hover:opacity-100 transition" />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5">
                              {unmet && (
                                <span title="Has unmet dependencies" className="flex-shrink-0">
                                  <Lock size={12} className="text-yellow-400" />
                                </span>
                              )}
                              {ready && (
                                <span title="All dependencies met" className="flex-shrink-0">
                                  <CheckCheck size={12} className="text-green-400" />
                                </span>
                              )}
                              <p className="text-sm font-medium truncate">{task.title}</p>
                            </div>
                            {task.description && (
                              <p className="text-xs text-warroom-muted mt-1 line-clamp-2">{task.description}</p>
                            )}
                            <div className="flex items-center gap-2 mt-2">
                              {task.priority && (
                                <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${PRIORITY_COLORS[task.priority] || ""}`}>
                                  {task.priority}
                                </span>
                              )}
                              <span className="text-[10px] text-warroom-muted">{task.assignee}</span>
                            </div>
                          </div>
                          <button
                            onClick={(e) => { e.stopPropagation(); deleteTask(task.id); }}
                            className="text-warroom-muted/30 hover:text-red-400 opacity-0 group-hover:opacity-100 transition p-1"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Task Detail Modal */}
      {selectedTask && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-warroom-surface border border-warroom-border rounded-lg p-6 max-w-lg w-full mx-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">{selectedTask.title}</h3>
              <button
                onClick={() => setSelectedTask(null)}
                className="text-warroom-muted hover:text-warroom-text transition p-1"
              >
                <X size={20} />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-warroom-muted uppercase tracking-wider block mb-1">Description</label>
                <p className="text-sm text-warroom-text">{selectedTask.description || "No description"}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-warroom-muted uppercase tracking-wider block mb-1">Status</label>
                  <p className="text-sm text-warroom-text capitalize">{selectedTask.status.replace("-", " ")}</p>
                </div>
                <div>
                  <label className="text-xs font-medium text-warroom-muted uppercase tracking-wider block mb-1">Assignee</label>
                  <p className="text-sm text-warroom-text">{selectedTask.assignee}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-warroom-muted uppercase tracking-wider block mb-1">Priority</label>
                  {selectedTask.priority && (
                    <span className={`inline-block text-xs px-2 py-1 rounded-full font-medium ${PRIORITY_COLORS[selectedTask.priority] || ""}`}>
                      {selectedTask.priority}
                    </span>
                  )}
                </div>
                <div>
                  <label className="text-xs font-medium text-warroom-muted uppercase tracking-wider block mb-1">Tags</label>
                  {selectedTask.tags && selectedTask.tags.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {selectedTask.tags.map((tag, idx) => (
                        <span key={idx} className="text-xs bg-warroom-accent/20 text-warroom-accent px-2 py-0.5 rounded">
                          {tag}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-warroom-muted">No tags</p>
                  )}
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-warroom-muted uppercase tracking-wider block mb-1">Created</label>
                <p className="text-sm text-warroom-text">{formatDate(selectedTask.created_at)}</p>
              </div>

              {selectedTask.completed_at && (
                <div>
                  <label className="text-xs font-medium text-warroom-muted uppercase tracking-wider block mb-1">Completed</label>
                  <p className="text-sm text-warroom-text">{formatDate(selectedTask.completed_at)}</p>
                </div>
              )}

              {/* ── Dependencies Section ── */}
              <div className="border-t border-warroom-border pt-4 mt-4">
                <div className="flex items-center gap-2 mb-3">
                  <Link size={14} className="text-warroom-accent" />
                  <label className="text-xs font-medium text-warroom-muted uppercase tracking-wider">Dependencies</label>
                </div>

                {selectedTaskDeps === null ? (
                  <p className="text-xs text-warroom-muted animate-pulse">Loading…</p>
                ) : (
                  <div className="space-y-3">
                    {/* Depends On */}
                    <div>
                      <p className="text-xs text-warroom-muted mb-1.5">Depends on:</p>
                      {selectedTaskDeps.depends_on.length === 0 ? (
                        <p className="text-xs text-warroom-muted/50 italic">None</p>
                      ) : (
                        <div className="space-y-1">
                          {selectedTaskDeps.depends_on.map((dep) => {
                            const depTask = taskById(dep.task_id);
                            const isDone = depTask?.status === "done";
                            return (
                              <div key={dep.id} className="flex items-center gap-2 group/dep">
                                <span className="flex-shrink-0">
                                  {isDone ? (
                                    <CheckCheck size={12} className="text-green-400" />
                                  ) : (
                                    <Lock size={12} className="text-yellow-400" />
                                  )}
                                </span>
                                <button
                                  onClick={() => depTask && setSelectedTask(depTask)}
                                  className="text-xs text-warroom-accent hover:underline truncate text-left"
                                >
                                  {depTask ? depTask.title : `Task #${dep.task_id}`}
                                </button>
                                <button
                                  onClick={() => removeDependency(selectedTask!.id, dep.id)}
                                  className="opacity-0 group-hover/dep:opacity-100 text-warroom-muted hover:text-red-400 transition flex-shrink-0"
                                  title="Remove dependency"
                                >
                                  <X size={12} />
                                </button>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>

                    {/* Blocks */}
                    <div>
                      <p className="text-xs text-warroom-muted mb-1.5">Blocks:</p>
                      {selectedTaskDeps.blocks.length === 0 ? (
                        <p className="text-xs text-warroom-muted/50 italic">None</p>
                      ) : (
                        <div className="space-y-1">
                          {selectedTaskDeps.blocks.map((dep) => {
                            const blockedTask = taskById(dep.task_id);
                            return (
                              <div key={dep.id} className="flex items-center gap-2">
                                <Unlink size={12} className="text-warroom-muted flex-shrink-0" />
                                <button
                                  onClick={() => blockedTask && setSelectedTask(blockedTask)}
                                  className="text-xs text-warroom-accent hover:underline truncate text-left"
                                >
                                  {blockedTask ? blockedTask.title : `Task #${dep.task_id}`}
                                </button>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>

                    {/* Add Dependency */}
                    {!addingDep ? (
                      <button
                        onClick={() => setAddingDep(true)}
                        className="flex items-center gap-1.5 text-xs text-warroom-accent hover:text-warroom-accent/80 transition mt-1"
                      >
                        <Plus size={12} /> Add Dependency
                      </button>
                    ) : (
                      <div className="flex items-center gap-2 mt-1">
                        <select
                          value={depDropdownValue}
                          onChange={(e) => setDepDropdownValue(e.target.value ? Number(e.target.value) : "")}
                          className="flex-1 text-xs bg-warroom-surface border border-warroom-border rounded px-2 py-1.5 text-warroom-text focus:border-warroom-accent outline-none"
                        >
                          <option value="">Select task…</option>
                          {availableDepTargets.map((t) => (
                            <option key={t.id} value={t.id}>
                              {t.title}
                            </option>
                          ))}
                        </select>
                        <button
                          disabled={depDropdownValue === ""}
                          onClick={() => {
                            if (depDropdownValue !== "") {
                              addDependency(selectedTask!.id, depDropdownValue as number);
                            }
                          }}
                          className="text-xs bg-warroom-accent/20 text-warroom-accent px-2.5 py-1.5 rounded hover:bg-warroom-accent/30 transition disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                          Add
                        </button>
                        <button
                          onClick={() => { setAddingDep(false); setDepDropdownValue(""); }}
                          className="text-warroom-muted hover:text-warroom-text transition"
                        >
                          <X size={14} />
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AI Planning Modal */}
      {showAIPlanning && (
        <AIPlanningModal
          onClose={() => setShowAIPlanning(false)}
          onTasksCreated={fetchTasks}
        />
      )}

      {/* Board Execution Modal */}
      {showExecution && (
        <BoardExecutionModal
          onClose={() => setShowExecution(false)}
          onComplete={() => {
            fetchTasks();
          }}
        />
      )}
    </div>
  );
}
