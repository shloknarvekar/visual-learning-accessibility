"use client";

import React, { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";
import type { SubjectType, VisualizationData } from "./types";
import { getSubjectTheme, type SubjectTheme } from "./subjectThemes";
import { ProcessRenderer } from "./renderers/ProcessRenderer";
import { ConceptMapRenderer } from "./renderers/ConceptMapRenderer";
import { ChartRenderer } from "./renderers/ChartRenderer";
import { ComparisonRenderer } from "./renderers/ComparisonRenderer";
import { TimelineRenderer } from "./renderers/TimelineRenderer";
import { VisualConceptCard } from "./renderers/VisualConceptCard";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallbackTitle?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

class VisualizationErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public state: ErrorBoundaryState = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Visualization error captured:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="w-full max-w-5xl mx-auto p-6 bg-rose-50/60 rounded-2xl border border-rose-200 text-[#172033]">
          <div className="flex items-center gap-3 mb-2 text-rose-800 font-bold text-sm">
            <span>⚠️</span>
            <span>Unable to render visualization note ({this.props.fallbackTitle || "Unknown"})</span>
          </div>
          <p className="text-xs text-[#5B6472]">
            An error occurred while displaying this study component. The rest of the lesson content remains unaffected.
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}

export interface VisualizationRendererProps {
  data?: VisualizationData | null;
  subject?: SubjectType | string;
  theme?: SubjectTheme;
}

export const VisualizationRenderer: React.FC<VisualizationRendererProps> = ({
  data,
  subject,
  theme: propTheme,
}) => {
  const resolvedTheme = propTheme || getSubjectTheme(data?.subject || subject);

  if (!data) {
    return (
      <div className="w-full max-w-5xl mx-auto p-6 bg-white rounded-xl border border-slate-200 text-center text-[#5B6472] text-xs">
        No visualization note data provided.
      </div>
    );
  }

  const renderContent = () => {
    switch (data.type) {
      case "process":
        return <ProcessRenderer data={data} theme={resolvedTheme} />;
      case "concept_map":
        return <ConceptMapRenderer data={data} theme={resolvedTheme} />;
      case "bar_chart":
      case "line_chart":
        return <ChartRenderer data={data} theme={resolvedTheme} />;
      case "comparison":
        return <ComparisonRenderer data={data} theme={resolvedTheme} />;
      case "timeline":
        return <TimelineRenderer data={data} theme={resolvedTheme} />;
      case "concept_card":
        return <VisualConceptCard data={data} theme={resolvedTheme} />;
      default:
        return (
          <div className="w-full max-w-5xl mx-auto p-6 bg-amber-50/70 rounded-xl border border-amber-200 text-amber-900 text-xs font-mono">
            <span className="font-bold">Unsupported Visualization Type:</span>{" "}
            {(data as { type?: string })?.type || "Unknown"}
          </div>
        );
    }
  };

  return (
    <VisualizationErrorBoundary fallbackTitle={data.title || data.type}>
      {renderContent()}
    </VisualizationErrorBoundary>
  );
};
