"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  useReactFlow,
  type Node,
  type Edge,
  type OnConnect,
  type NodeTypes,
  BackgroundVariant,
  ConnectionLineType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Zap, GitBranch, Play, ChevronLeft, ChevronRight } from "lucide-react";

import TriggerNode from "./nodes/TriggerNode";
import ConditionNode from "./nodes/ConditionNode";
import ActionNode from "./nodes/ActionNode";

/* ── Types ─────────────────────────────────────────────── */

interface WorkflowData {
  entity_type: string;
  event: string;
  condition_type: string;
  conditions: any[];
  actions: any[];
}

interface WorkflowCanvasProps {
  workflow: WorkflowData;
  readOnly?: boolean;
}

const nodeTypes: NodeTypes = {
  trigger: TriggerNode,
  condition: ConditionNode,
  action: ActionNode,
};

/* ── Palette Items ────────────────────────────────────── */

interface PaletteItem {
  type: string;
  label: string;
  icon: React.ReactNode;
  color: string;
}

const paletteItems: PaletteItem[] = [
  { type: "trigger", label: "Trigger", icon: <Zap size={16} />, color: "text-emerald-400" },
  { type: "condition", label: "Condition", icon: <GitBranch size={16} />, color: "text-yellow-400" },
  { type: "action", label: "Action", icon: <Play size={16} />, color: "text-blue-400" },
];

function NodePalette({ isCollapsed, onToggle }: { isCollapsed: boolean; onToggle: () => void }) {
  const onDragStart = (event: React.DragEvent, nodeType: string) => {
    event.dataTransfer.setData("application/reactflow", nodeType);
    event.dataTransfer.effectAllowed = "move";
  };

  return (
    <div className={`bg-warroom-surface border-r border-warroom-border transition-all duration-300 ${
      isCollapsed ? "w-12" : "w-48"
    } flex-shrink-0`}>
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center justify-between px-3">
        {!isCollapsed && <span className="text-xs font-semibold text-warroom-muted uppercase">Nodes</span>}
        <button
          onClick={onToggle}
          className="p-1 rounded-lg hover:bg-warroom-bg text-warroom-muted hover:text-warroom-text transition"
        >
          {isCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>

      {/* Palette Items */}
      <div className="p-3 space-y-2">
        {paletteItems.map((item) => (
          <div
            key={item.type}
            className={`${
              isCollapsed ? "flex justify-center" : "flex items-center gap-3"
            } p-3 rounded-lg bg-warroom-bg border border-warroom-border hover:border-warroom-accent/30 cursor-move transition`}
            draggable
            onDragStart={(event) => onDragStart(event, item.type)}
            title={isCollapsed ? item.label : undefined}
          >
            <div className={item.color}>
              {item.icon}
            </div>
            {!isCollapsed && (
              <span className="text-xs font-medium text-warroom-text">{item.label}</span>
            )}
          </div>
        ))}
      </div>

      {!isCollapsed && (
        <div className="px-3 py-2">
          <div className="text-[10px] text-warroom-muted/70 leading-relaxed">
            Drag items onto the canvas to add new nodes. They'll automatically connect to the last node.
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Layout ────────────────────────────────────────────── */

function buildNodesAndEdges(workflow: WorkflowData): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  let y = 0;
  const X_CENTER = 400;
  const Y_GAP = 200;

  // 1. Trigger node
  const triggerId = "trigger-1";
  nodes.push({
    id: triggerId,
    type: "trigger",
    position: { x: X_CENTER - 110, y },
    data: { entity_type: workflow.entity_type, event: workflow.event },
  });
  y += Y_GAP;

  // 2. Condition node (if conditions exist)
  let lastSourceId = triggerId;
  if (workflow.conditions && workflow.conditions.length > 0) {
    const condId = "condition-1";
    nodes.push({
      id: condId,
      type: "condition",
      position: { x: X_CENTER - 110, y },
      data: { conditions: workflow.conditions, conditionType: workflow.condition_type },
    });
    edges.push({
      id: `${triggerId}->${condId}`,
      source: triggerId,
      target: condId,
      type: "smoothstep",
      animated: true,
      style: { stroke: "#10b981", strokeWidth: 2 },
    });
    lastSourceId = condId;
    y += Y_GAP;
  }

  // 3. Action nodes
  const actionCount = workflow.actions?.length || 0;
  const NODE_H_GAP = 320; // horizontal gap between action nodes
  const totalWidth = actionCount * NODE_H_GAP;
  const startX = X_CENTER - totalWidth / 2;

  workflow.actions?.forEach((action: any, i: number) => {
    const actionId = `action-${i + 1}`;
    nodes.push({
      id: actionId,
      type: "action",
      position: { x: startX + i * NODE_H_GAP, y },
      data: {
        actionType: action.type,
        title: action.title || action.subject || action.goal || "",
        detail: action.body || action.message || action.channel || "",
        ...action,
      },
    });
    edges.push({
      id: `${lastSourceId}->${actionId}`,
      source: lastSourceId,
      sourceHandle: lastSourceId.startsWith("condition") ? "yes" : undefined,
      target: actionId,
      type: "smoothstep",
      animated: true,
      style: { stroke: "#6366f1", strokeWidth: 2 },
    });
  });

  return { nodes, edges };
}

/* ── Component ─────────────────────────────────────────── */

function WorkflowCanvasInner({ workflow, readOnly = false }: WorkflowCanvasProps) {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => buildNodesAndEdges(workflow),
    [workflow]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [paletteCollapsed, setPaletteCollapsed] = useState(false);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { screenToFlowPosition } = useReactFlow();

  const onConnect: OnConnect = useCallback(
    (params) => setEdges((eds) => addEdge({ ...params, type: "smoothstep", animated: true }, eds)),
    [setEdges]
  );

  // Find the last node in the flow
  const getLastNode = useCallback(() => {
    if (nodes.length === 0) return null;
    // Find the node with the highest Y position (bottom-most)
    return nodes.reduce((lastNode, currentNode) => 
      currentNode.position.y > lastNode.position.y ? currentNode : lastNode
    );
  }, [nodes]);

  // Generate unique ID for new nodes
  const generateNodeId = useCallback((nodeType: string) => {
    const existingIds = nodes
      .filter(node => node.id.startsWith(nodeType))
      .map(node => parseInt(node.id.split('-')[1]) || 0);
    const maxId = existingIds.length > 0 ? Math.max(...existingIds) : 0;
    return `${nodeType}-${maxId + 1}`;
  }, [nodes]);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const nodeType = event.dataTransfer.getData("application/reactflow");
      if (!nodeType || readOnly) return;

      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const newNodeId = generateNodeId(nodeType);
      let newNodeData: any = {};

      // Set default data based on node type
      switch (nodeType) {
        case "trigger":
          newNodeData = { entity_type: "deal", event: "created" };
          break;
        case "condition":
          newNodeData = { conditions: [], conditionType: "and" };
          break;
        case "action":
          newNodeData = { actionType: "send_email", title: "New Action", detail: "" };
          break;
      }

      const newNode: Node = {
        id: newNodeId,
        type: nodeType,
        position,
        data: newNodeData,
      };

      setNodes((nds) => nds.concat(newNode));

      // Connect to the last node
      const lastNode = getLastNode();
      if (lastNode) {
        const newEdge: Edge = {
          id: `${lastNode.id}->${newNodeId}`,
          source: lastNode.id,
          target: newNodeId,
          type: "smoothstep",
          animated: true,
          style: { stroke: "#6366f1", strokeWidth: 2 },
        };
        setEdges((eds) => eds.concat(newEdge));
      }
    },
    [screenToFlowPosition, readOnly, getLastNode, generateNodeId, setNodes, setEdges]
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  return (
    <div className="w-full h-full flex bg-warroom-bg rounded-xl overflow-hidden border border-warroom-border">
      {/* Node Palette Sidebar */}
      {!readOnly && (
        <div className={`${paletteCollapsed ? "hidden" : "block"} md:block`}>
          <NodePalette 
            isCollapsed={paletteCollapsed} 
            onToggle={() => setPaletteCollapsed(!paletteCollapsed)} 
          />
        </div>
      )}

      {/* React Flow Canvas */}
      <div className="flex-1" ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={readOnly ? undefined : onNodesChange}
          onEdgesChange={readOnly ? undefined : onEdgesChange}
          onConnect={readOnly ? undefined : onConnect}
          onDrop={readOnly ? undefined : onDrop}
          onDragOver={readOnly ? undefined : onDragOver}
          nodeTypes={nodeTypes}
          connectionLineType={ConnectionLineType.SmoothStep}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          minZoom={0.3}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
          className="workflow-canvas"
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={20}
            size={1}
            color="rgba(255,255,255,0.05)"
          />
          <Controls
            className="!bg-warroom-surface !border-warroom-border !rounded-xl !shadow-lg [&_button]:!bg-warroom-surface [&_button]:!border-warroom-border [&_button]:!text-warroom-text [&_button:hover]:!bg-warroom-bg"
          />
          <MiniMap
            className="!bg-warroom-surface !border-warroom-border !rounded-xl"
            nodeColor={() => "rgba(99, 102, 241, 0.5)"}
            maskColor="rgba(0, 0, 0, 0.3)"
          />
        </ReactFlow>
      </div>
    </div>
  );
}

// Wrapper component with ReactFlowProvider
export default function WorkflowCanvas(props: WorkflowCanvasProps) {
  return (
    <ReactFlowProvider>
      <WorkflowCanvasInner {...props} />
    </ReactFlowProvider>
  );
}
