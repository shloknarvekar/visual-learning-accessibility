"use client";

import React, { useState } from "react";
import type { ProcessVisualization } from "../types";
import { getSubjectTheme, type SubjectTheme } from "../subjectThemes";

interface ProcessRendererProps {
  data: ProcessVisualization;
  theme?: SubjectTheme;
}

export const ProcessRenderer: React.FC<ProcessRendererProps> = ({ data, theme: propTheme }) => {
  const [activeStep, setActiveStep] = useState<number | null>(null);

  const theme = propTheme || getSubjectTheme(data?.subject);

  if (!data || !data.steps || data.steps.length === 0) {
    return (
      <div className="py-6 text-center font-sans text-xs" style={{ color: theme.colors.mutedInk }}>
        No process steps available to render.
      </div>
    );
  }

  const annotations = theme.visualMotifs.annotations;
  const stageColors = theme.colors.nodeBgs;

  return (
    <section aria-label={data.title || "Process Flowchart"} className="w-full space-y-6">
      {data.description && (
        <p className="text-sm leading-relaxed max-w-3xl mb-4 font-sans" style={{ color: theme.colors.mutedInk }}>
          {data.description}
        </p>
      )}

      {/* Educational Infographic Process Diagram */}
      <div className="py-2">
        {/* Subject Start Input Graphic Header */}
        <div className="flex flex-col items-center justify-center mb-6 text-center">
          <div
            className="w-12 h-12 rounded-full flex items-center justify-center text-xl shadow-xs mb-1 font-bold"
            style={{
              backgroundColor: theme.colors.highlighterBg,
              borderColor: theme.colors.accent,
              borderWidth: "2px",
              color: theme.colors.ink,
            }}
          >
            {theme.visualMotifs.startIcon}
          </div>
          <span
            className="text-xs font-bold tracking-widest font-mono uppercase"
            style={{ color: theme.colors.primary }}
          >
            {theme.visualMotifs.startInputLabel}
          </span>
          <span
            className="text-base font-bold my-1 italic font-serif"
            style={{ color: theme.colors.handwritingInk }}
          >
            "{annotations[0] || "initial input stage ↓"}"
          </span>
        </div>

        {/* Illustrated Flow Steps connected by Pen Arrows */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 relative">
          {data.steps.map((step, index) => {
            const isSelected = activeStep === index;
            const isLast = index === data.steps.length - 1;
            const annotation = annotations[index] || annotations[index % annotations.length] || "";
            const colorStyle = stageColors[index % stageColors.length];

            return (
              <div key={step.id || index} className="flex flex-col items-center relative">
                {/* Visual Step Node */}
                <button
                  type="button"
                  onClick={() => setActiveStep(isSelected ? null : index)}
                  className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
                    colorStyle.bg
                  } ${colorStyle.border} ${
                    isSelected ? "ring-2 shadow-md scale-[1.02]" : "hover:shadow-sm"
                  }`}
                  style={
                    isSelected
                      ? {
                          borderColor: theme.colors.primary,
                          boxShadow: `0 4px 12px ${theme.colors.primary}25`,
                        }
                      : {}
                  }
                >
                  {/* Step Stage Header */}
                  <div
                    className="flex items-center justify-between pb-2 mb-2 border-b"
                    style={{ borderColor: `${theme.colors.ink}15` }}
                  >
                    <span
                      className="inline-flex items-center justify-center w-7 h-7 rounded-full border-2 text-xs font-bold font-mono"
                      style={{
                        borderColor: theme.colors.handCircleBorder,
                        color: theme.colors.handCircleText,
                      }}
                    >
                      0{index + 1}
                    </span>
                    <span
                      className="text-xs font-mono font-bold uppercase tracking-wider"
                      style={{ color: theme.colors.primary }}
                    >
                      STAGE 0{index + 1}
                    </span>
                  </div>

                  <h3 className="text-sm font-bold mb-1.5 leading-snug font-sans" style={{ color: theme.colors.ink }}>
                    {step.label}
                  </h3>

                  {step.description && (
                    <p className="text-xs leading-relaxed" style={{ color: theme.colors.mutedInk }}>
                      {step.description}
                    </p>
                  )}
                </button>

                {/* Handwritten Annotation floating near step */}
                {annotation && (
                  <span
                    className="text-xs font-bold italic font-serif mt-2 text-center"
                    style={{ color: theme.colors.handwritingInk }}
                  >
                    "{annotation}"
                  </span>
                )}

                {/* Pen Arrow Connectors between steps */}
                {!isLast && (
                  <div
                    className="hidden md:flex absolute -right-4 top-1/3 -translate-y-1/2 z-10 text-xl font-bold font-mono"
                    style={{ color: theme.colors.handwritingInk }}
                  >
                    ➔
                  </div>
                )}

                {!isLast && (
                  <div
                    className="md:hidden flex justify-center my-3 text-xl font-bold font-mono"
                    style={{ color: theme.colors.handwritingInk }}
                  >
                    ↓
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Subject End Output Footer */}
        <div className="flex flex-col items-center justify-center mt-8 text-center">
          <span
            className="text-base font-bold my-1 italic font-serif"
            style={{ color: theme.colors.handwritingInk }}
          >
            "{annotations[annotations.length - 1] || "final output state ↓"}"
          </span>
          <div
            className="w-12 h-12 rounded-full flex items-center justify-center text-xl shadow-xs mb-1 font-bold"
            style={{
              backgroundColor: theme.colors.highlighterBg,
              borderColor: theme.colors.primary,
              borderWidth: "2px",
              color: theme.colors.primary,
            }}
          >
            {theme.visualMotifs.endIcon}
          </div>
          <span
            className="text-xs font-bold tracking-widest font-mono uppercase"
            style={{ color: theme.colors.primary }}
          >
            {theme.visualMotifs.endOutputLabel}
          </span>
        </div>
      </div>

      {/* Key Study Note (Subject Highlighter Callout) */}
      <div
        className="p-4 rounded-xl border-l-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs"
        style={{
          backgroundColor: theme.colors.calloutBg,
          borderColor: theme.colors.calloutBorder,
          color: theme.colors.calloutText,
        }}
      >
        <div className="flex items-start gap-2.5">
          <span className="text-base flex-shrink-0">💡</span>
          <div>
            <span
              className="font-bold uppercase text-xs tracking-wider block mb-0.5 font-mono"
              style={{ color: theme.colors.primary }}
            >
              {theme.visualMotifs.keyRevisionTitle}
            </span>
            <p className="text-xs sm:text-sm leading-relaxed" style={{ color: theme.colors.ink }}>
              {theme.visualMotifs.keyRevisionNote}
            </p>
          </div>
        </div>
        <span
          className="text-xs sm:text-sm font-bold italic font-serif flex-shrink-0 bg-white/70 px-3 py-1 rounded-full border"
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
