"use client";

import React from "react";
import type { ComparisonVisualization } from "../types";
import { getSubjectTheme, type SubjectTheme } from "../subjectThemes";

interface ComparisonRendererProps {
  data: ComparisonVisualization;
  theme?: SubjectTheme;
}

export const ComparisonRenderer: React.FC<ComparisonRendererProps> = ({ data, theme: propTheme }) => {
  const theme = propTheme || getSubjectTheme(data?.subject);

  if (!data || !data.rows || data.rows.length === 0) {
    return (
      <div className="py-6 text-center font-sans text-xs" style={{ color: theme.colors.mutedInk }}>
        No comparison data available to render.
      </div>
    );
  }

  const columns = data.columns || ["Feature", "Option A", "Option B"];

  return (
    <section aria-label={data.title || "Comparison Table"} className="w-full space-y-4 font-sans">
      {data.description && (
        <p className="text-sm leading-relaxed max-w-3xl mb-3 font-sans" style={{ color: theme.colors.mutedInk }}>
          {data.description}
        </p>
      )}

      {/* Revision Table */}
      <div
        className="overflow-x-auto border rounded-xl shadow-xs"
        style={{
          backgroundColor: theme.colors.paperBg,
          borderColor: theme.colors.paperBorder,
        }}
      >
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr
              className="border-b-2"
              style={{
                backgroundColor: theme.colors.headerBg,
                borderColor: theme.colors.accentBorder,
                color: theme.colors.ink,
              }}
            >
              {columns.map((col, idx) => (
                <th
                  key={idx}
                  scope="col"
                  className={`py-3 px-4 font-bold ${
                    idx === 0
                      ? "w-1/4 uppercase tracking-wider text-[11px] font-mono"
                      : "text-xs font-serif uppercase tracking-wide"
                  }`}
                  style={{ color: idx === 0 ? theme.colors.primary : theme.colors.ink }}
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y" style={{ borderColor: `${theme.colors.ink}15` }}>
            {data.rows.map((row, rowIdx) => (
              <tr key={rowIdx} className="hover:bg-black/5 transition-colors">
                <td
                  className="py-3 px-4 font-bold uppercase text-[11px] font-mono tracking-wider"
                  style={{ color: theme.colors.ink }}
                >
                  {row.feature}
                </td>
                {row.values.map((val, valIdx) => {
                  const isHighlighted = row.highlightIndex === valIdx;
                  return (
                    <td
                      key={valIdx}
                      className="py-3 px-4 leading-relaxed"
                      style={{
                        backgroundColor: isHighlighted ? theme.colors.highlighterBg : "transparent",
                        color: isHighlighted ? theme.colors.highlighterText : theme.colors.mutedInk,
                        fontWeight: isHighlighted ? "700" : "400",
                        borderLeft: isHighlighted ? `3px solid ${theme.colors.accent}` : "none",
                      }}
                    >
                      {val}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Handwritten Study Takeaway Footer */}
      <div className="flex items-center justify-between gap-4 pt-2">
        <span className="text-xs font-mono" style={{ color: theme.colors.primary }}>
          ★ Highlighted cells mark fundamental pathway contrasts.
        </span>
        <span className="text-xs sm:text-sm font-bold italic font-serif" style={{ color: theme.colors.handwritingInk }}>
          "Opposite complementary contrasts! 🔄"
        </span>
      </div>
    </section>
  );
};
