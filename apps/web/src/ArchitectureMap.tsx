import { useMemo } from "react";
import { Background, Controls, MarkerType, ReactFlow } from "@xyflow/react";
import type {
  ArchitectureSummary,
  CycleDetail,
  LayerLink,
} from "./architecture-types";

export default function ArchitectureMap({
  summary,
  onRelationship,
}: {
  summary: ArchitectureSummary;
  onRelationship: (link: LayerLink) => void;
}) {
  const nodes = useMemo(
    () =>
      Object.entries(summary.layers).map(([name, count], index) => ({
        id: name,
        position: { x: (index % 3) * 250, y: Math.floor(index / 3) * 140 },
        data: { label: `${name}\n${count} files` },
        ariaLabel: `Layer ${name}, ${count} files`,
        style: { width: 200 },
      })),
    [summary.layers],
  );
  const edges = useMemo(
    () =>
      summary.relationships
        .slice(0, 100)
        .map((link, index) => ({
          id: String(index),
          source: link.source,
          target: link.target,
          label: `${link.count} imports`,
          markerEnd: { type: MarkerType.ArrowClosed },
        })),
    [summary.relationships],
  );
  return (
    <div className="architecture-map" aria-label="Architecture layer graph">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        deleteKeyCode={null}
        onEdgeClick={(_, edge) =>
          onRelationship(summary.relationships[Number(edge.id)])
        }
      >
        <Background />
        <Controls showInteractive={false} />
      </ReactFlow>
      <p className="muted">
        Consumer → dependency. Up to 100 relationships shown; every relationship
        is available in the table below.
      </p>
    </div>
  );
}

export function CycleMap({ detail }: { detail: CycleDetail }) {
  const { nodes, edges } = useMemo(() => {
    const members = detail.cycle.path.slice(0, -1).slice(0, 50);
    const visible = new Set(members);
    return {
      nodes: members.map((id, index) => ({
        id,
        position: {
          x: 300 + 250 * Math.cos((index * 2 * Math.PI) / members.length),
          y: 280 + 230 * Math.sin((index * 2 * Math.PI) / members.length),
        },
        data: { label: id.replace(/^file:/, "") },
        ariaLabel: id,
        style: { width: 180 },
      })),
      edges: detail.cycle.path.slice(0, -1).flatMap((source, index) => {
        const target = detail.cycle.path[index + 1];
        return visible.has(source) && visible.has(target)
          ? [
              {
                id: String(index),
                source,
                target,
                markerEnd: { type: MarkerType.ArrowClosed },
              },
            ]
          : [];
      }),
    };
  }, [detail]);
  return (
    <div className="architecture-map" aria-label="Cycle graph">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        deleteKeyCode={null}
      >
        <Background />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
