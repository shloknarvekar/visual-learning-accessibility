"use client";

import React, { useState, useRef, useMemo, useEffect } from "react";
import type { ConceptMapVisualization } from "../types";
import { getSubjectTheme, type SubjectTheme } from "../subjectThemes";

interface ConceptMapRendererProps {
  data: ConceptMapVisualization;
  theme?: SubjectTheme;
}

export function computeHierarchicalLayout(
  nodes: ConceptMapVisualization["nodes"] = [],
  edges: ConceptMapVisualization["edges"] = [],
  width = 1000,
  height = 540
): {
  positions: Record<string, { x: number; y: number }>;
  centralNodeId: string | null;
} {
  const map: Record<string, { x: number; y: number }> = {};
  if (!nodes || nodes.length === 0) return { positions: map, centralNodeId: null };

  const inDegree: Record<string, number> = {};
  const outDegree: Record<string, number> = {};
  const targetsOf: Record<string, string[]> = {};
  const sourcesOf: Record<string, string[]> = {};

  nodes.forEach((n) => {
    inDegree[n.id] = 0;
    outDegree[n.id] = 0;
    targetsOf[n.id] = [];
    sourcesOf[n.id] = [];
  });

  edges.forEach((e) => {
    if (inDegree[e.target] !== undefined) inDegree[e.target] += 1;
    if (outDegree[e.source] !== undefined) outDegree[e.source] += 1;
    if (targetsOf[e.source]) targetsOf[e.source].push(e.target);
    if (sourcesOf[e.target]) sourcesOf[e.target].push(e.source);
  });

  let maxDegree = -1;
  let centralNodeId: string | null = null;
  nodes.forEach((n) => {
    const totalDeg = (inDegree[n.id] || 0) + (outDegree[n.id] || 0);
    if (totalDeg > maxDegree) {
      maxDegree = totalDeg;
      centralNodeId = n.id;
    }
  });

  const levelMap: Record<string, number> = {};
  nodes.forEach((n) => {
    levelMap[n.id] = 0;
  });

  if (edges && edges.length > 0) {
    let changed = true;
    let iterations = 0;
    const maxIterations = nodes.length * 3;

    while (changed && iterations < maxIterations) {
      changed = false;
      iterations++;
      edges.forEach((e) => {
        const srcLvl = levelMap[e.source] ?? 0;
        const tgtLvl = levelMap[e.target] ?? 0;
        if (srcLvl >= tgtLvl) {
          levelMap[e.target] = srcLvl + 1;
          changed = true;
        }
      });
    }
  }

  const levelsRaw: Record<number, string[]> = {};
  nodes.forEach((n) => {
    const lvl = levelMap[n.id] ?? 0;
    if (!levelsRaw[lvl]) levelsRaw[lvl] = [];
    levelsRaw[lvl].push(n.id);
  });

  const sortedLevels = Object.keys(levelsRaw)
    .map(Number)
    .sort((a, b) => a - b);

  const orderedLevels: Record<number, string[]> = {};
  if (sortedLevels.length > 0) {
    orderedLevels[sortedLevels[0]] = [...levelsRaw[sortedLevels[0]]];
  }

  for (let i = 1; i < sortedLevels.length; i++) {
    const currentLvl = sortedLevels[i];
    const currentNodes = levelsRaw[currentLvl];

    const prevLevelNodes = orderedLevels[sortedLevels[i - 1]] || [];
    const prevPosMap: Record<string, number> = {};
    prevLevelNodes.forEach((id, idx) => {
      prevPosMap[id] = idx;
    });

    const nodeBarycenters = currentNodes.map((nodeId) => {
      const incomingSources = sourcesOf[nodeId] || [];
      if (incomingSources.length === 0) return 999;
      const sum = incomingSources.reduce((acc, srcId) => acc + (prevPosMap[srcId] ?? 0), 0);
      return sum / incomingSources.length;
    });

    const paired = currentNodes.map((id, idx) => ({ id, score: nodeBarycenters[idx] }));
    paired.sort((a, b) => a.score - b.score);

    orderedLevels[currentLvl] = paired.map((p) => p.id);
  }

  const totalLevels = sortedLevels.length;
  const paddingX = 80;
  const paddingY = 50;
  const usableWidth = width - paddingX * 2 - 150;
  const stepX = totalLevels > 1 ? usableWidth / (totalLevels - 1) : 0;

  sortedLevels.forEach((lvl, colIdx) => {
    const nodeIds = orderedLevels[lvl] || [];
    const countInLevel = nodeIds.length;
    const xPos = totalLevels > 1 ? paddingX + colIdx * stepX : width / 2 - 75;

    const usableHeight = height - paddingY * 2;
    const stepY = countInLevel > 1 ? usableHeight / countInLevel : 0;

    nodeIds.forEach((id, rowIdx) => {
      const nodeObj = nodes.find((n) => n.id === id);

      const x = typeof nodeObj?.x === "number" ? nodeObj.x : Math.round(xPos);
      const y =
        typeof nodeObj?.y === "number"
          ? nodeObj.y
          : countInLevel > 1
          ? Math.round(paddingY + (rowIdx + 0.5) * stepY - 25)
          : Math.round(height / 2 - 25);

      map[id] = { x, y };
    });
  });

  return { positions: map, centralNodeId };
}

export const ConceptMapRenderer: React.FC<ConceptMapRendererProps> = ({ data, theme: propTheme }) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [zoom, setZoom] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [activeTab, setActiveTab] = useState<"graph" | "text">("graph");

  const theme = propTheme || getSubjectTheme(data?.subject);

  const layoutResult = useMemo(() => {
    return computeHierarchicalLayout(data?.nodes, data?.edges, 1000, 540);
  }, [data]);

  const [nodePositions, setNodePositions] = useState<Record<string, { x: number; y: number }>>(
    layoutResult.positions
  );

  useEffect(() => {
    setNodePositions(layoutResult.positions);
  }, [layoutResult]);

  const draggingNodeRef = useRef<string | null>(null);
  const dragOffsetRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  if (!data || !data.nodes || data.nodes.length === 0) {
    return (
      <div className="py-6 text-center font-sans text-xs" style={{ color: theme.colors.mutedInk }}>
        No concept map data available to render.
      </div>
    );
  }

  const selectedNode = data.nodes.find((n) => n.id === selectedNodeId);

  const handleMouseDownNode = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setSelectedNodeId(id);
    draggingNodeRef.current = id;
    const currentPos = nodePositions[id] || { x: 0, y: 0 };
    dragOffsetRef.current = {
      x: e.clientX / zoom - currentPos.x,
      y: e.clientY / zoom - currentPos.y,
    };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!draggingNodeRef.current) return;
    const id = draggingNodeRef.current;
    const newX = e.clientX / zoom - dragOffsetRef.current.x;
    const newY = e.clientY / zoom - dragOffsetRef.current.y;
    setNodePositions((prev) => ({
      ...prev,
      [id]: { x: Math.max(20, Math.min(1100, newX)), y: Math.max(20, Math.min(600, newY)) },
    }));
  };

  const handleMouseUp = () => {
    draggingNodeRef.current = null;
  };

  const handleReset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setNodePositions(layoutResult.positions);
  };

  const nodeStyles = theme.colors.nodeBgs;

  return (
    <section aria-label={data.title || "Concept Map"} className="w-full space-y-4 font-sans">
      {data.description && (
        <p className="text-sm leading-relaxed max-w-3xl mb-2 font-sans" style={{ color: theme.colors.mutedInk }}>
          {data.description}
        </p>
      )}

      {/* Tab Switch: Visual Diagram vs Accessible Text Outline */}
      <div
        className="flex items-center justify-between border-b pb-2"
        style={{ borderColor: `${theme.colors.ink}15` }}
      >
        <div className="flex items-center gap-4 text-xs font-sans">
          <button
            type="button"
            onClick={() => setActiveTab("graph")}
            className={`pb-1 font-mono font-bold transition-all ${
              activeTab === "graph" ? "border-b-2 -mb-px" : "opacity-60 hover:opacity-100"
            }`}
            style={{
              color: activeTab === "graph" ? theme.colors.primary : theme.colors.ink,
              borderColor: activeTab === "graph" ? theme.colors.primary : "transparent",
            }}
          >
            Visual Diagram
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("text")}
            className={`pb-1 font-mono font-bold transition-all ${
              activeTab === "text" ? "border-b-2 -mb-px" : "opacity-60 hover:opacity-100"
            }`}
            style={{
              color: activeTab === "text" ? theme.colors.primary : theme.colors.ink,
              borderColor: activeTab === "text" ? theme.colors.primary : "transparent",
            }}
          >
            Accessible Outline
          </button>
        </div>

        <span
          className="text-xs italic font-serif font-bold hidden sm:inline"
          style={{ color: theme.colors.handwritingInk }}
        >
          "Drag nodes to rearrange • Click for details"
        </span>
      </div>

      {/* Accessible Text Outline */}
      {activeTab === "text" ? (
        <div
          className="p-4 rounded-xl border space-y-4 font-sans shadow-xs"
          style={{
            backgroundColor: theme.colors.headerBg,
            borderColor: theme.colors.paperBorder,
          }}
        >
          <div className="border-b pb-2" style={{ borderColor: `${theme.colors.ink}15` }}>
            <h3 className="text-sm font-bold" style={{ color: theme.colors.ink }}>
              Textbook Concept Breakdown
            </h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.nodes.map((node) => {
              const outgoingEdges = data.edges.filter((e) => e.source === node.id);
              const isCentral = node.id === layoutResult.centralNodeId;

              return (
                <div
                  key={node.id}
                  className="p-3 rounded-lg border"
                  style={{
                    backgroundColor: theme.colors.paperBg,
                    borderColor: isCentral ? theme.colors.primary : `${theme.colors.ink}20`,
                    boxShadow: isCentral ? `0 0 0 1px ${theme.colors.primary}` : "none",
                  }}
                >
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="font-bold text-xs font-sans" style={{ color: theme.colors.ink }}>
                      {node.label}
                    </h4>
                    {node.category && (
                      <span
                        className="text-[10px] uppercase font-bold font-mono"
                        style={{ color: theme.colors.primary }}
                      >
                        {node.category}
                      </span>
                    )}
                  </div>
                  {node.description && (
                    <p className="text-xs mb-2" style={{ color: theme.colors.mutedInk }}>
                      {node.description}
                    </p>
                  )}

                  {outgoingEdges.length > 0 && (
                    <div className="text-xs" style={{ color: theme.colors.handwritingInk }}>
                      <span className="font-bold font-mono">Relationships:</span>
                      <ul className="list-disc list-inside ml-1" style={{ color: theme.colors.mutedInk }}>
                        {outgoingEdges.map((e, idx) => {
                          const targetNode = data.nodes.find((n) => n.id === e.target);
                          return (
                            <li key={idx}>
                              {e.relationship} →{" "}
                              <span className="font-semibold" style={{ color: theme.colors.ink }}>
                                {targetNode?.label || e.target}
                              </span>
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        /* Visual Diagram View Canvas */
        <div
          className="relative rounded-xl border overflow-hidden shadow-xs"
          style={{
            backgroundColor: theme.colors.paperBg,
            borderColor: theme.colors.paperBorder,
          }}
        >
          {/* Zoom / Reset Toolbar */}
          <div
            className="absolute top-3 left-3 z-20 flex items-center gap-1 border p-1 rounded-md text-xs shadow-xs font-mono"
            style={{
              backgroundColor: theme.colors.headerBg,
              borderColor: theme.colors.accentBorder,
            }}
          >
            <button
              type="button"
              onClick={() => setZoom((z) => Math.min(z + 0.15, 1.8))}
              className="w-6 h-6 hover:bg-black/5 font-bold flex items-center justify-center"
              style={{ color: theme.colors.ink }}
              title="Zoom In"
            >
              +
            </button>
            <span className="text-[11px] px-1" style={{ color: theme.colors.ink }}>
              {Math.round(zoom * 100)}%
            </span>
            <button
              type="button"
              onClick={() => setZoom((z) => Math.max(z - 0.15, 0.6))}
              className="w-6 h-6 hover:bg-black/5 font-bold flex items-center justify-center"
              style={{ color: theme.colors.ink }}
              title="Zoom Out"
            >
              -
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="px-2 py-0.5 hover:bg-black/5 font-semibold text-[11px] border-l"
              style={{
                color: theme.colors.primary,
                borderColor: theme.colors.accentBorder,
              }}
            >
              Reset
            </button>
          </div>

          {/* SVG Canvas */}
          <div
            className="w-full h-[520px] cursor-grab active:cursor-grabbing select-none relative"
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          >
            <svg
              className="w-full h-full"
              viewBox="0 0 1000 540"
              style={{
                transform: `scale(${zoom}) translate(${pan.x}px, ${pan.y}px)`,
                transformOrigin: "center center",
                transition: draggingNodeRef.current ? "none" : "transform 0.15s ease-out",
              }}
            >
              <defs>
                <pattern id={`subjectGrid-${theme.id}`} width="24" height="24" patternUnits="userSpaceOnUse">
                  {theme.colors.paperGridPattern === "graph" ? (
                    <path d="M 24 0 L 0 0 0 24" fill="none" stroke={theme.colors.gridColor} strokeWidth="0.8" />
                  ) : theme.colors.paperGridPattern === "hex" ? (
                    <path d="M 12 0 L 24 7 L 24 21 L 12 28 L 0 21 L 0 7 Z" fill="none" stroke={theme.colors.gridColor} strokeWidth="0.6" />
                  ) : theme.colors.paperGridPattern === "contour" ? (
                    <path d="M 0 12 Q 6 4 12 12 T 24 12" fill="none" stroke={theme.colors.gridColor} strokeWidth="0.8" />
                  ) : theme.colors.paperGridPattern === "lines" ? (
                    <line x1="0" y1="24" x2="24" y2="24" stroke={theme.colors.gridColor} strokeWidth="0.8" />
                  ) : (
                    <circle cx="12" cy="12" r="0.9" fill={theme.colors.gridColor} />
                  )}
                </pattern>

                <marker
                  id={`arrowhead-${theme.id}`}
                  markerWidth="8"
                  markerHeight="6"
                  refX="16"
                  refY="3"
                  orient="auto"
                >
                  <polygon points="0 0, 8 3, 0 6" fill={theme.colors.handwritingInk} />
                </marker>
              </defs>

              {/* Subject Paper Canvas Grid Background */}
              <rect width="1000" height="540" fill={`url(#subjectGrid-${theme.id})`} />

              {/* Subject Watermark Decorative Symbols */}
              {theme.visualMotifs.symbolWatermark.slice(0, 4).map((sym, idx) => (
                <text
                  key={idx}
                  x={150 + idx * 220}
                  y={80 + (idx % 2) * 320}
                  fill={theme.colors.primary}
                  opacity="0.06"
                  fontSize="48"
                  fontWeight="bold"
                  fontFamily="sans-serif"
                >
                  {sym}
                </text>
              ))}

              {/* Render Non-Crossing S-Curve Ink Edges */}
              {data.edges.map((edge, i) => {
                const sourcePos = nodePositions[edge.source] || { x: 100, y: 100 };
                const targetPos = nodePositions[edge.target] || { x: 300, y: 300 };

                const startX = sourcePos.x + 150;
                const startY = sourcePos.y + 25;
                const endX = targetPos.x;
                const endY = targetPos.y + 25;

                const midX = (startX + endX) / 2;
                const pathD = `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`;
                const labelX = midX;
                const labelY = (startY + endY) / 2;

                return (
                  <g key={i}>
                    <path
                      d={pathD}
                      fill="none"
                      stroke={theme.colors.handwritingInk}
                      strokeWidth="1.8"
                      strokeDasharray="4 2"
                      markerEnd={`url(#arrowhead-${theme.id})`}
                    />
                    {/* Relationship Label Pill */}
                    <g transform={`translate(${labelX}, ${labelY})`}>
                      <rect
                        x="-44"
                        y="-11"
                        width="88"
                        height="22"
                        rx="6"
                        fill={theme.colors.headerBg}
                        stroke={theme.colors.handwritingInk}
                        strokeWidth="1"
                      />
                      <text
                        x="0"
                        y="4"
                        textAnchor="middle"
                        fill={theme.colors.handwritingInk}
                        fontSize="11"
                        fontFamily="serif"
                        fontStyle="italic"
                        fontWeight="700"
                      >
                        {edge.relationship}
                      </text>
                    </g>
                  </g>
                );
              })}

              {/* Render Concept Nodes */}
              {data.nodes.map((node, nodeIdx) => {
                const pos = nodePositions[node.id] || { x: 100, y: 100 };
                const isSelected = selectedNodeId === node.id;
                const isCentral = node.id === layoutResult.centralNodeId;
                const style = nodeStyles[nodeIdx % nodeStyles.length];

                return (
                  <g
                    key={node.id}
                    transform={`translate(${pos.x}, ${pos.y})`}
                    onMouseDown={(e) => handleMouseDownNode(e, node.id)}
                    className="cursor-pointer"
                  >
                    <foreignObject width="150" height="52">
                      <div
                        className={`w-full h-full p-2.5 rounded-xl border-2 flex flex-col justify-center transition-all ${
                          style.bg
                        } ${style.border}`}
                        style={{
                          borderColor: isCentral
                            ? theme.colors.primary
                            : isSelected
                            ? theme.colors.handwritingInk
                            : undefined,
                          boxShadow: isCentral
                            ? `0 0 0 2px ${theme.colors.primary}33`
                            : isSelected
                            ? `0 4px 12px ${theme.colors.handwritingInk}30`
                            : "none",
                        }}
                      >
                        <div className="flex items-center justify-between">
                          <span className={`text-xs font-bold truncate ${style.text} font-sans`}>
                            {node.label}
                          </span>
                          {isCentral && (
                            <span
                              className="text-[8px] font-mono uppercase px-1 rounded font-bold"
                              style={{
                                backgroundColor: theme.colors.primary,
                                color: "#ffffff",
                              }}
                            >
                              CORE
                            </span>
                          )}
                        </div>
                        {node.category && (
                          <span
                            className={`text-[9px] uppercase tracking-wider font-semibold font-mono truncate ${style.tag}`}
                          >
                            {node.category}
                          </span>
                        )}
                      </div>
                    </foreignObject>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Selected Node Details Drawer */}
          {selectedNode && (
            <div
              className="p-3 border-t flex items-center justify-between gap-3 text-xs font-sans"
              style={{
                backgroundColor: theme.colors.headerBg,
                borderColor: theme.colors.paperBorder,
              }}
            >
              <div>
                <span className="font-bold font-mono" style={{ color: theme.colors.primary }}>
                  Selected Concept:
                </span>{" "}
                <span className="font-bold" style={{ color: theme.colors.ink }}>
                  {selectedNode.label}
                </span>
                {selectedNode.description && (
                  <p className="text-xs" style={{ color: theme.colors.mutedInk }}>
                    {selectedNode.description}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={() => setSelectedNodeId(null)}
                className="text-xs underline font-mono"
                style={{ color: theme.colors.primary }}
              >
                Close
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  );
};
