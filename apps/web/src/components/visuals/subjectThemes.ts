import type { SubjectType } from "./types";

export interface NodeBgStyle {
  bg: string;
  border: string;
  text: string;
  tag: string;
}

export interface SubjectTheme {
  id: SubjectType | "default";
  name: string;
  code: string;
  topicDefault: string;
  badgeEmoji: string;
  colors: {
    pageBg: string;
    headerBg: string;
    headerBorder: string;
    paperBg: string;
    paperBorder: string;
    paperGridPattern: "dots" | "graph" | "lines" | "hex" | "parchment" | "code" | "contour";
    gridColor: string;
    marginLineColor: string;
    ink: string;
    mutedInk: string;
    primary: string;
    secondary: string;
    accent: string;
    accentBorder: string;
    handwritingInk: string;
    handCircleBorder: string;
    handCircleText: string;
    highlighterBg: string;
    highlighterBorder: string;
    highlighterText: string;
    calloutBg: string;
    calloutBorder: string;
    calloutText: string;
    nodeBgs: NodeBgStyle[];
    chartPrimary: string;
    chartSecondary: string;
    chartGrid: string;
    chartTooltipBg: string;
    chartTooltipText: string;
    badgeBg: string;
    badgeText: string;
  };
  visualMotifs: {
    icon: string;
    svgMotifType: "leaf" | "math" | "physics" | "chemistry" | "history" | "code" | "geography" | "default";
    symbolWatermark: string[];
    startInputLabel: string;
    startIcon: string;
    endOutputLabel: string;
    endIcon: string;
    intuitionQuote: string;
    takeawayQuote: string;
    keyRevisionTitle: string;
    keyRevisionNote: string;
    annotations: string[];
  };
}

export const subjectThemes: Record<SubjectType | "default", SubjectTheme> = {
  biology: {
    id: "biology",
    name: "Biology",
    code: "BIO 101",
    topicDefault: "Bioenergetics & Plant Metabolism",
    badgeEmoji: "🌿",
    colors: {
      pageBg: "#FAF0D7",
      headerBg: "#FFF8DC",
      headerBorder: "rgba(120, 53, 15, 0.15)",
      paperBg: "#FFFBEA",
      paperBorder: "rgba(120, 53, 15, 0.2)",
      paperGridPattern: "dots",
      gridColor: "#e2d8b2",
      marginLineColor: "#f87171",
      ink: "#172033",
      mutedInk: "#4a3728",
      primary: "#059669",
      secondary: "#0284c7",
      accent: "#f59e0b",
      accentBorder: "#fcd34d",
      handwritingInk: "#1d4ed8",
      handCircleBorder: "#1d4ed8",
      handCircleText: "#1e40af",
      highlighterBg: "#fef08a",
      highlighterBorder: "#fde047",
      highlighterText: "#5c4033",
      calloutBg: "rgba(254, 240, 138, 0.9)",
      calloutBorder: "#f59e0b",
      calloutText: "#5c4033",
      nodeBgs: [
        { bg: "bg-amber-100/90", border: "border-amber-400", text: "text-amber-950", tag: "text-amber-800" },
        { bg: "bg-sky-100/90", border: "border-sky-400", text: "text-sky-950", tag: "text-sky-800" },
        { bg: "bg-amber-100/90", border: "border-amber-400", text: "text-amber-950", tag: "text-amber-800" },
        { bg: "bg-emerald-100/90", border: "border-emerald-400", text: "text-emerald-950", tag: "text-emerald-800" },
      ],
      chartPrimary: "#16a34a",
      chartSecondary: "#0284c7",
      chartGrid: "#e2d8b2",
      chartTooltipBg: "#FFF8DC",
      chartTooltipText: "#1e3a8a",
      badgeBg: "#065f46",
      badgeText: "#fffbe5",
    },
    visualMotifs: {
      icon: "🌿",
      svgMotifType: "leaf",
      symbolWatermark: ["🌿", "🍃", "🔬", "🧫", "🧬"],
      startInputLabel: "SOLAR LIGHT ENERGY INPUT",
      startIcon: "☀",
      endOutputLabel: "GLUCOSE SUGAR (C₆H₁₂O₆) OUTPUT",
      endIcon: "🍃",
      intuitionQuote: '"Think of it as: Light Energy → Chemical Fuel (ATP) → Glucose Sugar"',
      takeawayQuote: '"Review daily for active recall! 🌿"',
      keyRevisionTitle: "KEY BIOLOGY REVISION NOTE:",
      keyRevisionNote: "Light-dependent reactions harvest photon energy to generate molecular ATP + NADPH fuel for carbon fixation.",
      annotations: [
        "energy captured here ↓",
        "water split into O₂ & H⁺",
        "ATP + NADPH fuel generated →",
        "carbon fixed into glucose sugar",
      ],
    },
  },

  mathematics: {
    id: "mathematics",
    name: "Mathematics",
    code: "MATH 201",
    topicDefault: "Algebraic Analysis & Calculus",
    badgeEmoji: "📐",
    colors: {
      pageBg: "#EBF3FB",
      headerBg: "#F0F6FF",
      headerBorder: "rgba(30, 58, 138, 0.15)",
      paperBg: "#FAFCFF",
      paperBorder: "rgba(30, 58, 138, 0.2)",
      paperGridPattern: "graph",
      gridColor: "#cbd5e1",
      marginLineColor: "#6366f1",
      ink: "#0f172a",
      mutedInk: "#334155",
      primary: "#2563eb",
      secondary: "#4f46e5",
      accent: "#0284c7",
      accentBorder: "#93c5fd",
      handwritingInk: "#312e81",
      handCircleBorder: "#312e81",
      handCircleText: "#1e1b4b",
      highlighterBg: "#e0e7ff",
      highlighterBorder: "#a5b4fc",
      highlighterText: "#1e1b4b",
      calloutBg: "rgba(224, 231, 255, 0.9)",
      calloutBorder: "#6366f1",
      calloutText: "#1e1b4b",
      nodeBgs: [
        { bg: "bg-indigo-100/90", border: "border-indigo-400", text: "text-indigo-950", tag: "text-indigo-800" },
        { bg: "bg-blue-100/90", border: "border-blue-400", text: "text-blue-950", tag: "text-blue-800" },
        { bg: "bg-slate-100/90", border: "border-slate-400", text: "text-slate-950", tag: "text-slate-800" },
        { bg: "bg-sky-100/90", border: "border-sky-400", text: "text-sky-950", tag: "text-sky-800" },
      ],
      chartPrimary: "#2563eb",
      chartSecondary: "#4f46e5",
      chartGrid: "#cbd5e1",
      chartTooltipBg: "#F0F6FF",
      chartTooltipText: "#1e1b4b",
      badgeBg: "#1e3a8a",
      badgeText: "#eff6ff",
    },
    visualMotifs: {
      icon: "📐",
      svgMotifType: "math",
      symbolWatermark: ["∑", "∫", "π", "f(x)", "x² + y² = r²", "Δy/Δx"],
      startInputLabel: "INITIAL GIVEN CONDITIONS / DOMAIN",
      startIcon: "f(x)",
      endOutputLabel: "FINAL SOLVED PROOF / RANGE",
      endIcon: "Q.E.D.",
      intuitionQuote: '"Think of it as: Input Domain → Transformation Function → Output Codomain"',
      takeawayQuote: '"Verify steps with active geometric substitution! 📐"',
      keyRevisionTitle: "KEY MATHEMATICAL DERIVATION:",
      keyRevisionNote: "Each transformation preserves equality while reducing algebraic complexity to isolate target variables.",
      annotations: [
        "given parameters ↓",
        "apply transformation rule",
        "substitute intermediate terms →",
        "simplified final proof",
      ],
    },
  },

  physics: {
    id: "physics",
    name: "Physics",
    code: "PHYS 150",
    topicDefault: "Classical Mechanics & Wave Dynamics",
    badgeEmoji: "⚡",
    colors: {
      pageBg: "#F0F4FA",
      headerBg: "#F4F8FC",
      headerBorder: "rgba(14, 116, 144, 0.15)",
      paperBg: "#FAFBFD",
      paperBorder: "rgba(14, 116, 144, 0.2)",
      paperGridPattern: "lines",
      gridColor: "#cbd5e1",
      marginLineColor: "#f59e0b",
      ink: "#0f172a",
      mutedInk: "#334155",
      primary: "#0284c7",
      secondary: "#d97706",
      accent: "#2563eb",
      accentBorder: "#fde047",
      handwritingInk: "#1e3a8a",
      handCircleBorder: "#0284c7",
      handCircleText: "#0369a1",
      highlighterBg: "#feecdc",
      highlighterBorder: "#fcd34d",
      highlighterText: "#78350f",
      calloutBg: "rgba(254, 236, 220, 0.9)",
      calloutBorder: "#d97706",
      calloutText: "#78350f",
      nodeBgs: [
        { bg: "bg-sky-100/90", border: "border-sky-400", text: "text-sky-950", tag: "text-sky-800" },
        { bg: "bg-amber-100/90", border: "border-amber-400", text: "text-amber-950", tag: "text-amber-800" },
        { bg: "bg-blue-100/90", border: "border-blue-400", text: "text-blue-950", tag: "text-blue-800" },
        { bg: "bg-orange-100/90", border: "border-orange-400", text: "text-orange-950", tag: "text-orange-800" },
      ],
      chartPrimary: "#0284c7",
      chartSecondary: "#d97706",
      chartGrid: "#cbd5e1",
      chartTooltipBg: "#F4F8FC",
      chartTooltipText: "#0c4a6e",
      badgeBg: "#0c4a6e",
      badgeText: "#f0f9ff",
    },
    visualMotifs: {
      icon: "⚡",
      svgMotifType: "physics",
      symbolWatermark: ["F=ma", "E=mc²", "λ", "ω", "v⃗", "⚙"],
      startInputLabel: "INITIAL FORCE & VECTOR INPUT",
      startIcon: "F⃗",
      endOutputLabel: "NET WORK DONE & KINETIC ENERGY",
      endIcon: "E_k",
      intuitionQuote: '"Think of it as: Applied Force Vector → Energy Transfer → Net Work Done"',
      takeawayQuote: '"Conservation of Energy always holds! ⚡"',
      keyRevisionTitle: "KEY PHYSICS PRINCIPLE:",
      keyRevisionNote: "Vector summation of external forces governs momentum conservation and kinetic energy exchange.",
      annotations: [
        "applied force vector ↓",
        "overcomes frictional inertia",
        "accelerates mass along axis →",
        "transfers kinetic work",
      ],
    },
  },

  chemistry: {
    id: "chemistry",
    name: "Chemistry",
    code: "CHEM 110",
    topicDefault: "Molecular Kinetics & Catalysis",
    badgeEmoji: "⚗️",
    colors: {
      pageBg: "#E6F5F3",
      headerBg: "#EDF8F6",
      headerBorder: "rgba(15, 118, 110, 0.15)",
      paperBg: "#F4FBF9",
      paperBorder: "rgba(15, 118, 110, 0.2)",
      paperGridPattern: "hex",
      gridColor: "#a7f3d0",
      marginLineColor: "#ec4899",
      ink: "#134e4a",
      mutedInk: "#2dd4bf",
      primary: "#0d9488",
      secondary: "#7c3aed",
      accent: "#f59e0b",
      accentBorder: "#a7f3d0",
      handwritingInk: "#581c87",
      handCircleBorder: "#0d9488",
      handCircleText: "#115e59",
      highlighterBg: "#ccfbf1",
      highlighterBorder: "#5eead4",
      highlighterText: "#134e4a",
      calloutBg: "rgba(204, 251, 241, 0.9)",
      calloutBorder: "#0d9488",
      calloutText: "#134e4a",
      nodeBgs: [
        { bg: "bg-teal-100/90", border: "border-teal-400", text: "text-teal-950", tag: "text-teal-800" },
        { bg: "bg-purple-100/90", border: "border-purple-400", text: "text-purple-950", tag: "text-purple-800" },
        { bg: "bg-cyan-100/90", border: "border-cyan-400", text: "text-cyan-950", tag: "text-cyan-800" },
        { bg: "bg-amber-100/90", border: "border-amber-400", text: "text-amber-950", tag: "text-amber-800" },
      ],
      chartPrimary: "#0d9488",
      chartSecondary: "#7c3aed",
      chartGrid: "#99f6e4",
      chartTooltipBg: "#EDF8F6",
      chartTooltipText: "#134e4a",
      badgeBg: "#115e59",
      badgeText: "#f0fdfa",
    },
    visualMotifs: {
      icon: "⚗️",
      svgMotifType: "chemistry",
      symbolWatermark: ["H₂O", "CO₂", "NaCl", "pH", "⚗️", "🧪"],
      startInputLabel: "REACTANTS & ACTIVATION ENERGY",
      startIcon: "⚗️",
      endOutputLabel: "STABLE PRODUCT MOLECULES",
      endIcon: "🧪",
      intuitionQuote: '"Think of it as: Reactants + Activation Energy → Transition Complex → Synthesized Products"',
      takeawayQuote: '"Catalysts lower activation energy barrier! ⚗️"',
      keyRevisionTitle: "KEY REACTION DYNAMICS:",
      keyRevisionNote: "Substrate binding lowers the transition state energy barrier, accelerating product synthesis rate.",
      annotations: [
        "reactant collision ↓",
        "exceeds activation threshold",
        "forms transition complex →",
        "yields stable molecular products",
      ],
    },
  },

  history: {
    id: "history",
    name: "History",
    code: "HIST 301",
    topicDefault: "World Revolutions & Archival Chronology",
    badgeEmoji: "📜",
    colors: {
      pageBg: "#F6F0E6",
      headerBg: "#FAF4EB",
      headerBorder: "rgba(120, 53, 15, 0.2)",
      paperBg: "#FAF4E8",
      paperBorder: "rgba(120, 53, 15, 0.25)",
      paperGridPattern: "parchment",
      gridColor: "#d7c5ae",
      marginLineColor: "#991b1b",
      ink: "#3b2314",
      mutedInk: "#5c4033",
      primary: "#78350f",
      secondary: "#991b1b",
      accent: "#d97706",
      accentBorder: "#f59e0b",
      handwritingInk: "#7c2d12",
      handCircleBorder: "#78350f",
      handCircleText: "#451a03",
      highlighterBg: "#fef3c7",
      highlighterBorder: "#fde047",
      highlighterText: "#451a03",
      calloutBg: "rgba(254, 243, 199, 0.9)",
      calloutBorder: "#b45309",
      calloutText: "#451a03",
      nodeBgs: [
        { bg: "bg-amber-100/90", border: "border-amber-500", text: "text-amber-950", tag: "text-amber-900" },
        { bg: "bg-orange-100/90", border: "border-orange-500", text: "text-orange-950", tag: "text-orange-900" },
        { bg: "bg-stone-100/90", border: "border-stone-400", text: "text-stone-950", tag: "text-stone-800" },
        { bg: "bg-rose-100/90", border: "border-rose-400", text: "text-rose-950", tag: "text-rose-900" },
      ],
      chartPrimary: "#78350f",
      chartSecondary: "#991b1b",
      chartGrid: "#d7c5ae",
      chartTooltipBg: "#FAF4EB",
      chartTooltipText: "#451a03",
      badgeBg: "#78350f",
      badgeText: "#fffbeb",
    },
    visualMotifs: {
      icon: "📜",
      svgMotifType: "history",
      symbolWatermark: ["📜", "🏛️", "🖋️", "⚔️", "👑", "⏳"],
      startInputLabel: "HISTORICAL ANTECEDENTS & CAUSES",
      startIcon: "📜",
      endOutputLabel: "LONG-TERM HISTORICAL CONSEQUENCES",
      endIcon: "🏛️",
      intuitionQuote: '"Think of it as: Structural Causes → Precipitating Event → Institutional Change"',
      takeawayQuote: '"Analyze primary archival sources carefully! 📜"',
      keyRevisionTitle: "KEY HISTORICAL ANALYSIS:",
      keyRevisionNote: "Economic shifts combined with ideological movements created irreversible systemic transformation.",
      annotations: [
        "underlying socio-economic tension ↓",
        "catalyst event triggers crisis",
        "mobilizes social movement →",
        "redefines institutional framework",
      ],
    },
  },

  computer_science: {
    id: "computer_science",
    name: "Computer Science",
    code: "CS 101",
    topicDefault: "Data Structures & Algorithmic Logic",
    badgeEmoji: "⌘",
    colors: {
      pageBg: "#F1F5F9",
      headerBg: "#F8FAFC",
      headerBorder: "rgba(30, 41, 59, 0.15)",
      paperBg: "#F8FAFC",
      paperBorder: "rgba(30, 41, 59, 0.2)",
      paperGridPattern: "code",
      gridColor: "#cbd5e1",
      marginLineColor: "#3b82f6",
      ink: "#0f172a",
      mutedInk: "#334155",
      primary: "#2563eb",
      secondary: "#059669",
      accent: "#0284c7",
      accentBorder: "#93c5fd",
      handwritingInk: "#0284c7",
      handCircleBorder: "#2563eb",
      handCircleText: "#1d4ed8",
      highlighterBg: "#dbeafe",
      highlighterBorder: "#93c5fd",
      highlighterText: "#1e3a8a",
      calloutBg: "rgba(219, 234, 254, 0.9)",
      calloutBorder: "#3b82f6",
      calloutText: "#1e3a8a",
      nodeBgs: [
        { bg: "bg-slate-100/90", border: "border-slate-400", text: "text-slate-950", tag: "text-slate-800" },
        { bg: "bg-blue-100/90", border: "border-blue-400", text: "text-blue-950", tag: "text-blue-800" },
        { bg: "bg-emerald-100/90", border: "border-emerald-400", text: "text-emerald-950", tag: "text-emerald-800" },
        { bg: "bg-cyan-100/90", border: "border-cyan-400", text: "text-cyan-950", tag: "text-cyan-800" },
      ],
      chartPrimary: "#2563eb",
      chartSecondary: "#059669",
      chartGrid: "#cbd5e1",
      chartTooltipBg: "#F8FAFC",
      chartTooltipText: "#0f172a",
      badgeBg: "#0f172a",
      badgeText: "#f8fafc",
    },
    visualMotifs: {
      icon: "⌘",
      svgMotifType: "code",
      symbolWatermark: ["{ }", "</>", "=>", "O(log n)", "if/else", "0101"],
      startInputLabel: "INITIAL INPUT STREAM / UNORDERED DATA",
      startIcon: "{ }",
      endOutputLabel: "OPTIMIZED RETURN VALUE / SORTED OUTPUT",
      endIcon: "</>",
      intuitionQuote: '"Think of it as: Input Data Structure → Algorithmic Processing → O(N) Output State"',
      takeawayQuote: '"Strive for logarithmic time complexity O(log N)! ⌘"',
      keyRevisionTitle: "KEY ALGORITHMIC ANALYSIS:",
      keyRevisionNote: "Divide-and-conquer strategy reduces search space by half in each recursive iteration step.",
      annotations: [
        "load input array ↓",
        "evaluate condition check",
        "branch execution path →",
        "return computed result",
      ],
    },
  },

  geography: {
    id: "geography",
    name: "Geography",
    code: "GEO 205",
    topicDefault: "Spatial Systems & Physical Earth Processes",
    badgeEmoji: "🗺️",
    colors: {
      pageBg: "#EFEFD6",
      headerBg: "#F6F6E5",
      headerBorder: "rgba(21, 128, 61, 0.15)",
      paperBg: "#FAF9F0",
      paperBorder: "rgba(21, 128, 61, 0.2)",
      paperGridPattern: "contour",
      gridColor: "#c2d6b4",
      marginLineColor: "#0284c7",
      ink: "#1c3d29",
      mutedInk: "#375241",
      primary: "#15803d",
      secondary: "#0284c7",
      accent: "#d97706",
      accentBorder: "#86efac",
      handwritingInk: "#166534",
      handCircleBorder: "#15803d",
      handCircleText: "#14532d",
      highlighterBg: "#dcfce7",
      highlighterBorder: "#86efac",
      highlighterText: "#14532d",
      calloutBg: "rgba(220, 252, 231, 0.9)",
      calloutBorder: "#15803d",
      calloutText: "#14532d",
      nodeBgs: [
        { bg: "bg-emerald-100/90", border: "border-emerald-400", text: "text-emerald-950", tag: "text-emerald-800" },
        { bg: "bg-sky-100/90", border: "border-sky-400", text: "text-sky-950", tag: "text-sky-800" },
        { bg: "bg-lime-100/90", border: "border-lime-400", text: "text-lime-950", tag: "text-lime-800" },
        { bg: "bg-amber-100/90", border: "border-amber-400", text: "text-amber-950", tag: "text-amber-800" },
      ],
      chartPrimary: "#15803d",
      chartSecondary: "#0284c7",
      chartGrid: "#c2d6b4",
      chartTooltipBg: "#F6F6E5",
      chartTooltipText: "#14532d",
      badgeBg: "#14532d",
      badgeText: "#f0fdf4",
    },
    visualMotifs: {
      icon: "🗺️",
      svgMotifType: "geography",
      symbolWatermark: ["🗺️", "⛰️", "🌊", "🧭", "🌋", "📍"],
      startInputLabel: "GEOGRAPHIC REGION & CLIMATIC FORCING",
      startIcon: "🗺️",
      endOutputLabel: "GEOMORPHIC LANDFORM / SPATIAL PATTERN",
      endIcon: "⛰️",
      intuitionQuote: '"Think of it as: Tectonic / Climate Drivers → Environmental Interaction → Spatial Landform"',
      takeawayQuote: '"Spatial distribution reflects environmental feedback loops! 🗺️"',
      keyRevisionTitle: "KEY GEOGRAPHIC INSIGHT:",
      keyRevisionNote: "Plate boundary interactions combined with atmospheric weathering shape regional landforms over geological epochs.",
      annotations: [
        "solar radiation / tectonic drive ↓",
        "evaporation & cloud transport",
        "precipitation & river runoff →",
        "sedimentation & delta buildup",
      ],
    },
  },

  default: {
    id: "default",
    name: "General Academic",
    code: "NOTEBOOK 101",
    topicDefault: "General Revision & Academic Study Notes",
    badgeEmoji: "📚",
    colors: {
      pageBg: "#FAF0D7",
      headerBg: "#FFF8DC",
      headerBorder: "rgba(120, 53, 15, 0.15)",
      paperBg: "#FFFBEA",
      paperBorder: "rgba(120, 53, 15, 0.2)",
      paperGridPattern: "dots",
      gridColor: "#e2d8b2",
      marginLineColor: "#f87171",
      ink: "#172033",
      mutedInk: "#4a3728",
      primary: "#1d4ed8",
      secondary: "#0284c7",
      accent: "#f59e0b",
      accentBorder: "#fde047",
      handwritingInk: "#1d4ed8",
      handCircleBorder: "#1d4ed8",
      handCircleText: "#1e40af",
      highlighterBg: "#fef08a",
      highlighterBorder: "#fde047",
      highlighterText: "#5c4033",
      calloutBg: "rgba(254, 240, 138, 0.9)",
      calloutBorder: "#f59e0b",
      calloutText: "#5c4033",
      nodeBgs: [
        { bg: "bg-amber-100/90", border: "border-amber-400", text: "text-amber-950", tag: "text-amber-800" },
        { bg: "bg-sky-100/90", border: "border-sky-400", text: "text-sky-950", tag: "text-sky-800" },
        { bg: "bg-slate-100/90", border: "border-slate-400", text: "text-slate-950", tag: "text-slate-800" },
        { bg: "bg-emerald-100/90", border: "border-emerald-400", text: "text-emerald-950", tag: "text-emerald-800" },
      ],
      chartPrimary: "#1d4ed8",
      chartSecondary: "#0284c7",
      chartGrid: "#e2d8b2",
      chartTooltipBg: "#FFF8DC",
      chartTooltipText: "#1e3a8a",
      badgeBg: "#1e3a8a",
      badgeText: "#fffbe5",
    },
    visualMotifs: {
      icon: "📚",
      svgMotifType: "default",
      symbolWatermark: ["📚", "✍️", "💡", "📌", "⭐"],
      startInputLabel: "INITIAL CONCEPT INPUT",
      startIcon: "💡",
      endOutputLabel: "FINAL COMPREHENSION OUTPUT",
      endIcon: "⭐",
      intuitionQuote: '"Think of it as: Core Concept → Structuring Information → Mastery & Recall"',
      takeawayQuote: '"Consistent daily active recall yields long-term retention! 📚"',
      keyRevisionTitle: "KEY STUDY TAKEAWAY:",
      keyRevisionNote: "Synthesizing complex topics into structured visual diagrams accelerates conceptual understanding.",
      annotations: [
        "input concept definition ↓",
        "examine components",
        "analyze relationships →",
        "synthesize main summary",
      ],
    },
  },
};

/**
 * Normalizes subject string and resolves corresponding SubjectTheme.
 * Defaults safely to `subjectThemes.default` if unknown or unprovided.
 */
export function getSubjectTheme(subject?: string | null): SubjectTheme {
  if (!subject) return subjectThemes.default;

  const key = subject.toLowerCase().trim().replace(/[\s-]/g, "_");

  if (key in subjectThemes) {
    return subjectThemes[key as SubjectType];
  }

  // Alias checks
  if (key.includes("bio") || key.includes("botany") || key.includes("zoology") || key.includes("life")) {
    return subjectThemes.biology;
  }
  if (key.includes("math") || key.includes("algebra") || key.includes("calculus") || key.includes("geom")) {
    return subjectThemes.mathematics;
  }
  if (key.includes("phys") || key.includes("mech") || key.includes("wave") || key.includes("optics")) {
    return subjectThemes.physics;
  }
  if (key.includes("chem") || key.includes("molecul") || key.includes("reaction") || key.includes("organic")) {
    return subjectThemes.chemistry;
  }
  if (key.includes("hist") || key.includes("archive") || key.includes("civic") || key.includes("epoch")) {
    return subjectThemes.history;
  }
  if (key.includes("cs") || key.includes("comp") || key.includes("code") || key.includes("algorithm") || key.includes("software")) {
    return subjectThemes.computer_science;
  }
  if (key.includes("geo") || key.includes("map") || key.includes("earth") || key.includes("terrain") || key.includes("spatial")) {
    return subjectThemes.geography;
  }

  return subjectThemes.default;
}
