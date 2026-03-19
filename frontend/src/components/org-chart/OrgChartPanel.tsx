"use client";

import { useState, useEffect, useCallback } from "react";
import { 
  ReactFlow, 
  Node, 
  Edge, 
  addEdge, 
  MiniMap, 
  Controls, 
  Background,
  useNodesState,
  useEdgesState,
  Connection,
  NodeChange,
  EdgeChange
} from "@xyflow/react";
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
  Briefcase
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

// ── Custom Node Component ───────────────────────────────────

function OrgNode({ data }: { data: any }) {
  const { member, onEdit } = data;
  
  const getRoleIcon = (role: string) => {
    switch (role) {
      case "ceo": return <Crown className="w-4 h-4 text-yellow-500" />;
      case "director": return <Shield className="w-4 h-4 text-purple-500" />;
      case "manager": return <Briefcase className="w-4 h-4 text-blue-500" />;
      default: return <UserCircle className="w-4 h-4 text-gray-500" />;
    }
  };
  
  const getTypeIcon = (type: string) => {
    return type === "agent" ? (
      <Bot className="w-5 h-5 text-blue-400" />
    ) : (
      <Users className="w-5 h-5 text-green-400" />
    );
  };
  
  const getDepartmentColor = (department?: string) => {
    const colors: Record<string, string> = {
      "Technology": "bg-blue-100 border-blue-300",
      "Marketing": "bg-purple-100 border-purple-300", 
      "Design": "bg-pink-100 border-pink-300",
      "Executive": "bg-yellow-100 border-yellow-300",
      "Sales": "bg-green-100 border-green-300",
    };
    return colors[department || ""] || "bg-gray-100 border-gray-300";
  };

  return (
    <div 
      className={`px-4 py-3 rounded-lg border-2 cursor-pointer transition-all duration-200 hover:shadow-md min-w-[200px] ${getDepartmentColor(member.department)}`}
      onClick={() => onEdit(member)}
    >
      <div className="flex items-center gap-3 mb-2">
        {getTypeIcon(member.member_type)}
        <div className="flex-1">
          <div className="font-semibold text-sm text-gray-800">{member.name}</div>
          {member.title && (
            <div className="text-xs text-gray-600">{member.title}</div>
          )}
        </div>
        {getRoleIcon(member.role)}
      </div>
      
      {member.department && (
        <div className="text-xs text-gray-500 mb-1">{member.department}</div>
      )}
      
      {member.skills.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {member.skills.slice(0, 3).map((skill: string) => (
            <span 
              key={skill} 
              className="text-xs bg-white bg-opacity-70 rounded px-2 py-0.5 text-gray-700"
            >
              {skill}
            </span>
          ))}
          {member.skills.length > 3 && (
            <span className="text-xs text-gray-500">+{member.skills.length - 3} more</span>
          )}
        </div>
      )}
    </div>
  );
}

const nodeTypes = {
  orgMember: OrgNode,
};

// ── Main Component ──────────────────────────────────────────

export default function OrgChartPanel() {
  const [members, setMembers] = useState<OrgMember[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedMember, setSelectedMember] = useState<OrgMember | null>(null);
  const [showGoals, setShowGoals] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // ── Data Loading ────────────────────────────────────────

  const loadMembers = useCallback(async () => {
    try {
      const response = await authFetch(`${API}/api/org-chart/members`);
      if (!response.ok) {
        throw new Error(`Failed to load members: ${response.statusText}`);
      }
      const data = await response.json();
      setMembers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load members");
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

  const loadOrgTree = useCallback(async () => {
    try {
      setLoading(true);
      await loadMembers();
      await loadGoals();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load org chart data");
    } finally {
      setLoading(false);
    }
  }, [loadMembers, loadGoals]);

  // ── React Flow Layout Generation ───────────────────────────

  const generateLayout = useCallback((members: OrgMember[]) => {
    if (!members.length) return { nodes: [], edges: [] };

    // Build hierarchy
    const memberMap = new Map(members.map(m => [m.id, m]));
    const roots: OrgMember[] = [];
    const childrenMap = new Map<number, OrgMember[]>();

    members.forEach(member => {
      if (!member.reports_to_id) {
        roots.push(member);
      } else {
        if (!childrenMap.has(member.reports_to_id)) {
          childrenMap.set(member.reports_to_id, []);
        }
        childrenMap.get(member.reports_to_id)!.push(member);
      }
    });

    // Generate positions using a simple tree layout
    const nodes: Node[] = [];
    const edges: Edge[] = [];
    const levelWidth = 300;
    const levelHeight = 120;

    function layoutNode(member: OrgMember, level: number, siblingIndex: number, siblingCount: number): number {
      const x = siblingIndex * levelWidth - ((siblingCount - 1) * levelWidth) / 2;
      const y = level * levelHeight;

      nodes.push({
        id: member.id.toString(),
        type: 'orgMember',
        position: { x, y },
        data: { 
          member,
          onEdit: setSelectedMember
        },
      });

      // Add edge to parent
      if (member.reports_to_id) {
        edges.push({
          id: `edge-${member.reports_to_id}-${member.id}`,
          source: member.reports_to_id.toString(),
          target: member.id.toString(),
          type: 'smoothstep',
          animated: false,
          style: { stroke: '#64748b', strokeWidth: 2 },
        });
      }

      // Layout children
      const children = childrenMap.get(member.id) || [];
      let totalChildWidth = 0;
      
      children.forEach((child, index) => {
        totalChildWidth += layoutNode(child, level + 1, index, children.length);
      });

      return Math.max(levelWidth, totalChildWidth);
    }

    // Start layout from roots
    roots.forEach((root, index) => {
      layoutNode(root, 0, index, roots.length);
    });

    return { nodes, edges };
  }, []);

  // ── Effects ─────────────────────────────────────────────

  useEffect(() => {
    loadOrgTree();
  }, [loadOrgTree]);

  useEffect(() => {
    if (members.length > 0) {
      const { nodes: newNodes, edges: newEdges } = generateLayout(members);
      setNodes(newNodes);
      setEdges(newEdges);
    }
  }, [members, generateLayout, setNodes, setEdges]);

  // ── Event Handlers ──────────────────────────────────────

  const handleAddMember = () => {
    // TODO: Open add member modal
    console.log("Add member clicked");
  };

  const handleEditMember = (member: OrgMember) => {
    setSelectedMember(member);
  };

  const closeMemberDrawer = () => {
    setSelectedMember(null);
  };

  // ── Render ──────────────────────────────────────────────

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
        {!showGoals ? (
          // Org Chart View
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            fitView
            className="bg-warroom-bg"
          >
            <Background color="#374151" />
            <Controls className="bg-warroom-surface border border-warroom-border" />
            <MiniMap 
              className="bg-warroom-surface border border-warroom-border"
              nodeColor="#6366f1"
              maskColor="rgba(0, 0, 0, 0.2)"
            />
          </ReactFlow>
        ) : (
          // Goals View
          <div className="p-6 space-y-6">
            <div className="grid gap-4">
              {goals.map(goal => (
                <GoalCard key={goal.id} goal={goal} members={members} />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Member Detail Drawer */}
      {selectedMember && (
        <MemberDrawer 
          member={selectedMember} 
          onClose={closeMemberDrawer}
          onUpdate={loadOrgTree}
        />
      )}
    </div>
  );
}

// ── Goal Card Component ─────────────────────────────────────

function GoalCard({ goal, members }: { goal: Goal; members: OrgMember[] }) {
  const owner = goal.owner_member_id ? members.find(m => m.id === goal.owner_member_id) : null;
  
  const getTypeColor = (type: string) => {
    const colors = {
      mission: "border-yellow-400 bg-yellow-50",
      department: "border-blue-400 bg-blue-50", 
      project: "border-green-400 bg-green-50",
      task: "border-gray-400 bg-gray-50"
    };
    return colors[type as keyof typeof colors] || colors.task;
  };

  const getStatusColor = (status: string) => {
    const colors = {
      active: "text-green-600",
      paused: "text-yellow-600", 
      completed: "text-blue-600",
      cancelled: "text-red-600"
    };
    return colors[status as keyof typeof colors] || colors.active;
  };

  return (
    <div className={`border-2 rounded-lg p-4 ${getTypeColor(goal.goal_type)}`}>
      <div className="flex items-start justify-between mb-2">
        <div>
          <h3 className="font-semibold text-gray-800">{goal.title}</h3>
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <span className="capitalize font-medium">{goal.goal_type}</span>
            <span className={`capitalize ${getStatusColor(goal.status)}`}>• {goal.status}</span>
          </div>
        </div>
        
        {owner && (
          <div className="flex items-center gap-2 text-sm text-gray-600">
            {owner.member_type === "agent" ? (
              <Bot className="w-4 h-4 text-blue-400" />
            ) : (
              <Users className="w-4 h-4 text-green-400" />
            )}
            <span>{owner.name}</span>
          </div>
        )}
      </div>
      
      {goal.description && (
        <p className="text-sm text-gray-600 mb-3">{goal.description}</p>
      )}
      
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="flex items-center justify-between text-sm mb-1">
            <span>Progress</span>
            <span>{goal.progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${goal.progress}%` }}
            />
          </div>
        </div>
        
        {goal.due_date && (
          <div className="ml-4 text-sm text-gray-500">
            Due: {new Date(goal.due_date).toLocaleDateString()}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Member Drawer Component ─────────────────────────────────

function MemberDrawer({ 
  member, 
  onClose, 
  onUpdate 
}: { 
  member: OrgMember; 
  onClose: () => void;
  onUpdate: () => void;
}) {
  const [isEditing, setIsEditing] = useState(false);
  
  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-warroom-surface border-l border-warroom-border shadow-xl z-50 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-warroom-border flex items-center justify-between">
        <h2 className="text-lg font-semibold text-warroom-text">
          {member.member_type === "agent" ? "Agent" : "Team Member"} Details
        </h2>
        <button 
          onClick={onClose}
          className="p-1 hover:bg-warroom-surface-hover rounded text-warroom-muted"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 p-4 space-y-4 overflow-y-auto">
        <div className="flex items-center gap-3">
          {member.member_type === "agent" ? (
            <Bot className="w-8 h-8 text-blue-400" />
          ) : (
            <Users className="w-8 h-8 text-green-400" />
          )}
          <div>
            <h3 className="font-semibold text-warroom-text">{member.name}</h3>
            {member.title && (
              <p className="text-sm text-warroom-muted">{member.title}</p>
            )}
          </div>
        </div>

        <div className="space-y-3">
          <div>
            <label className="text-sm font-medium text-warroom-muted">Department</label>
            <p className="text-warroom-text">{member.department || "—"}</p>
          </div>
          
          <div>
            <label className="text-sm font-medium text-warroom-muted">Role</label>
            <p className="text-warroom-text capitalize">{member.role}</p>
          </div>
          
          <div>
            <label className="text-sm font-medium text-warroom-muted">Status</label>
            <p className="text-warroom-text capitalize">{member.status}</p>
          </div>

          {member.skills.length > 0 && (
            <div>
              <label className="text-sm font-medium text-warroom-muted">Skills</label>
              <div className="flex flex-wrap gap-1 mt-1">
                {member.skills.map(skill => (
                  <span 
                    key={skill}
                    className="text-xs bg-warroom-surface-secondary text-warroom-text px-2 py-1 rounded"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          {member.budget_allocation > 0 && (
            <div>
              <label className="text-sm font-medium text-warroom-muted">Budget Allocation</label>
              <p className="text-warroom-text">${member.budget_allocation.toLocaleString()}</p>
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="p-4 border-t border-warroom-border flex gap-2">
        <button 
          onClick={() => setIsEditing(true)}
          className="flex items-center gap-2 px-3 py-2 bg-warroom-accent text-white rounded hover:bg-warroom-accent/90 transition-colors"
        >
          <Edit className="w-4 h-4" />
          Edit
        </button>
        <button 
          className="flex items-center gap-2 px-3 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
        >
          <Trash2 className="w-4 h-4" />
          Remove
        </button>
      </div>
    </div>
  );
}