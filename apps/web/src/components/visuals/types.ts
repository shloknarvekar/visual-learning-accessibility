export type VisualizationType =
  | "process"
  | "concept_map"
  | "bar_chart"
  | "line_chart"
  | "comparison"
  | "timeline"
  | "concept_card";

export type SubjectType =
  | "biology"
  | "mathematics"
  | "physics"
  | "chemistry"
  | "history"
  | "computer_science"
  | "geography";

export interface ProcessStep {
  id: string;
  label: string;
  description?: string;
  icon?: string;
}

export interface ProcessVisualization {
  type: "process";
  subject?: SubjectType | string;
  title: string;
  description?: string;
  steps: ProcessStep[];
}

export interface ConceptNode {
  id: string;
  label: string;
  description?: string;
  category?: string;
  x?: number;
  y?: number;
}

export interface ConceptEdge {
  source: string;
  target: string;
  relationship: string;
}

export interface ConceptMapVisualization {
  type: "concept_map";
  subject?: SubjectType | string;
  title: string;
  description?: string;
  nodes: ConceptNode[];
  edges: ConceptEdge[];
}

export interface ChartDataItem {
  label: string;
  value: number;
  category?: string;
  color?: string;
}

export interface BarChartVisualization {
  type: "bar_chart";
  subject?: SubjectType | string;
  title: string;
  description?: string;
  xAxisLabel?: string;
  yAxisLabel?: string;
  unit?: string;
  data: ChartDataItem[];
}

export interface LineChartVisualization {
  type: "line_chart";
  subject?: SubjectType | string;
  title: string;
  description?: string;
  xAxisLabel?: string;
  yAxisLabel?: string;
  unit?: string;
  data: ChartDataItem[];
}

export interface ComparisonRow {
  feature: string;
  values: string[];
  highlightIndex?: number;
}

export interface ComparisonVisualization {
  type: "comparison";
  subject?: SubjectType | string;
  title: string;
  description?: string;
  columns: string[];
  rows: ComparisonRow[];
}

export interface TimelineEvent {
  date: string;
  title: string;
  description: string;
  category?: string;
}

export interface TimelineVisualization {
  type: "timeline";
  subject?: SubjectType | string;
  title: string;
  description?: string;
  events: TimelineEvent[];
}

export interface ConceptCardVisualization {
  type: "concept_card";
  subject?: SubjectType | string;
  title: string;
  definition: string;
  keyIdeas: string[];
  supportingInfo?: string;
  icon?: string;
}

export type VisualizationData =
  | ProcessVisualization
  | ConceptMapVisualization
  | BarChartVisualization
  | LineChartVisualization
  | ComparisonVisualization
  | TimelineVisualization
  | ConceptCardVisualization;
