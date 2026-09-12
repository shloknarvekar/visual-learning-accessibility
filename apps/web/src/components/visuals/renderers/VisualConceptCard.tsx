"use client";

import React from "react";
import type { ConceptCardVisualization } from "../types";
import { getSubjectTheme, type SubjectTheme } from "../subjectThemes";

interface VisualConceptCardProps {
  data: ConceptCardVisualization;
  theme?: SubjectTheme;
}

export const VisualConceptCard: React.FC<VisualConceptCardProps> = ({ data, theme: propTheme }) => {
  const theme = propTheme || getSubjectTheme(data?.subject);

  if (!data) {
    return (
      <div className="py-6 text-center font-sans text-xs" style={{ color: theme.colors.mutedInk }}>
        No concept card data available.
      </div>
    );
  }

  return (
    <article aria-label={data.title || "Concept Card"} className="w-full space-y-5 font-sans">
      {/* Definition inside Subject Highlighter Box */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span
            className="text-[10px] uppercase font-bold tracking-widest font-mono"
            style={{ color: theme.colors.primary }}
          >
            KEY CONCEPT DEFINITION
          </span>
          <span
            className="text-xs font-bold italic font-serif hidden sm:inline"
            style={{ color: theme.colors.handwritingInk }}
          >
            ★ REMEMBER THIS DEFINITION FOR EXAM!
          </span>
        </div>

        <div
          className="p-5 rounded-xl border-l-4 leading-relaxed shadow-xs"
          style={{
            backgroundColor: theme.colors.calloutBg,
            borderColor: theme.colors.calloutBorder,
            color: theme.colors.calloutText,
          }}
        >
          <span
            className="font-bold font-mono uppercase text-[11px] block mb-1"
            style={{ color: theme.colors.primary }}
          >
            Definition:
          </span>
          <p className="italic font-serif text-base sm:text-lg" style={{ color: theme.colors.ink }}>
            "{data.definition}"
          </p>
        </div>
      </div>

      {/* Core Principles List */}
      {data.keyIdeas && data.keyIdeas.length > 0 && (
        <div>
          <h3
            className="text-xs uppercase font-mono font-bold tracking-wider mb-2"
            style={{ color: theme.colors.primary }}
          >
            Core Takeaways & Insights
          </h3>
          <ul className="space-y-2">
            {data.keyIdeas.map((idea, idx) => (
              <li key={idx} className="flex items-start gap-2.5 text-xs">
                <span
                  className="font-bold font-mono"
                  style={{ color: theme.colors.handwritingInk }}
                >
                  ✓
                </span>
                <span className="leading-relaxed" style={{ color: theme.colors.ink }}>
                  {idea}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Supporting Note */}
      {data.supportingInfo && (
        <div
          className="p-3.5 rounded-xl border text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-xs"
          style={{
            backgroundColor: theme.colors.headerBg,
            borderColor: theme.colors.accentBorder,
            color: theme.colors.ink,
          }}
        >
          <div className="flex items-center gap-2">
            <span style={{ color: theme.colors.primary }} className="text-sm">
              💡
            </span>
            <div>
              <span className="font-bold font-mono" style={{ color: theme.colors.primary }}>
                Note:
              </span>{" "}
              {data.supportingInfo}
            </div>
          </div>
          <span
            className="text-xs font-bold italic font-serif flex-shrink-0"
            style={{ color: theme.colors.handwritingInk }}
          >
            "High exam probability!"
          </span>
        </div>
      )}
    </article>
  );
};
