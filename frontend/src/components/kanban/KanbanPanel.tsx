"use client";

import { useState, useEffect, useCallback } from "react";
import { Plus, GripVertical, CheckCircle2, Circle, Clock, Archive, Trash2, X } from "lucide-react";

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

  const fetchTasks = useCallback(async () => {
    try {
      const resp = await fetch(`${API}/api/kanban/tasks`);
      const data = await resp.json();
      // Handle both {tasks: [...]} and [...] formats
      setTasks(Array.isArray(data) ? data : data.tasks || []);
    } catch {
      console.error("Failed to fetch tasks");
    }
  }, []);

  useEffect(() => { fetchTasks(); }, [fetchTasks]);

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
      // Stop any sub-agent assigned to this task
      fetch(`${API}/api/kanban/tasks/${taskId}/agent`, { method: "DELETE" }).catch(() => {});
      fetchTasks();
    } catch {
      console.error("Failed to delete task");
    }
  };

  const handleMouseDown = (e: React.MouseEvent, task: Task) => {
    setMouseDownPosition({ x: e.clientX, y: e.clientY });
  };

  const handleMouseUp = (e: React.MouseEvent, task: Task) => {
    if (!mouseDownPosition) return;
    
    const deltaX = Math.abs(e.clientX - mouseDownPosition.x);
    const deltaY = Math.abs(e.clientY - mouseDownPosition.y);
    
    // If mouse moved less than 5px, treat as click
    if (deltaX < 5 && deltaY < 5) {
      setSelectedTask(task);
    }
    
    setMouseDownPosition(null);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="flex flex-col h-full">
      <div className="h-14 border-b border-warroom-border flex items-center px-6 justify-between">
        <h2 className="text-sm font-semibold">Task Board</h2>
        <button className="flex items-center gap-1.5 text-xs bg-warroom-accent/20 text-warroom-accent px-3 py-1.5 rounded-lg hover:bg-warroom-accent/30 transition">
          <Plus size={14} /> New Task
        </button>
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
                  {columnTasks.map((task) => (
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
                          <p className="text-sm font-medium truncate">{task.title}</p>
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
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteTask(task.id);
                          }}
                          className="text-warroom-muted/30 hover:text-red-400 opacity-0 group-hover:opacity-100 transition p-1"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Task Detail Modal */}
      {selectedTask && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-warroom-surface border border-warroom-border rounded-lg p-6 max-w-md w-full mx-4 max-h-[80vh] overflow-y-auto">
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
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
