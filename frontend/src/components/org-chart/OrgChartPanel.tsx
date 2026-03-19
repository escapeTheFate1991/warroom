"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { 
  Users, 
  Bot, 
  Plus, 
  Edit, 
  Trash2, 
  Target, 
  ChevronRight,
  Building2,
  Crown,
  Shield,
  UserCircle,
  Briefcase,
  List,
  Network
} from "lucide-react";
import { authFetch, API } from "../../lib/api";

// ── Types ────────────────────────────────────────────────────

interface OrgMember {
  id: number;
  org_id: number;
  member_type: "human" | "agent";
  agent_id?: number;
  user_id?: number;
  name: string;
  title?: string;
  department?: string;
  reports_to_id?: number;
  role: "ceo" | "director" | "manager" | "employee" | "contractor";
  skills: string[];
  budget_allocation: number;
  status: "active" | "onboarding" | "offboarded";
  hired_at: string;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

interface Goal {
  id: number;
  org_id: number;
  parent_goal_id?: number;
  title: string;
  description?: string;
  goal_type: "mission" | "department" | "project" | "task";
  owner_member_id?: number;
  status: "active" | "paused" | "completed" | "cancelled";
  progress: number;
  due_date?: string;
  created_at: string;
  updated_at: string;
}

interface OrgTreeNode {
  id: number;
  name: string;
  title?: string;
  department?: string;
  role: string;
  member_type: "human" | "agent";
  status: string;
  children: OrgTreeNode[];
}

interface LayoutNode {
  id: number;
  name: string;
  title?: string;
  department?: string;
  role: string;
  member_type: "human" | "agent";
  status: string;
  x: number;
  y: number;
  children: LayoutNode[];
}

// ── Layout constants ────────────────────────────────────────────

const CARD_W = 220;
const CARD_H = 120;
const GAP_X = 40;
const GAP_Y = 80;
const PADDING = 60;

// ── Tree layout algorithm ───────────────────────────────────────

/** Compute the width each subtree needs. */
function subtreeWidth(node: OrgTreeNode): number {
  if (node.children.length === 0) return CARD_W;
  const childrenW = node.children.reduce((sum, c) => sum + subtreeWidth(c), 0);
  const gaps = (node.children.length - 1) * GAP_X;
  return Math.max(CARD_W, childrenW + gaps);
}

/** Recursively assign x,y positions. */
function layoutTree(node: OrgTreeNode, x: number, y: number): LayoutNode {
  const totalW = subtreeWidth(node);
  const layoutChildren: LayoutNode[] = [];

  if (node.children.length > 0) {
    const childrenW = node.children.reduce((sum, c) => sum + subtreeWidth(c), 0);
    const gaps = (node.children.length - 1) * GAP_X;
    let cx = x + (totalW - childrenW - gaps) / 2;

    for (const child of node.children) {
      const cw = subtreeWidth(child);
      layoutChildren.push(layoutTree(child, cx, y + CARD_H + GAP_Y));
      cx += cw + GAP_X;
    }
  }

  return {
    id: node.id,
    name: node.name,
    title: node.title,
    department: node.department,
    role: node.role,
    member_type: node.member_type,
    status: node.status,
    x: x + (totalW - CARD_W) / 2,
    y,
    children: layoutChildren,
  };
}

/** Layout all root nodes side by side. */
function layoutForest(roots: OrgTreeNode[]): LayoutNode[] {
  if (roots.length === 0) return [];

  const totalW = roots.reduce((sum, r) => sum + subtreeWidth(r), 0);
  const gaps = (roots.length - 1) * GAP_X;
  let x = PADDING;
  const y = PADDING;

  const result: LayoutNode[] = [];
  for (const root of roots) {
    const w = subtreeWidth(root);
    result.push(layoutTree(root, x, y));
    x += w + GAP_X;
  }

  return result;
}

/** Flatten layout tree to list of nodes. */
function flattenLayout(nodes: LayoutNode[]): LayoutNode[] {
  const result: LayoutNode[] = [];
  function walk(n: LayoutNode) {
    result.push(n);
    n.children.forEach(walk);
  }
  nodes.forEach(walk);
  return result;
}

/** Collect all parent→child edges. */
function collectEdges(nodes: LayoutNode[]): Array<{ parent: LayoutNode; child: LayoutNode }> {
  const edges: Array<{ parent: LayoutNode; child: LayoutNode }> = [];
  function walk(n: LayoutNode) {
    for (const c of n.children) {
      edges.push({ parent: n, child: c });
      walk(c);
    }
  }
  nodes.forEach(walk);
  return edges;
}

// ── Status colors ───────────────────────────────────────────────

const statusColors: Record<string, string> = {
  active: "#4ade80",
  running: "#22d3ee", 
  paused: "#facc15",
  idle: "#facc15",
  error: "#f87171",
  onboarding: "#a78bfa",
  offboarded: "#a3a3a3",
  terminated: "#a3a3a3",
};

const defaultStatusColor = "#a3a3a3";

// ── Tree List View Component ────────────────────────────────────

function OrgTreeList({ nodes }: { nodes: OrgTreeNode[] }) {
  return (
    <div className="p-6 space-y-2">
      {nodes.map((node) => (
        <OrgTreeListNode key={node.id} node={node} depth={0} />
      ))}
    </div>
  );
}

function OrgTreeListNode({ node, depth }: { node: OrgTreeNode; depth: number }) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = node.children.length > 0;

  const getTypeIcon = () => {
    return node.member_type === "agent" ? (
      <Bot className="w-4 h-4 text-blue-400" />
    ) : (
      <Users className="w-4 h-4 text-green-400" />
    );
  };

  return (
    <div>
      <div
        className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-warroom-surface-hover text-sm transition-colors cursor-pointer"
        style={{ paddingLeft: `${depth * 20 + 12}px` }}
      >
        {hasChildren ? (
          <button
            className="p-0.5 hover:bg-warroom-surface-secondary rounded"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setExpanded(!expanded);
            }}
          >
            <ChevronRight
              className={`w-3 h-3 text-warroom-muted transition-transform ${
                expanded ? "rotate-90" : ""
              }`}
            />
          </button>
        ) : (
          <span className="w-4" />
        )}
        
        <span
          className="w-2 h-2 rounded-full shrink-0"
          style={{ backgroundColor: statusColors[node.status] ?? defaultStatusColor }}
        />
        
        {getTypeIcon()}
        
        <span className="font-medium text-warroom-text flex-1">{node.name}</span>
        
        {node.title && (
          <span className="text-xs text-warroom-muted">{node.title}</span>
        )}
        
        <span className="text-xs text-warroom-muted capitalize">{node.role}</span>
      </div>
      
      {hasChildren && expanded && (
        <div>
          {node.children.map((child) => (
            <OrgTreeListNode key={child.id} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────

export default function OrgChartPanel() {
  const [orgTree, setOrgTree] = useState<OrgTreeNode[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showGoals, setShowGoals] = useState(false);
  const [viewMode, setViewMode] = useState<"chart" | "list">("chart");

  // Layout computation
  const layout = useMemo(() => layoutForest(orgTree), [orgTree]);
  const allNodes = useMemo(() => flattenLayout(layout), [layout]);
  const edges = useMemo(() => collectEdges(layout), [layout]);

  // Compute SVG bounds
  const bounds = useMemo(() => {
    if (allNodes.length === 0) return { width: 800, height: 600 };
    let maxX = 0, maxY = 0;
    for (const n of allNodes) {
      maxX = Math.max(maxX, n.x + CARD_W);
      maxY = Math.max(maxY, n.y + CARD_H);
    }
    return { width: maxX + PADDING, height: maxY + PADDING };
  }, [allNodes]);

  // Pan & zoom state
  const containerRef = useRef<HTMLDivElement>(null);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [dragging, setDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0, panX: 0, panY: 0 });

  // Center the chart on first load
  const hasInitialized = useRef(false);
  useEffect(() => {
    if (hasInitialized.current || allNodes.length === 0 || !containerRef.current) return;
    hasInitialized.current = true;

    const container = containerRef.current;
    const containerW = container.clientWidth;
    const containerH = container.clientHeight;

    // Fit chart to container
    const scaleX = (containerW - 40) / bounds.width;
    const scaleY = (containerH - 40) / bounds.height;
    const fitZoom = Math.min(scaleX, scaleY, 1);

    const chartW = bounds.width * fitZoom;
    const chartH = bounds.height * fitZoom;

    setZoom(fitZoom);
    setPan({
      x: (containerW - chartW) / 2,
      y: (containerH - chartH) / 2,
    });
  }, [allNodes, bounds]);

  // ── Data Loading ────────────────────────────────────────────

  const loadOrgTree = useCallback(async () => {
    try {
      const response = await authFetch(`${API}/api/org-chart/tree`);
      if (!response.ok) {
        throw new Error(`Failed to load org tree: ${response.statusText}`);
      }
      const data = await response.json();
      setOrgTree(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load org tree");
    }
  }, []);

  const loadGoals = useCallback(async () => {
    try {
      const response = await authFetch(`${API}/api/org-goals`);
      if (!response.ok) {
        throw new Error(`Failed to load goals: ${response.statusText}`);
      }
      const data = await response.json();
      setGoals(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load goals");
    }
  }, []);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        await Promise.all([loadOrgTree(), loadGoals()]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [loadOrgTree, loadGoals]);

  // ── Pan & Zoom Handlers ─────────────────────────────────────

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    // Don't drag if clicking a card
    const target = e.target as HTMLElement;
    if (target.closest("[data-org-card]")) return;
    setDragging(true);
    dragStart.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y };
  }, [pan]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragging) return;
    const dx = e.clientX - dragStart.current.x;
    const dy = e.clientY - dragStart.current.y;
    setPan({ x: dragStart.current.panX + dx, y: dragStart.current.panY + dy });
  }, [dragging]);

  const handleMouseUp = useCallback(() => {
    setDragging(false);
  }, []);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const container = containerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const factor = e.deltaY < 0 ? 1.1 : 0.9;
    const newZoom = Math.min(Math.max(zoom * factor, 0.2), 3);

    // Zoom toward mouse position
    const scale = newZoom / zoom;
    setPan({
      x: mouseX - scale * (mouseX - pan.x),
      y: mouseY - scale * (mouseY - pan.y),
    });
    setZoom(newZoom);
  }, [zoom, pan]);

  // ── Zoom Controls ───────────────────────────────────────────

  const zoomIn = () => {
    const newZoom = Math.min(zoom * 1.2, 3);
    const container = containerRef.current;
    if (container) {
      const cx = container.clientWidth / 2;
      const cy = container.clientHeight / 2;
      const scale = newZoom / zoom;
      setPan({ x: cx - scale * (cx - pan.x), y: cy - scale * (cy - pan.y) });
    }
    setZoom(newZoom);
  };

  const zoomOut = () => {
    const newZoom = Math.max(zoom * 0.8, 0.2);
    const container = containerRef.current;
    if (container) {
      const cx = container.clientWidth / 2;
      const cy = container.clientHeight / 2;
      const scale = newZoom / zoom;
      setPan({ x: cx - scale * (cx - pan.x), y: cy - scale * (cy - pan.y) });
    }
    setZoom(newZoom);
  };

  const fitToScreen = () => {
    if (!containerRef.current || allNodes.length === 0) return;
    const cW = containerRef.current.clientWidth;
    const cH = containerRef.current.clientHeight;
    const scaleX = (cW - 40) / bounds.width;
    const scaleY = (cH - 40) / bounds.height;
    const fitZoom = Math.min(scaleX, scaleY, 1);
    const chartW = bounds.width * fitZoom;
    const chartH = bounds.height * fitZoom;
    setZoom(fitZoom);
    setPan({ x: (cW - chartW) / 2, y: (cH - chartH) / 2 });
  };

  // ── Node Card Component ─────────────────────────────────────

  const renderNodeCard = (node: LayoutNode) => {
    const statusColor = statusColors[node.status] ?? defaultStatusColor;

    const getRoleIcon = (role: string) => {
      switch (role) {
        case "ceo": return <Crown className="w-4 h-4 text-yellow-500" />;
        case "director": return <Shield className="w-4 h-4 text-purple-500" />;
        case "manager": return <Briefcase className="w-4 h-4 text-blue-500" />;
        default: return <UserCircle className="w-4 h-4 text-gray-500" />;
      }
    };

    const getTypeIcon = () => {
      return node.member_type === "agent" ? (
        <Bot className="w-5 h-5 text-blue-400" />
      ) : (
        <Users className="w-5 h-5 text-green-400" />
      );
    };

    return (
      <div
        key={node.id}
        data-org-card
        className="absolute bg-warroom-surface border border-warroom-border rounded-lg shadow-sm hover:shadow-md hover:border-warroom-accent/50 transition-all duration-150 cursor-pointer select-none"
        style={{
          left: node.x,
          top: node.y,
          width: CARD_W,
          height: CARD_H,
        }}
        onClick={() => {
          // TODO: Navigate to member detail or open drawer
          console.log("Clicked member:", node.name);
        }}
      >
        <div className="flex items-start px-4 py-3 gap-3 h-full">
          {/* Agent/Human icon + status dot */}
          <div className="relative shrink-0">
            <div className="w-9 h-9 rounded-full bg-warroom-surface-secondary flex items-center justify-center">
              {getTypeIcon()}
            </div>
            <span
              className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-warroom-surface"
              style={{ backgroundColor: statusColor }}
            />
          </div>
          
          {/* Name + title + role + department */}
          <div className="flex flex-col min-w-0 flex-1">
            <span className="text-sm font-semibold text-warroom-text leading-tight truncate">
              {node.name}
            </span>
            {node.title && (
              <span className="text-xs text-warroom-muted leading-tight mt-0.5 truncate">
                {node.title}
              </span>
            )}
            <div className="flex items-center gap-1 mt-1">
              {getRoleIcon(node.role)}
              <span className="text-xs text-warroom-muted capitalize">
                {node.role}
              </span>
            </div>
            {node.department && (
              <span className="text-xs text-warroom-accent mt-1 truncate">
                {node.department}
              </span>
            )}
          </div>
        </div>
      </div>
    );
  };

  // ── Event Handlers ──────────────────────────────────────────

  const handleAddMember = () => {
    // TODO: Open add member modal
    console.log("Add member clicked");
  };

  // ── Render ──────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-warroom-bg">
        <div className="text-warroom-muted">Loading org chart...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center bg-warroom-bg">
        <div className="text-red-400">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="h-full bg-warroom-bg relative">
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 z-10 bg-warroom-surface border-b border-warroom-border p-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Building2 className="w-6 h-6 text-warroom-accent" />
            <h1 className="text-xl font-semibold text-warroom-text">Organization Chart</h1>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowGoals(!showGoals)}
              className={`px-3 py-1.5 rounded text-sm transition-colors ${
                showGoals 
                  ? 'bg-warroom-accent text-white' 
                  : 'bg-warroom-surface-secondary text-warroom-muted border border-warroom-border hover:bg-warroom-surface-hover'
              }`}
            >
              <Target className="w-4 h-4 inline mr-1" />
              {showGoals ? 'Chart View' : 'Goals View'}
            </button>

            {!showGoals && (
              <button
                onClick={() => setViewMode(viewMode === "chart" ? "list" : "chart")}
                className={`px-3 py-1.5 rounded text-sm transition-colors ${
                  viewMode === "list"
                    ? 'bg-warroom-accent text-white' 
                    : 'bg-warroom-surface-secondary text-warroom-muted border border-warroom-border hover:bg-warroom-surface-hover'
                }`}
              >
                {viewMode === "chart" ? (
                  <>
                    <List className="w-4 h-4 inline mr-1" />
                    List View
                  </>
                ) : (
                  <>
                    <Network className="w-4 h-4 inline mr-1" />
                    Chart View
                  </>
                )}
              </button>
            )}
          </div>
        </div>

        <button
          onClick={handleAddMember}
          className="flex items-center gap-2 px-4 py-2 bg-warroom-accent text-white rounded hover:bg-warroom-accent/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Member
        </button>
      </div>

      {/* Main Content */}
      <div className="pt-20 h-full">
        {showGoals ? (
          // Goals View
          <div className="p-6 space-y-6">
            <div className="grid gap-4">
              {goals.map(goal => (
                <GoalCard key={goal.id} goal={goal} />
              ))}
            </div>
          </div>
        ) : viewMode === "list" ? (
          // List View
          <div className="h-full overflow-y-auto">
            {orgTree.length > 0 ? (
              <OrgTreeList nodes={orgTree} />
            ) : (
              <div className="flex items-center justify-center h-full text-warroom-muted">
                No organizational hierarchy defined.
              </div>
            )}
          </div>
        ) : (
          // Chart View (SVG Canvas)
          <div
            ref={containerRef}
            className="w-full h-full overflow-hidden relative bg-warroom-bg border border-warroom-border rounded-lg"
            style={{ cursor: dragging ? "grabbing" : "grab" }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={handleWheel}
          >
            {/* Zoom controls */}
            <div className="absolute top-3 right-3 z-10 flex flex-col gap-1">
              <button
                className="w-8 h-8 flex items-center justify-center bg-warroom-surface border border-warroom-border rounded text-sm hover:bg-warroom-surface-hover transition-colors text-warroom-text"
                onClick={zoomIn}
                aria-label="Zoom in"
              >
                +
              </button>
              <button
                className="w-8 h-8 flex items-center justify-center bg-warroom-surface border border-warroom-border rounded text-sm hover:bg-warroom-surface-hover transition-colors text-warroom-text"
                onClick={zoomOut}
                aria-label="Zoom out"
              >
                −
              </button>
              <button
                className="w-8 h-8 flex items-center justify-center bg-warroom-surface border border-warroom-border rounded text-xs hover:bg-warroom-surface-hover transition-colors text-warroom-text font-mono"
                onClick={fitToScreen}
                title="Fit to screen"
                aria-label="Fit chart to screen"
              >
                Fit
              </button>
            </div>

            {allNodes.length === 0 ? (
              <div className="flex items-center justify-center h-full text-warroom-muted">
                No organizational hierarchy defined.
              </div>
            ) : (
              <>
                {/* SVG layer for edges */}
                <svg
                  className="absolute inset-0 pointer-events-none"
                  style={{
                    width: "100%",
                    height: "100%",
                  }}
                >
                  <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                    {edges.map(({ parent, child }) => {
                      const x1 = parent.x + CARD_W / 2;
                      const y1 = parent.y + CARD_H;
                      const x2 = child.x + CARD_W / 2;
                      const y2 = child.y;
                      const midY = (y1 + y2) / 2;

                      return (
                        <path
                          key={`${parent.id}-${child.id}`}
                          d={`M ${x1} ${y1} L ${x1} ${midY} L ${x2} ${midY} L ${x2} ${y2}`}
                          fill="none"
                          stroke="rgb(107, 114, 128)"
                          strokeWidth={2}
                        />
                      );
                    })}
                  </g>
                </svg>

                {/* Card layer */}
                <div
                  className="absolute inset-0"
                  style={{
                    transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                    transformOrigin: "0 0",
                  }}
                >
                  {allNodes.map(renderNodeCard)}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Goal Card Component ─────────────────────────────────────────

function GoalCard({ goal }: { goal: Goal }) {
  const getTypeColor = (type: string) => {
    const colors = {
      mission: "border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20",
      department: "border-blue-500 bg-blue-50 dark:bg-blue-950/20", 
      project: "border-green-500 bg-green-50 dark:bg-green-950/20",
      task: "border-gray-500 bg-gray-50 dark:bg-gray-950/20"
    };
    return colors[type as keyof typeof colors] || colors.task;
  };

  const getStatusColor = (status: string) => {
    const colors = {
      active: "text-green-600 dark:text-green-400",
      paused: "text-yellow-600 dark:text-yellow-400", 
      completed: "text-blue-600 dark:text-blue-400",
      cancelled: "text-red-600 dark:text-red-400"
    };
    return colors[status as keyof typeof colors] || colors.active;
  };

  return (
    <div className={`border-2 rounded-lg p-4 bg-warroom-surface ${getTypeColor(goal.goal_type)}`}>
      <div className="flex items-start justify-between mb-2">
        <div>
          <h3 className="font-semibold text-warroom-text">{goal.title}</h3>
          <div className="flex items-center gap-2 text-sm text-warroom-muted">
            <span className="capitalize font-medium">{goal.goal_type}</span>
            <span className={`capitalize ${getStatusColor(goal.status)}`}>• {goal.status}</span>
          </div>
        </div>
      </div>
      
      {goal.description && (
        <p className="text-sm text-warroom-muted mb-3">{goal.description}</p>
      )}
      
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="flex items-center justify-between text-sm mb-1">
            <span className="text-warroom-text">Progress</span>
            <span className="text-warroom-text">{goal.progress}%</span>
          </div>
          <div className="w-full bg-warroom-border rounded-full h-2">
            <div 
              className="bg-warroom-accent h-2 rounded-full transition-all duration-300"
              style={{ width: `${goal.progress}%` }}
            />
          </div>
        </div>
        
        {goal.due_date && (
          <div className="ml-4 text-sm text-warroom-muted">
            Due: {new Date(goal.due_date).toLocaleDateString()}
          </div>
        )}
      </div>
    </div>
  );
}