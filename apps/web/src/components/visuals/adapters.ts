import type { Section } from "@visual-learning/contracts";
import type {
  VisualizationData,
  ProcessVisualization,
  ConceptMapVisualization,
  BarChartVisualization,
  LineChartVisualization,
  ComparisonVisualization,
  TimelineVisualization,
  ConceptCardVisualization,
} from "./types";

/**
 * Adapter module to convert any `@visual-learning/contracts` Section object
 * into internal `VisualizationData` format consumable by `VisualizationRenderer`.
 *
 * Returns `null` for non-visual sections (`explanation`, `example`).
 */
export function adaptSectionToVisualization(
  section: Section,
  subject?: string,
): VisualizationData | null {
  if (!section) return null;

  switch (section.type) {
    case "process": {
      const { content, title } = section;
      const steps = (content?.steps || []).map((step) => ({
        id: step.id,
        label: step.title,
        description: step.description,
      }));

      return {
        type: "process",
        subject,
        title: title || "Process Steps",
        steps,
      } as ProcessVisualization;
    }

    case "concept_map": {
      const { content, title } = section;
      const nodes = (content?.nodes || []).map((node) => ({
        id: node.id,
        label: node.label,
        description: node.description,
      }));

      const edges = (content?.edges || []).map((edge) => ({
        source: edge.from_id,
        target: edge.to_id,
        relationship: edge.label || "",
      }));

      return {
        type: "concept_map",
        subject,
        title: title || "Concept Map",
        description: content?.summary,
        nodes,
        edges,
      } as ConceptMapVisualization;
    }

    case "diagram": {
      const { content, title } = section;
      const nodes = (content?.nodes || []).map((node) => ({
        id: node.id,
        label: node.label,
        description: node.description,
        category: content?.diagram_type,
      }));

      const edges = (content?.edges || []).map((edge) => ({
        source: edge.from_id,
        target: edge.to_id,
        relationship: edge.label || "",
      }));

      return {
        type: "concept_map",
        subject,
        title: title || "Diagram",
        description: content?.summary,
        nodes,
        edges,
      } as ConceptMapVisualization;
    }

    case "chart": {
      const { content, title } = section;
      const firstSeries = content?.series?.[0];
      const points = firstSeries?.points || [];

      const chartData = points.map((pt) => ({
        label: pt.label,
        value: pt.value,
      }));

      const isLine = content?.chart_type === "line";

      if (isLine) {
        return {
          type: "line_chart",
          subject,
          title: title || "Line Chart",
          description: content?.summary,
          xAxisLabel: content?.x_axis_label,
          yAxisLabel: content?.y_axis_label,
          unit: content?.unit,
          data: chartData,
        } as LineChartVisualization;
      }

      return {
        type: "bar_chart",
        subject,
        title: title || "Bar Chart",
        description: content?.summary,
        xAxisLabel: content?.x_axis_label,
        yAxisLabel: content?.y_axis_label,
        unit: content?.unit,
        data: chartData,
      } as BarChartVisualization;
    }

    case "comparison": {
      const { content, title } = section;
      const items = content?.items || [];
      const columns = ["Criterion", ...items];

      const rows = (content?.rows || []).map((row) => ({
        feature: row.criterion,
        values: row.values,
      }));

      return {
        type: "comparison",
        subject,
        title: title || "Comparison Table",
        columns,
        rows,
      } as ComparisonVisualization;
    }

    case "timeline": {
      const { content, title } = section;
      const events = (content?.events || []).map((evt) => ({
        date: evt.time_label,
        title: evt.title,
        description: evt.description,
      }));

      return {
        type: "timeline",
        subject,
        title: title || "Timeline",
        events,
      } as TimelineVisualization;
    }

    case "concept": {
      const { content, title } = section;
      return {
        type: "concept_card",
        subject,
        title: title || "Key Concept",
        definition: content ? `${content.term}: ${content.definition}` : "",
        keyIdeas: content?.key_points || [],
      } as ConceptCardVisualization;
    }

    case "explanation":
    case "example":
    default:
      return null;
  }
}
