"use client";

import React, { useState } from "react";
import type { BarChartVisualization, LineChartVisualization } from "../types";
import { getSubjectTheme, type SubjectTheme } from "../subjectThemes";

interface ChartRendererProps {
  data: BarChartVisualization | LineChartVisualization;
  theme?: SubjectTheme;
}

export const ChartRenderer: React.FC<ChartRendererProps> = ({ data, theme: propTheme }) => {
  const [showTableView, setShowTableView] = useState<boolean>(false);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const theme = propTheme || getSubjectTheme(data?.subject);

  if (!data || !data.data || data.data.length === 0) {
    return (
      <div className="py-6 text-center font-sans text-xs" style={{ color: theme.colors.mutedInk }}>
        No chart data available to display.
      </div>
    );
  }

  const isBar = data.type === "bar_chart";
  const defaultColor = theme.colors.chartPrimary;

  const values = data.data.map((d) => d.value);
  const maxValue = Math.max(...values, 1);
  const minValue = Math.min(...values, 0);

  // SVG dimensions for standard responsive view
  const svgWidth = 600;
  const svgHeight = 240;
  const paddingLeft = 50;
  const paddingRight = 30;
  const paddingTop = 20;
  const paddingBottom = 40;

  const chartWidth = svgWidth - paddingLeft - paddingRight;
  const chartHeight = svgHeight - paddingTop - paddingBottom;

  return (
    <section aria-label={data.title || "Data Chart"} className="w-full space-y-4 font-sans">
      {/* Header controls */}
      <div
        className="flex items-center justify-between border-b pb-2"
        style={{ borderColor: `${theme.colors.ink}15` }}
      >
        <span
          className="text-xs font-mono font-bold uppercase tracking-wider"
          style={{ color: theme.colors.primary }}
        >
          {isBar ? "Textbook Figure: Bar Chart" : "Textbook Figure: Line Chart"}{" "}
          {data.unit ? `(${data.unit})` : ""}
        </span>

        <button
          type="button"
          onClick={() => setShowTableView(!showTableView)}
          className="text-xs font-semibold underline font-mono"
          style={{ color: theme.colors.primary }}
        >
          {showTableView ? "View Graphic Figure" : "View Data Table"}
        </button>
      </div>

      {/* Graphic Figure View or Table View */}
      {showTableView ? (
        <div
          className="overflow-x-auto rounded-xl border shadow-xs"
          style={{
            backgroundColor: theme.colors.paperBg,
            borderColor: theme.colors.paperBorder,
          }}
        >
          <table className="w-full text-left text-xs" style={{ color: theme.colors.ink }}>
            <thead
              className="uppercase font-mono border-b"
              style={{
                backgroundColor: theme.colors.headerBg,
                borderColor: theme.colors.accentBorder,
                color: theme.colors.primary,
              }}
            >
              <tr>
                <th scope="col" className="py-2.5 px-4 font-bold">
                  {data.xAxisLabel || "Input"}
                </th>
                <th scope="col" className="py-2.5 px-4 font-bold">
                  {data.yAxisLabel || "Value"} {data.unit ? `(${data.unit})` : ""}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: `${theme.colors.ink}15` }}>
              {data.data.map((item, idx) => (
                <tr key={idx} className="hover:bg-black/5">
                  <td className="py-2.5 px-4 font-semibold" style={{ color: theme.colors.ink }}>
                    {item.label}
                  </td>
                  <td
                    className="py-2.5 px-4 font-mono font-bold"
                    style={{ color: theme.colors.primary }}
                  >
                    {item.value}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        /* Pure SVG Responsive Figure Canvas */
        <div
          className="w-full p-4 rounded-xl border relative shadow-xs"
          style={{
            backgroundColor: theme.colors.paperBg,
            borderColor: theme.colors.paperBorder,
          }}
        >
          <div className="w-full overflow-hidden">
            <svg
              viewBox={`0 0 ${svgWidth} ${svgHeight}`}
              className="w-full h-auto max-h-80"
              preserveAspectRatio="xMidYMid meet"
            >
              {/* Grid Lines */}
              {[0, 0.25, 0.5, 0.75, 1].map((ratio, idx) => {
                const y = paddingTop + chartHeight * (1 - ratio);
                const val = (minValue + (maxValue - minValue) * ratio).toFixed(1);
                return (
                  <g key={idx}>
                    <line
                      x1={paddingLeft}
                      y1={y}
                      x2={paddingLeft + chartWidth}
                      y2={y}
                      stroke={theme.colors.chartGrid}
                      strokeWidth="1"
                      strokeDasharray="3 3"
                    />
                    <text
                      x={paddingLeft - 8}
                      y={y + 4}
                      textAnchor="end"
                      fontSize="10"
                      fontFamily="monospace"
                      fill={theme.colors.ink}
                    >
                      {val}
                    </text>
                  </g>
                );
              })}

              {/* Bar Chart Rendering */}
              {isBar &&
                data.data.map((item, idx) => {
                  const barCount = data.data.length;
                  const slotWidth = chartWidth / barCount;
                  const barWidth = Math.max(12, slotWidth * 0.55);
                  const x = paddingLeft + idx * slotWidth + (slotWidth - barWidth) / 2;

                  const ratio = Math.max(0, (item.value - minValue) / (maxValue - minValue || 1));
                  const h = Math.max(4, ratio * chartHeight);
                  const y = paddingTop + chartHeight - h;

                  const isHovered = hoveredIndex === idx;

                  return (
                    <g
                      key={idx}
                      onMouseEnter={() => setHoveredIndex(idx)}
                      onMouseLeave={() => setHoveredIndex(null)}
                      className="cursor-pointer"
                    >
                      <rect
                        x={x}
                        y={y}
                        width={barWidth}
                        height={h}
                        rx="4"
                        fill={item.color || defaultColor}
                        opacity={isHovered ? 0.85 : 1}
                        stroke={isHovered ? theme.colors.primary : "none"}
                        strokeWidth="2"
                      />
                      {/* X-Axis Label */}
                      <text
                        x={x + barWidth / 2}
                        y={paddingTop + chartHeight + 20}
                        textAnchor="middle"
                        fontSize="10"
                        fontFamily="sans-serif"
                        fill={theme.colors.ink}
                      >
                        {item.label}
                      </text>
                    </g>
                  );
                })}

              {/* Line Chart Rendering */}
              {!isBar && (
                <>
                  {/* Line path */}
                  {(() => {
                    const points = data.data.map((item, idx) => {
                      const count = data.data.length;
                      const x = paddingLeft + (count > 1 ? (idx / (count - 1)) * chartWidth : chartWidth / 2);
                      const ratio = Math.max(0, (item.value - minValue) / (maxValue - minValue || 1));
                      const y = paddingTop + chartHeight - ratio * chartHeight;
                      return { x, y, item };
                    });

                    const pathD = points
                      .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`)
                      .join(" ");

                    return (
                      <>
                        <path
                          d={pathD}
                          fill="none"
                          stroke={theme.colors.chartPrimary}
                          strokeWidth="3"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                        {points.map((p, idx) => {
                          const isHovered = hoveredIndex === idx;
                          return (
                            <g
                              key={idx}
                              onMouseEnter={() => setHoveredIndex(idx)}
                              onMouseLeave={() => setHoveredIndex(null)}
                              className="cursor-pointer"
                            >
                              <circle
                                cx={p.x}
                                cy={p.y}
                                r={isHovered ? 7 : 5}
                                fill={isHovered ? theme.colors.chartSecondary : theme.colors.chartPrimary}
                                stroke={theme.colors.paperBg}
                                strokeWidth="2"
                              />
                              {/* X Axis Label */}
                              <text
                                x={p.x}
                                y={paddingTop + chartHeight + 20}
                                textAnchor="middle"
                                fontSize="10"
                                fontFamily="sans-serif"
                                fill={theme.colors.ink}
                              >
                                {p.item.label}
                              </text>
                            </g>
                          );
                        })}
                      </>
                    );
                  })()}
                </>
              )}
            </svg>
          </div>

          {/* Interactive Tooltip Callout when hovering data points */}
          {hoveredIndex !== null && data.data[hoveredIndex] && (
            <div
              className="mt-2 p-2 rounded-md text-xs font-mono font-bold flex items-center justify-between border"
              style={{
                backgroundColor: theme.colors.chartTooltipBg,
                borderColor: theme.colors.accentBorder,
                color: theme.colors.chartTooltipText,
              }}
            >
              <span>{data.data[hoveredIndex].label}</span>
              <span>
                {data.data[hoveredIndex].value} {data.unit || ""}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Callout Block */}
      <div
        className="p-4 rounded-xl border-l-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs shadow-xs"
        style={{
          backgroundColor: theme.colors.calloutBg,
          borderColor: theme.colors.calloutBorder,
          color: theme.colors.calloutText,
        }}
      >
        <div className="flex items-start gap-2">
          <span className="font-bold uppercase tracking-wider flex-shrink-0 font-mono" style={{ color: theme.colors.primary }}>
            WHAT THIS SHOWS:
          </span>
          <p className="leading-relaxed" style={{ color: theme.colors.ink }}>
            {data.description ||
              "Quantified relationships demonstrating rate limits, trends, or critical inflection points across experimental parameters."}
          </p>
        </div>

        <span
          className="text-xs font-bold italic font-serif flex-shrink-0 bg-white/70 px-3 py-1 rounded-full border"
          style={{
            color: theme.colors.handwritingInk,
            borderColor: theme.colors.accentBorder,
          }}
        >
          {theme.visualMotifs.takeawayQuote}
        </span>
      </div>
    </section>
  );
};
