/* Generated from lesson.schema.json by `npm run contracts:generate`. Do not edit by hand. */

/**
 * Identifier, unique within its parent collection. Safe for use in URLs and HTML ids.
 */
export type Id = string;
/**
 * Non-empty plain text. No HTML or Markdown.
 */
export type PlainText = string;
export type SourceType = "youtube" | "pdf";
/**
 * One block of lesson content. `type` determines the shape of `content`.
 */
export type Section =
  | ConceptSection
  | ExplanationSection
  | ProcessSection
  | ComparisonSection
  | TimelineSection
  | ExampleSection
  | ConceptMapSection
  | DiagramSection
  | ChartSection;
/**
 * Non-empty plain text. No HTML or Markdown.
 */
export type PlainText1 = string;
/**
 * Plain-language description of what a visual shows. Used as its text alternative.
 */
export type VisualSummary = string;
/**
 * Non-empty plain text. No HTML or Markdown.
 */
export type PlainText2 = string;
/**
 * Identifier, unique within its parent collection. Safe for use in URLs and HTML ids.
 */
export type Id1 = string;
/**
 * Non-empty plain text. No HTML or Markdown.
 */
export type PlainText3 = string;

/**
 * A structured, visual-first lesson built from educational source material. Every human-readable string is plain text: no HTML and no Markdown. Renderers choose presentation from each section's `type`.
 */
export interface Lesson {
  /**
   * Version of this contract. Changes that break existing consumers bump this value.
   */
  schema_version: "0.1.0";
  id: Id;
  title: PlainText;
  overview: PlainText;
  source: Source;
  /**
   * Ordered lesson content. Render in array order.
   *
   * @minItems 1
   */
  sections: [Section, ...Section[]];
  /**
   * Checkpoint questions. May be empty.
   */
  quiz: QuizQuestion[];
}
/**
 * The material the lesson was generated from.
 */
export interface Source {
  source_type: SourceType;
  title: PlainText;
  /**
   * Original location, for example the YouTube video URL.
   */
  url?: string;
  /**
   * Display name of an uploaded file. Sanitised by the API; never a server path.
   */
  filename?: string;
}
export interface ConceptSection {
  id: Id;
  type: "concept";
  title: PlainText;
  source_references?: SourceReference[];
  content: ConceptContent;
}
/**
 * Points back to where content came from in the source. Use the locators that apply: page_number for PDFs, time range for videos.
 */
export interface SourceReference {
  page_number?: number;
  start_time_seconds?: number;
  end_time_seconds?: number;
  /**
   * Short verbatim quote from the source.
   */
  excerpt?: string;
}
/**
 * A key term with its definition.
 */
export interface ConceptContent {
  term: PlainText;
  definition: PlainText;
  key_points?: PlainText[];
}
export interface ExplanationSection {
  id: Id;
  type: "explanation";
  title: PlainText;
  source_references?: SourceReference[];
  content: ExplanationContent;
}
/**
 * A short, clear explanation in literal language.
 */
export interface ExplanationContent {
  body: PlainText;
  key_points?: PlainText[];
}
export interface ProcessSection {
  id: Id;
  type: "process";
  title: PlainText;
  source_references?: SourceReference[];
  content: ProcessContent;
}
/**
 * Ordered steps. Render in array order.
 */
export interface ProcessContent {
  /**
   * @minItems 1
   */
  steps: [ProcessStep, ...ProcessStep[]];
}
export interface ProcessStep {
  id: Id;
  title: PlainText;
  description: PlainText;
}
export interface ComparisonSection {
  id: Id;
  type: "comparison";
  title: PlainText;
  source_references?: SourceReference[];
  content: ComparisonContent;
}
/**
 * A comparison table. `items` are the things compared (columns); each row compares them on one criterion.
 */
export interface ComparisonContent {
  /**
   * @minItems 2
   */
  items: [PlainText, PlainText, ...PlainText[]];
  /**
   * @minItems 1
   */
  rows: [ComparisonRow, ...ComparisonRow[]];
}
/**
 * values[i] describes items[i]. The API guarantees values has the same length as items.
 */
export interface ComparisonRow {
  criterion: PlainText;
  /**
   * @minItems 2
   */
  values: [PlainText, PlainText, ...PlainText[]];
}
export interface TimelineSection {
  id: Id;
  type: "timeline";
  title: PlainText;
  source_references?: SourceReference[];
  content: TimelineContent;
}
/**
 * Chronological events. Render in array order.
 */
export interface TimelineContent {
  /**
   * @minItems 1
   */
  events: [TimelineEvent, ...TimelineEvent[]];
}
export interface TimelineEvent {
  id: Id;
  time_label: PlainText1;
  title: PlainText;
  description: PlainText;
}
export interface ExampleSection {
  id: Id;
  type: "example";
  title: PlainText;
  source_references?: SourceReference[];
  content: ExampleContent;
}
/**
 * A concrete scenario and how it connects to the lesson.
 */
export interface ExampleContent {
  scenario: PlainText;
  explanation: PlainText;
}
export interface ConceptMapSection {
  id: Id;
  type: "concept_map";
  title: PlainText;
  source_references?: SourceReference[];
  content: ConceptMapContent;
}
/**
 * Concepts (nodes) and labelled relationships between them (edges).
 */
export interface ConceptMapContent {
  summary: VisualSummary;
  /**
   * @minItems 1
   */
  nodes: [GraphNode, ...GraphNode[]];
  edges: GraphEdge[];
}
export interface GraphNode {
  id: Id;
  label: PlainText;
  description?: PlainText;
}
/**
 * A directed connection. from_id and to_id reference GraphNode ids in the same section; the API guarantees they exist.
 */
export interface GraphEdge {
  from_id: Id;
  to_id: Id;
  label?: PlainText2;
}
export interface DiagramSection {
  id: Id;
  type: "diagram";
  title: PlainText;
  source_references?: SourceReference[];
  content: DiagramContent;
}
/**
 * A structural diagram. `diagram_type` is a layout hint for the renderer.
 */
export interface DiagramContent {
  diagram_type: "flowchart" | "cycle" | "hierarchy";
  summary: VisualSummary;
  /**
   * @minItems 1
   */
  nodes: [GraphNode, ...GraphNode[]];
  edges: GraphEdge[];
}
export interface ChartSection {
  id: Id;
  type: "chart";
  title: PlainText;
  source_references?: SourceReference[];
  content: ChartContent;
}
/**
 * Numeric data from the source. Only used when the source contains real data.
 */
export interface ChartContent {
  chart_type: "bar" | "line" | "pie";
  summary: VisualSummary;
  x_axis_label?: PlainText;
  y_axis_label?: PlainText;
  unit?: PlainText;
  /**
   * @minItems 1
   */
  series: [ChartSeries, ...ChartSeries[]];
}
export interface ChartSeries {
  name: PlainText;
  /**
   * @minItems 1
   */
  points: [ChartPoint, ...ChartPoint[]];
}
export interface ChartPoint {
  label: PlainText;
  value: number;
}
export interface QuizQuestion {
  id: Id;
  type: "multiple_choice";
  prompt: PlainText;
  /**
   * @minItems 2
   */
  options: [QuizOption, QuizOption, ...QuizOption[]];
  correct_option_id: Id1;
  explanation: PlainText3;
  /**
   * Sections this question checks understanding of, for linking back to review content.
   */
  section_ids?: Id[];
  source_references?: SourceReference[];
}
export interface QuizOption {
  id: Id;
  text: PlainText;
}
