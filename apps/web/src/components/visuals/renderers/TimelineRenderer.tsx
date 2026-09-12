"use client";

import React from "react";
import type { TimelineVisualization } from "../types";
import { getSubjectTheme, type SubjectTheme } from "../subjectThemes";

interface TimelineRendererProps {
  data: TimelineVisualization;
  theme?: SubjectTheme;
}

export const TimelineRenderer: React.FC<TimelineRendererProps> = ({ data, theme: propTheme }) => {
  const theme = propTheme || getSubjectTheme(data?.subject);

  if (!data || !data.events || data.events.length === 0) {
    return (
      <div className="py-6 text-center font-sans text-xs" style={{ color: theme.colors.mutedInk }}>
        No timeline events available to render.
      </div>
    );
  }

  return (
    <section aria-label={data.title || "Historical Timeline"} className="w-full space-y-4 font-sans">
      {data.description && (
        <p className="text-sm leading-relaxed max-w-3xl mb-4 font-sans" style={{ color: theme.colors.mutedInk }}>
          {data.description}
        </p>
      )}

      {/* Vertical Discovery Timeline Axis */}
      <div
        className="relative border-l-2 ml-4 sm:ml-28 space-y-6 py-2"
        style={{ borderColor: theme.colors.handwritingInk }}
      >
        {data.events.map((event, idx) => (
          <div key={idx} className="relative pl-6 group">
            {/* Timeline Dot */}
            <div
              className="absolute -left-[9px] top-1.5 w-4 h-4 rounded-full border-2 transition-all group-hover:scale-110"
              style={{
                backgroundColor: theme.colors.paperBg,
                borderColor: theme.colors.handwritingInk,
              }}
            />

            {/* Date Badge on Left Margin */}
            <div
              className="hidden sm:block absolute -left-32 top-0.5 w-24 text-right italic font-serif text-sm font-bold"
              style={{ color: theme.colors.handwritingInk }}
            >
              {event.date}
            </div>

            {/* Event Block */}
            <div
              className="p-3.5 border rounded-xl shadow-xs"
              style={{
                backgroundColor: theme.colors.paperBg,
                borderColor: theme.colors.paperBorder,
              }}
            >
              <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
                <span
                  className="sm:hidden text-xs italic font-serif font-bold"
                  style={{ color: theme.colors.handwritingInk }}
                >
                  {event.date}
                </span>
                <h3 className="font-bold text-sm font-serif" style={{ color: theme.colors.ink }}>
                  {event.title}
                </h3>
                {event.category && (
                  <span
                    className="text-[10px] uppercase font-mono tracking-wider font-bold"
                    style={{ color: theme.colors.primary }}
                  >
                    {event.category}
                  </span>
                )}
              </div>
              <p className="text-xs leading-relaxed" style={{ color: theme.colors.mutedInk }}>
                {event.description}
              </p>
            </div>
          </div>
        ))}
      </div>

      <div className="pt-2 text-right">
        <span className="text-xs sm:text-sm font-bold italic font-serif" style={{ color: theme.colors.handwritingInk }}>
          {theme.visualMotifs.takeawayQuote}
        </span>
      </div>
    </section>
  );
};
