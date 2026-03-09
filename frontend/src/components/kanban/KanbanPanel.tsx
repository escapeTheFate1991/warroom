"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Plus, GripVertical, CheckCircle2, Circle, Clock, Archive, Trash2, X, Lock, CheckCheck, Link, Unlink, Brain, Play, Save, Edit3, Eye, Tag, Paperclip, Calendar, User, Hash, Bot } from "lucide-react";
import AIPlanningModal from "./AIPlanningModal";
import BoardExecutionModal from "./BoardExecutionModal";
import EntityAssignmentControl from "@/components/agents/EntityAssignmentControl";
import type { AgentAssignmentSummary } from "@/lib/agentAssignments";
import { API, authFetch } from "@/lib/api";


interface Task {
  id: number;
  title: string;
  description: string;
  status: string;
  assignee: string;
  priority: string;
  tags: string[];
  created_at: string;
  updated_at?: string;
  completed_at: string | null;
  agent_assignments?: AgentAssignmentSummary[];
}

interface DepEntry {
  id: number;
  task_id: number;
}

interface TaskDeps {
  depends_on: DepEntry[];
  blocks: DepEntry[];
}

const COLUMNS = [
  { id: "backlog", label: "Backlog", icon: Archive, color: "text-warroom-muted", borderColor: "border-t-gray-500" },
  { id: "todo", label: "To Do", icon: Circle, color: "text-warroom-warning", borderColor: "border-t-yellow-500" },
  { id: "in-progress", label: "In Progress", icon: Clock, color: "text-warroom-accent", borderColor: "border-t-blue-500" },
  { id: "done", label: "Done", icon: CheckCircle2, color: "text-warroom-success", borderColor: "border-t-green-500" },
];

const PRIORITY_COLORS: Record<string, string> = {
  critical: "bg-red-500/20 text-red-400",
  high: "bg-orange-500/20 text-orange-400",
  medium: "bg-yellow-500/20 text-yellow-400",
  low: "bg-blue-500/20 text-blue-400",
};

const PRIORITY_BORDER_COLORS: Record<string, string> = {
  critical: "border-l-red-500",
  high: "border-l-orange-500",
  medium: "border-l-yellow-500",
  low: "border-l-blue-500",
};

const PRIORITY_OPTIONS = ["low", "medium", "high", "critical"];
const STATUS_OPTIONS = COLUMNS.map((c) => c.id);
const EMPTY_ASSIGNMENTS: AgentAssignmentSummary[] = [];

export default function KanbanPanel() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [draggedTask, setDraggedTask] = useState<number | null>(null);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [mouseDownPosition, setMouseDownPosition] = useState<{ x: number; y: number } | null>(null);
  const [showAIPlanning, setShowAIPlanning] = useState(false);
  const [showExecution, setShowExecution] = useState(false);
  const [showNewTask, setShowNewTask] = useState(false);

  // Edit state for task detail
  const [editMode, setEditMode] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [editPriority, setEditPriority] = useState("medium");
  const [editStatus, setEditStatus] = useState("todo");
  const [editAssignee, setEditAssignee] = useState("friday");
  const [editTags, setEditTags] = useState<string[]>([]);
  const [newTagInput, setNewTagInput] = useState("");
  const [saving, setSaving] = useState(false);

  // New task state
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newPriority, setNewPriority] = useState("medium");
  const [newStatus, setNewStatus] = useState("todo");
  const [newAssignee, setNewAssignee] = useState("friday");
  const [newTags, setNewTags] = useState<string[]>([]);
  const [newTagText, setNewTagText] = useState("");
  const [creating, setCreating] = useState(false);

  // Dependency state
  const [allDeps, setAllDeps] = useState<Record<number, TaskDeps>>({});
  const [selectedTaskDeps, setSelectedTaskDeps] = useState<TaskDeps | null>(null);
  const [addingDep, setAddingDep] = useState(false);
  const [depDropdownValue, setDepDropdownValue] = useState<number | "">("");
  const [taskAssignments, setTaskAssignments] = useState<Record<number, AgentAssignmentSummary[]>>({});

  const fetchTasks = useCallback(async () => {
    try {
      const resp = await authFetch(`${API}/api/kanban/tasks`);
      const data = await resp.json();
      const nextTasks = Array.isArray(data) ? data : data.tasks || [];
      setTasks(nextTasks);
      setSelectedTask((current) => current ? nextTasks.find((task: Task) => task.id === current.id) ?? current : current);
    } catch {
      console.error("Failed to fetch tasks");
    }
  }, []);

  const fetchTaskAssignments = useCallback(async () => {
    try {
      const resp = await authFetch(`${API}/api/agents/assignments?entity_type=kanban_task&limit=500`);
      if (!resp.ok) return;
      const data = (await resp.json()) as AgentAssignmentSummary[];
      const grouped = data.reduce<Record<number, AgentAssignmentSummary[]>>((acc, assignment) => {
        const taskId = Number(assignment.entity_id);
        if (!Number.isNaN(taskId)) {
          acc[taskId] = [...(acc[taskId] || []), assignment];
        }
        return acc;
      }, {});
      setTaskAssignments(grouped);
    } catch {
      console.error("Failed to fetch task assignments");
    }
  }, []);

  const fetchAllDeps = useCallback(async (taskList: Task[]) => {
    // Fetch deps for all tasks in parallel for card indicators
    const depsMap: Record<number, TaskDeps> = {};
    await Promise.all(
      taskList.map(async (t) => {
        try {
          const resp = await authFetch(`${API}/api/tasks/${t.id}/dependencies`);
          if (resp.ok) {
            depsMap[t.id] = await resp.json();
          }
        } catch { /* ignore */ }
      })
    );
    setAllDeps(depsMap);
  }, []);

  useEffect(() => {
    fetchTasks();
    fetchTaskAssignments();
  }, [fetchTaskAssignments, fetchTasks]);

  // Refresh deps whenever tasks change
  useEffect(() => {
    if (tasks.length > 0) fetchAllDeps(tasks);
  }, [tasks, fetchAllDeps]);

  const fetchSelectedDeps = useCallback(async (taskId: number) => {
    try {
      const resp = await authFetch(`${API}/api/tasks/${taskId}/dependencies`);
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

  // ── Create Task ──
  const createTask = async () => {
    if (!newTitle.trim()) return;
    setCreating(true);
    try {
      await authFetch(`${API}/api/kanban/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: newTitle.trim(),
          description: newDesc.trim(),
          priority: newPriority,
          status: newStatus,
          assignee: newAssignee,
          tags: newTags,
        }),
      });
      setShowNewTask(false);
      setNewTitle(""); setNewDesc(""); setNewPriority("medium"); setNewStatus("todo"); setNewAssignee("friday"); setNewTags([]); setNewTagText("");
      fetchTasks();
    } catch { console.error("Failed to create task"); }
    setCreating(false);
  };

  // ── Edit helpers ──
  const enterEditMode = () => {
    if (!selectedTask) return;
    setEditTitle(selectedTask.title);
    setEditDesc(selectedTask.description || "");
    setEditPriority(selectedTask.priority);
    setEditStatus(selectedTask.status);
    setEditAssignee(selectedTask.assignee);
    setEditTags([...(selectedTask.tags || [])]);
    setEditMode(true);
  };

  const saveTask = async () => {
    if (!selectedTask || !editTitle.trim()) return;
    setSaving(true);
    try {
      const resp = await authFetch(`${API}/api/kanban/tasks/${selectedTask.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: editTitle.trim(),
          description: editDesc.trim(),
          priority: editPriority,
          status: editStatus,
          assignee: editAssignee,
          tags: editTags,
        }),
      });
      if (resp.ok) {
        const updated = await resp.json();
        setSelectedTask(updated);
        setEditMode(false);
        fetchTasks();
      }
    } catch { console.error("Failed to save task"); }
    setSaving(false);
  };

  const addEditTag = () => {
    const t = newTagInput.trim();
    if (t && !editTags.includes(t)) { setEditTags([...editTags, t]); setNewTagInput(""); }
  };

  const updateTaskStatus = async (taskId: number, newStatus: string) => {
    await authFetch(`${API}/api/kanban/tasks/${taskId}`, {
      method: "PUT",
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
      await authFetch(`${API}/api/kanban/tasks/${taskId}`, { method: "DELETE" });
      authFetch(`${API}/api/kanban/tasks/${taskId}/agent`, { method: "DELETE" }).catch(() => {});
      fetchTasks();
      if (selectedTask?.id === taskId) setSelectedTask(null);
    } catch {
      console.error("Failed to delete task");
    }
  };

  const addDependency = async (taskId: number, dependsOn: number) => {
    try {
      const resp = await authFetch(`${API}/api/tasks/${taskId}/dependencies`, {
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
      await authFetch(`${API}/api/tasks/${taskId}/dependencies/${depRowId}`, { method: "DELETE" });
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
  const getTaskAssignments = (task: Task) => taskAssignments[task.id] ?? task.agent_assignments ?? EMPTY_ASSIGNMENTS;

  const handleTaskAssignmentsChange = useCallback((taskId: number, assignments: AgentAssignmentSummary[]) => {
    setTaskAssignments((prev) => ({ ...prev, [taskId]: assignments }));
    setTasks((prev) => prev.map((task) => task.id === taskId ? { ...task, agent_assignments: assignments } : task));
    setSelectedTask((prev) => prev && prev.id === taskId ? { ...prev, agent_assignments: assignments } : prev);
  }, []);

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
          <button
            onClick={() => setShowNewTask(true)}
            className="flex items-center gap-1.5 text-xs bg-warroom-accent/20 text-warroom-accent px-3 py-1.5 rounded-lg hover:bg-warroom-accent/30 transition"
          >
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
                className={`w-72 flex flex-col bg-warroom-bg/30 border border-warroom-border rounded-lg border-t-2 ${col.borderColor} min-h-[200px]`}
                onDragOver={(e) => e.preventDefault()}
                onDrop={() => handleDrop(col.id)}
              >
                <div className="p-3 border-b border-warroom-border">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Icon size={14} className={col.color} />
                      <span className="text-sm font-bold text-warroom-text">
                        {col.label}
                      </span>
                    </div>
                    <span className="text-xs bg-warroom-bg px-2 py-0.5 rounded-full text-warroom-muted">{columnTasks.length}</span>
                  </div>
                </div>
                <div className="flex-1 space-y-2 overflow-y-auto p-2">
                  {columnTasks.map((task) => {
                    const unmet = hasUnmetDeps(task.id);
                    const ready = allDepsMet(task.id);
                    const assignments = getTaskAssignments(task);
                    return (
                      <div
                        key={task.id}
                        draggable
                        onDragStart={() => setDraggedTask(task.id)}
                        onMouseDown={(e) => handleMouseDown(e, task)}
                        onMouseUp={(e) => handleMouseUp(e, task)}
                        className={`bg-warroom-surface border border-warroom-border rounded-xl p-4 cursor-grab active:cursor-grabbing hover:border-warroom-accent/40 hover:shadow-lg hover:shadow-black/10 transition-all group border-l-2 ${PRIORITY_BORDER_COLORS[task.priority] || "border-l-transparent"}`}
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
                              {assignments.length > 0 && (
                                <span title={`${assignments.length} AI assignment${assignments.length === 1 ? "" : "s"}`} className="flex items-center gap-1 rounded-full bg-warroom-accent/15 px-1.5 py-0.5 text-[10px] text-warroom-accent">
                                  <Bot size={10} />
                                  {assignments.length}
                                </span>
                              )}
                              <p className="text-sm font-semibold truncate">{task.title}</p>
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

      {/* ══════ New Task Modal ══════ */}
      {showNewTask && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowNewTask(false)}>
          <div className="bg-warroom-surface border border-warroom-border rounded-xl p-0 max-w-xl w-full mx-4 max-h-[85vh] overflow-hidden shadow-2xl shadow-black/40" onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-warroom-border">
              <h3 className="text-base font-semibold flex items-center gap-2"><Plus size={16} className="text-warroom-accent" /> New Task</h3>
              <button onClick={() => setShowNewTask(false)} className="text-warroom-muted hover:text-warroom-text transition p-1"><X size={18} /></button>
            </div>

            <div className="p-5 space-y-4 overflow-y-auto max-h-[calc(85vh-130px)] scrollbar-thin scrollbar-thumb-warroom-border">
              {/* Title */}
              <div>
                <label className="text-xs font-medium text-warroom-muted uppercase tracking-wider block mb-1.5">Title *</label>
                <input value={newTitle} onChange={(e) => setNewTitle(e.target.value)} placeholder="Task title…"
                  className="w-full text-sm bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2.5 text-warroom-text focus:border-warroom-accent outline-none transition"
                  autoFocus onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && createTask()} />
              </div>

              {/* Description */}
              <div>
                <label className="text-xs font-medium text-warroom-muted uppercase tracking-wider block mb-1.5">Description</label>
                <textarea value={newDesc} onChange={(e) => setNewDesc(e.target.value)} placeholder="Describe the task… (Markdown supported)"
                  rows={4} className="w-full text-sm bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2.5 text-warroom-text focus:border-warroom-accent outline-none transition resize-y" />
              </div>

              {/* Row: Status + Priority + Assignee */}
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs font-medium text-warroom-muted uppercase tracking-wider block mb-1.5">Status</label>
                  <select value={newStatus} onChange={(e) => setNewStatus(e.target.value)}
                    className="w-full text-sm bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2.5 text-warroom-text focus:border-warroom-accent outline-none">
                    {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s.replace("-", " ")}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-warroom-muted uppercase tracking-wider block mb-1.5">Priority</label>
                  <select value={newPriority} onChange={(e) => setNewPriority(e.target.value)}
                    className="w-full text-sm bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2.5 text-warroom-text focus:border-warroom-accent outline-none">
                    {PRIORITY_OPTIONS.map((p) => <option key={p} value={p}>{p}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-warroom-muted uppercase tracking-wider block mb-1.5">Assignee</label>
                  <input value={newAssignee} onChange={(e) => setNewAssignee(e.target.value)} placeholder="friday"
                    className="w-full text-sm bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2.5 text-warroom-text focus:border-warroom-accent outline-none" />
                </div>
              </div>

              {/* Tags */}
              <div>
                <label className="text-xs font-medium text-warroom-muted uppercase tracking-wider block mb-1.5">Tags</label>
                <div className="flex flex-wrap gap-1.5 mb-2">
                  {newTags.map((tag, i) => (
                    <span key={i} className="text-xs bg-warroom-accent/20 text-warroom-accent px-2 py-0.5 rounded-full flex items-center gap-1">
                      {tag}
                      <button onClick={() => setNewTags(newTags.filter((_, j) => j !== i))} className="hover:text-red-400"><X size={10} /></button>
                    </span>
                  ))}
                </div>
                <div className="flex gap-2">
                  <input value={newTagText} onChange={(e) => setNewTagText(e.target.value)} placeholder="Add tag…"
                    className="flex-1 text-sm bg-warroom-bg border border-warroom-border rounded-lg px-3 py-1.5 text-warroom-text focus:border-warroom-accent outline-none"
                    onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); const t = newTagText.trim(); if (t && !newTags.includes(t)) { setNewTags([...newTags, t]); setNewTagText(""); }}}} />
                  <button onClick={() => { const t = newTagText.trim(); if (t && !newTags.includes(t)) { setNewTags([...newTags, t]); setNewTagText(""); }}}
                    className="text-xs bg-warroom-border/50 text-warroom-muted px-3 py-1.5 rounded-lg hover:bg-warroom-border transition">Add</button>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 px-5 py-4 border-t border-warroom-border">
              <button onClick={() => setShowNewTask(false)} className="text-xs text-warroom-muted hover:text-warroom-text px-3 py-2 transition">Cancel</button>
              <button onClick={createTask} disabled={!newTitle.trim() || creating}
                className="flex items-center gap-1.5 text-xs bg-warroom-accent text-white px-4 py-2 rounded-lg hover:bg-warroom-accent/90 transition disabled:opacity-40 disabled:cursor-not-allowed">
                {creating ? "Creating…" : <><Plus size={14} /> Create Task</>}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ══════ Task Detail Modal (View + Edit) ══════ */}
      {selectedTask && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => { setSelectedTask(null); setEditMode(false); }}>
          <div className="bg-warroom-surface border border-warroom-border rounded-xl p-0 max-w-xl w-full mx-4 max-h-[85vh] overflow-hidden shadow-2xl shadow-black/40" onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-warroom-border">
              {editMode ? (
                <input value={editTitle} onChange={(e) => setEditTitle(e.target.value)}
                  className="text-base font-semibold bg-warroom-bg border border-warroom-border rounded-lg px-3 py-1.5 text-warroom-text focus:border-warroom-accent outline-none flex-1 mr-3" />
              ) : (
                <h3 className="text-base font-semibold flex-1 mr-3 truncate">{selectedTask.title}</h3>
              )}
              <div className="flex items-center gap-1">
                {!editMode ? (
                  <button onClick={enterEditMode} className="text-warroom-muted hover:text-warroom-accent transition p-1.5 rounded-lg hover:bg-warroom-accent/10" title="Edit task">
                    <Edit3 size={16} />
                  </button>
                ) : (
                  <button onClick={saveTask} disabled={saving || !editTitle.trim()} className="text-warroom-accent hover:text-warroom-accent/80 transition p-1.5 rounded-lg hover:bg-warroom-accent/10 disabled:opacity-40" title="Save">
                    <Save size={16} />
                  </button>
                )}
                <button onClick={() => { setSelectedTask(null); setEditMode(false); }} className="text-warroom-muted hover:text-warroom-text transition p-1.5"><X size={18} /></button>
              </div>
            </div>

            <div className="p-5 space-y-4 overflow-y-auto max-h-[calc(85vh-130px)] scrollbar-thin scrollbar-thumb-warroom-border">
              {/* Description */}
              <div>
                <label className="text-xs font-medium text-warroom-muted uppercase tracking-wider block mb-1.5">Description</label>
                {editMode ? (
                  <textarea value={editDesc} onChange={(e) => setEditDesc(e.target.value)} rows={5} placeholder="Describe the task… (Markdown supported)"
                    className="w-full text-sm bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2.5 text-warroom-text focus:border-warroom-accent outline-none transition resize-y" />
                ) : (
                  <div className="text-sm text-warroom-text whitespace-pre-wrap bg-warroom-bg/50 rounded-lg p-3 min-h-[60px]">
                    {selectedTask.description || <span className="text-warroom-muted italic">No description</span>}
                  </div>
                )}
              </div>

              {/* Row: Status + Priority + Assignee */}
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs font-medium text-warroom-muted uppercase tracking-wider block mb-1.5">Status</label>
                  {editMode ? (
                    <select value={editStatus} onChange={(e) => setEditStatus(e.target.value)}
                      className="w-full text-sm bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-warroom-text focus:border-warroom-accent outline-none">
                      {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s.replace("-", " ")}</option>)}
                    </select>
                  ) : (
                    <p className="text-sm text-warroom-text capitalize">{selectedTask.status.replace("-", " ")}</p>
                  )}
                </div>
                <div>
                  <label className="text-xs font-medium text-warroom-muted uppercase tracking-wider block mb-1.5">Priority</label>
                  {editMode ? (
                    <select value={editPriority} onChange={(e) => setEditPriority(e.target.value)}
                      className="w-full text-sm bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-warroom-text focus:border-warroom-accent outline-none">
                      {PRIORITY_OPTIONS.map((p) => <option key={p} value={p}>{p}</option>)}
                    </select>
                  ) : (
                    <span className={`inline-block text-xs px-2 py-1 rounded-full font-medium ${PRIORITY_COLORS[selectedTask.priority] || ""}`}>{selectedTask.priority}</span>
                  )}
                </div>
                <div>
                  <label className="text-xs font-medium text-warroom-muted uppercase tracking-wider block mb-1.5">Assignee</label>
                  {editMode ? (
                    <input value={editAssignee} onChange={(e) => setEditAssignee(e.target.value)}
                      className="w-full text-sm bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-warroom-text focus:border-warroom-accent outline-none" />
                  ) : (
                    <p className="text-sm text-warroom-text">{selectedTask.assignee}</p>
                  )}
                </div>
              </div>

              {/* Tags */}
              <div>
                <label className="text-xs font-medium text-warroom-muted uppercase tracking-wider block mb-1.5">Tags</label>
                {editMode ? (
                  <>
                    <div className="flex flex-wrap gap-1.5 mb-2">
                      {editTags.map((tag, i) => (
                        <span key={i} className="text-xs bg-warroom-accent/20 text-warroom-accent px-2 py-0.5 rounded-full flex items-center gap-1">
                          {tag}
                          <button onClick={() => setEditTags(editTags.filter((_, j) => j !== i))} className="hover:text-red-400"><X size={10} /></button>
                        </span>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <input value={newTagInput} onChange={(e) => setNewTagInput(e.target.value)} placeholder="Add tag…"
                        className="flex-1 text-sm bg-warroom-bg border border-warroom-border rounded-lg px-3 py-1.5 text-warroom-text focus:border-warroom-accent outline-none"
                        onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addEditTag(); }}} />
                      <button onClick={addEditTag} className="text-xs bg-warroom-border/50 text-warroom-muted px-3 py-1.5 rounded-lg hover:bg-warroom-border transition">Add</button>
                    </div>
                  </>
                ) : (
                  selectedTask.tags && selectedTask.tags.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {selectedTask.tags.map((tag, idx) => (
                        <span key={idx} className="text-xs bg-warroom-accent/20 text-warroom-accent px-2 py-0.5 rounded-full">{tag}</span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-warroom-muted italic">No tags</p>
                  )
                )}
              </div>

              {/* Metadata */}
              <div className="grid grid-cols-2 gap-3 text-xs text-warroom-muted">
                <div><Calendar size={12} className="inline mr-1" />Created: {formatDate(selectedTask.created_at)}</div>
                {selectedTask.completed_at && <div><CheckCircle2 size={12} className="inline mr-1" />Completed: {formatDate(selectedTask.completed_at)}</div>}
              </div>

              <EntityAssignmentControl
                entityType="kanban_task"
                entityId={selectedTask.id}
                title={selectedTask.title}
                initialAssignments={getTaskAssignments(selectedTask)}
                onAssignmentsChange={(assignments) => handleTaskAssignmentsChange(selectedTask.id, assignments)}
                emptyLabel="No AI agents assigned yet."
              />

              {/* ── Dependencies Section ── */}
              <div className="border-t border-warroom-border pt-4 mt-2">
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
                                <span className="flex-shrink-0">{isDone ? <CheckCheck size={12} className="text-green-400" /> : <Lock size={12} className="text-yellow-400" />}</span>
                                <button onClick={() => depTask && setSelectedTask(depTask)} className="text-xs text-warroom-accent hover:underline truncate text-left">
                                  {depTask ? depTask.title : `Task #${dep.task_id}`}
                                </button>
                                <button onClick={() => removeDependency(selectedTask!.id, dep.id)}
                                  className="opacity-0 group-hover/dep:opacity-100 text-warroom-muted hover:text-red-400 transition flex-shrink-0" title="Remove"><X size={12} /></button>
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
                                <button onClick={() => blockedTask && setSelectedTask(blockedTask)} className="text-xs text-warroom-accent hover:underline truncate text-left">
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
                      <button onClick={() => setAddingDep(true)} className="flex items-center gap-1.5 text-xs text-warroom-accent hover:text-warroom-accent/80 transition mt-1">
                        <Plus size={12} /> Add Dependency
                      </button>
                    ) : (
                      <div className="flex items-center gap-2 mt-1">
                        <select value={depDropdownValue} onChange={(e) => setDepDropdownValue(e.target.value ? Number(e.target.value) : "")}
                          className="flex-1 text-xs bg-warroom-bg border border-warroom-border rounded px-2 py-1.5 text-warroom-text focus:border-warroom-accent outline-none">
                          <option value="">Select task…</option>
                          {availableDepTargets.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
                        </select>
                        <button disabled={depDropdownValue === ""} onClick={() => { if (depDropdownValue !== "") addDependency(selectedTask!.id, depDropdownValue as number); }}
                          className="text-xs bg-warroom-accent/20 text-warroom-accent px-2.5 py-1.5 rounded hover:bg-warroom-accent/30 transition disabled:opacity-30 disabled:cursor-not-allowed">Add</button>
                        <button onClick={() => { setAddingDep(false); setDepDropdownValue(""); }} className="text-warroom-muted hover:text-warroom-text transition"><X size={14} /></button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between px-5 py-4 border-t border-warroom-border">
              <button onClick={() => deleteTask(selectedTask.id)} className="flex items-center gap-1.5 text-xs text-red-400 hover:text-red-300 hover:bg-red-400/10 px-3 py-2 rounded-lg transition">
                <Trash2 size={14} /> Delete
              </button>
              <div className="flex items-center gap-2">
                {editMode && (
                  <button onClick={() => setEditMode(false)} className="text-xs text-warroom-muted hover:text-warroom-text px-3 py-2 transition">Cancel</button>
                )}
                {editMode ? (
                  <button onClick={saveTask} disabled={saving || !editTitle.trim()}
                    className="flex items-center gap-1.5 text-xs bg-warroom-accent text-white px-4 py-2 rounded-lg hover:bg-warroom-accent/90 transition disabled:opacity-40">
                    {saving ? "Saving…" : <><Save size={14} /> Save Changes</>}
                  </button>
                ) : (
                  <button onClick={enterEditMode}
                    className="flex items-center gap-1.5 text-xs bg-warroom-accent/20 text-warroom-accent px-4 py-2 rounded-lg hover:bg-warroom-accent/30 transition">
                    <Edit3 size={14} /> Edit
                  </button>
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
