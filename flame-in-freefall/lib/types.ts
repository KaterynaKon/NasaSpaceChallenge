export type Breakdown = { oxygen: number; materials: number; gravity: number; flow: number };

export type Finding = { text: string; source: string; doi?: string };

export type Publication = {
  title: string;
  venue: string;
  year: number;
  citations?: number;
  openAccess?: boolean;
  url: string;
  kind?: "paper" | "pdf";
};

export type Investigation = {
  id: string;
  name: string;
  fullName: string;
  category: string;      // e.g. "Solid materials"
  year: number;          // used for sorting
  fuels: string[];       // used by the Fuel filter, e.g. "100% C2H4"
  materials: string[];   // used by the Material filter, e.g. "Teflon"
  fuelLabel: string;     // stat tile: "Solid"
  o2Label: string;       // stat tile: "21–30%"
  o2Max: number;         // used for sorting
  flowLabel: string;     // stat tile: "0–20 cm/s"
  samples: number;
  tags: string[];
  score: number;         // relevance for Lunar Base, 0–100
  breakdown: Breakdown;
  findings: Finding[];
  publications: Publication[];
};

export type Dimension = "fuel" | "material";
export type SortKey = "relevance" | "o2" | "year";
