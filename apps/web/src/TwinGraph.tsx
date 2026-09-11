import { useMemo } from "react";
import {
  Background,
  Controls,
  MarkerType,
  ReactFlow,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { GraphData, GraphNode } from "./types";

export default function TwinGraph({
  graph,
  selected,
  affected,
  onSelect,
}: {
  graph: GraphData;
  selected: string | null;
  affected: Set<string>;
  onSelect: (node: GraphNode) => void;
}) {
  const nodes: Node[] = useMemo(
    () =>
      graph.nodes.map((node, index) => ({
        id: node.id,
        position: {
          x: (index % (graph.nodes.length <= 12 ? 2 : 4)) * 260,
          y: Math.floor(index / (graph.nodes.length <= 12 ? 2 : 4)) * 125,
        },
        data: {
          label: (
            <div className="graph-label">
              <span>
                {node.kind} · {node.language}
              </span>
              <strong title={node.label}>{node.label.split("/").pop()}</strong>
              <small title={node.path}>{node.path}</small>
            </div>
          ),
        },
        selected: selected === node.id,
        className: affected.has(node.id) ? "impact-node" : "",
        ariaLabel: `${node.kind} ${node.label}`,
        style: { width: 220 },
      })),
    [graph.nodes, selected, affected],
  );
  const edges = useMemo(
    () =>
      graph.edges.map((edge) => ({
        ...edge,
        markerEnd: { type: MarkerType.ArrowClosed },
        style: {
          stroke:
            affected.has(edge.source) && affected.has(edge.target)
              ? "#deab62"
              : "#697486",
          strokeWidth: 1.5,
        },
        label: edge.kind,
        animated: false,
      })),
    [graph.edges, affected],
  );
  return (
    <div className="graph-canvas" aria-label="Interactive repository graph">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        minZoom={0.15}
        maxZoom={2}
        nodesDraggable={false}
        nodesConnectable={false}
        deleteKeyCode={null}
        onNodeClick={(_, node) => {
          const match = graph.nodes.find((n) => n.id === node.id);
          if (match) onSelect(match);
        }}
      >
        <Background gap={24} size={1} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
