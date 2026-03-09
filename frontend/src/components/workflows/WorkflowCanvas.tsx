"use client";

import { useCallback, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  type Node,
  type Edge,
  type OnConnect,
  type NodeTypes,
  BackgroundVariant,
  ConnectionLineType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

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

export default function WorkflowCanvas({ workflow, readOnly = false }: WorkflowCanvasProps) {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => buildNodesAndEdges(workflow),
    [workflow]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect: OnConnect = useCallback(
    (params) => setEdges((eds) => addEdge({ ...params, type: "smoothstep", animated: true }, eds)),
    [setEdges]
  );

  return (
    <div className="w-full h-full bg-warroom-bg rounded-xl overflow-hidden border border-warroom-border">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={readOnly ? undefined : onNodesChange}
        onEdgesChange={readOnly ? undefined : onEdgesChange}
        onConnect={readOnly ? undefined : onConnect}
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
  );
}
