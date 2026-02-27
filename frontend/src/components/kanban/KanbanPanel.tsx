"use client";

import { useState, useEffect, useCallback } from "react";
import { Plus, GripVertical, CheckCircle2, Circle, Clock, Archive } from "lucide-react";

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
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
