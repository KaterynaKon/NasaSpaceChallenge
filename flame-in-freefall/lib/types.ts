// Types for the Flame in Freefall dataset.
// Keep in sync with handoff/DATA_CONTRACT.md.

export type EnvironmentId = "cabin" | "habitat" | "suit" | "rover";

export type Badge = "table parsed" | "samples only" | "from report" | "estimated";

export type FuelType = "solid" | "liquid" | "gaseous" | "mixed" | "unknown";

export interface ScorePart {
  label: string;
  points: number;
  max: number;
  why: string;
}

export interface Publication {
  title: string;
  venue: string;
  year: string;
  citations: number;
  openAccess: boolean;
  url: string;
}

export interface Finding {
  text: string;
  source: string;
  doi?: string;
  url?: string;
}

export interface Hardware {
  name: string;
  url: string;
}

export interface DataFiles {
  count: number;
  sizeGb: number;
}

export interface Investigation {
  id: string;
  badge: Badge;
  name: string;
  fullName: string;
  category: string;
  platform: string;
  years: string;
  year: number | null;
  fuelTypes: FuelType[];
  testedMaterials: string[];
  fuelLabel: string;
  o2Label: string;
  o2Max: number | null;
  pressureLabel: string;
  flowLabel: string;
  hardware: Hardware;
  dataFiles: DataFiles;
  samples: number;
  tags: string[];
  /** Legacy: cabin score. Use scores[env]. */
  score: number;
  scores: Record<EnvironmentId, number>;
  scoreParts: Record<EnvironmentId, ScorePart[]>;
  findings: Finding[];
  publications: Publication[];
  sourceUrl: string;
  image: string | null;
  imageCaption: string | null;
}

export interface EnvironmentSource {
  label: string;
  url: string;
}

export interface EnvironmentInfo {
  id: EnvironmentId;
  label: string;
  o2: string;
  pressure: string;
  flow: string;
  material: string;
  description: string;
  /** Non-empty when a number is an estimate rather than a published figure. */
  assumption: string;
  sources: EnvironmentSource[];
}

// --- Aliases kept for the existing components ---------------------------

/** Same four environments, older name used by lib/data.ts and components. */
export type Environment = EnvironmentId;

/** Filter dimension: fuel state or material group. */
export type Dimension = "fuel" | "material";

/** Sort order for the ranking list. */
export type SortKey = "relevance" | "o2" | "year";