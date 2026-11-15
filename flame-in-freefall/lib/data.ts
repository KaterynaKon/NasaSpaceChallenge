// Single entry point for the dataset.
// Components import from here, never from the JSON files directly.
//
// The exported API is the same as before (getInvestigation, scoreFor,
// getFilterOptions, filterAndSort) so existing components keep compiling.
// New helpers at the bottom are for the redesigned dashboard.

import raw from "@/data/dashboard_data.json";
import envRaw from "@/data/environments.json";
import type {
  Dimension,
  Environment,
  EnvironmentId,
  EnvironmentInfo,
  Investigation,
  ScorePart,
  SortKey,
} from "./types";

export const investigations = raw as unknown as Investigation[];
export const environments = envRaw as unknown as EnvironmentInfo[];

export const DEFAULT_ENV: EnvironmentId = "cabin";

export function getInvestigation(id: string) {
  return investigations.find((i) => i.id.toLowerCase() === id.toLowerCase());
}

export function scoreFor(item: Investigation, env: Environment): number {
  return item.scores?.[env] ?? item.score;
}

// --- Filter groups -------------------------------------------------------
// testedMaterials is free text ("75% cotton and 25% fiberglass (by mass)"), so we
// map it onto a few clean groups. Better long term: add a materialGroups field to the JSON.
const MATERIAL_RULES: [string, string[]][] = [
  ["PMMA", ["pmma", "polymethyl"]],
  ["Cotton / fiberglass", ["cotton", "fiberglass", "sibal"]],
  ["Nomex", ["nomex"]],
  ["Silicone", ["silicone"]],
  ["Wax", ["wax"]],
  ["Foam", ["pyrell", "foam"]],
];
const OTHER = "Other";
const NOT_STATED = "Not stated";
const MATERIAL_ORDER = [...MATERIAL_RULES.map(([g]) => g), OTHER, NOT_STATED];
const FUEL_ORDER_BASE = ["solid", "liquid", "gaseous", "unknown"];

function materialGroups(item: Investigation): string[] {
  if (!item.testedMaterials?.length) return [NOT_STATED];
  const text = item.testedMaterials.join(" ").toLowerCase();
  const groups = MATERIAL_RULES.filter(([, keys]) =>
    keys.some((k) => text.includes(k))
  ).map(([g]) => g);
  return groups.length ? groups : [OTHER];
}

function fuelGroups(item: Investigation): string[] {
  return item.fuelTypes?.length
    ? item.fuelTypes.map((f) => f.toLowerCase())
    : ["unknown"];
}

function groupsFor(item: Investigation, dimension: Dimension) {
  return dimension === "fuel" ? fuelGroups(item) : materialGroups(item);
}

export function getFilterOptions(dimension: Dimension): string[] {
  const present = new Set(
    investigations.flatMap((i) => groupsFor(i, dimension))
  );
  const order = dimension === "fuel" ? FUEL_ORDER_BASE : MATERIAL_ORDER;
  return order.filter((o) => present.has(o));
}

// --- Filter + sort ------------------------------------------------------
export function filterAndSort(
  dimension: Dimension,
  value: string | null,
  sort: SortKey,
  env: Environment
): Investigation[] {
  const list = value
    ? investigations.filter((i) => groupsFor(i, dimension).includes(value))
    : [...investigations];

  const sorters: Record<
    SortKey,
    (a: Investigation, b: Investigation) => number
  > = {
    relevance: (a, b) => scoreFor(b, env) - scoreFor(a, env),
    o2: (a, b) => (b.o2Max ?? -1) - (a.o2Max ?? -1), // unknown O2 goes last
    year: (a, b) => (b.year ?? -1) - (a.year ?? -1), // unknown year goes last
  };
  return list.sort(sorters[sort]);
}

// --- Environment helpers -------------------------------------------------

export function getEnvironment(id: string): EnvironmentInfo {
  return environments.find((e) => e.id === id) ?? environments[0];
}

/** Ranked list for one environment. Never mutates the source array. */
export function rankBy(env: Environment): Investigation[] {
  return [...investigations].sort((a, b) => b.scores[env] - a.scores[env]);
}

/** The five scored components for one environment. */
export function partsOf(item: Investigation, env: Environment): ScorePart[] {
  return item.scoreParts?.[env] ?? [];
}

/** How many investigations have a table with numeric conditions. */
export function countWithTable(): number {
  return investigations.filter((i) => i.badge === "table parsed").length;
}

export function imageUrl(item: Investigation): string | null {
  return item.image ? `/assets/nasa/${item.image}` : null;
}

// --- Fuel chips ----------------------------------------------------------

export const FUEL_KEYS = ["all", "solid", "liquid", "gaseous", "unknown"] as const;

export type FuelKey = (typeof FUEL_KEYS)[number];

export const FUEL_LABEL: Record<FuelKey, string> = {
  all: "All",
  solid: "Solid",
  liquid: "Liquid",
  gaseous: "Gas",
  unknown: "Unknown",
};

function primaryFuel(item: Investigation): FuelKey {
  const first = item.fuelTypes?.[0];
  if (first === "solid" || first === "liquid" || first === "gaseous") return first;
  return "unknown";
}

export function fuelCounts(): Record<FuelKey, number> {
  const counts = { all: investigations.length, solid: 0, liquid: 0, gaseous: 0, unknown: 0 };
  for (const item of investigations) counts[primaryFuel(item)] += 1;
  return counts;
}

export function filterByFuel(items: Investigation[], fuel: FuelKey): Investigation[] {
  if (fuel === "all") return items;
  return items.filter((item) => primaryFuel(item) === fuel);
}