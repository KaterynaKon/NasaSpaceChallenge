import raw from "@/data/dashboard_data.json";
import type { Dimension, Investigation, SortKey } from "./types";

export const investigations = raw as Investigation[];

export function getInvestigation(id: string) {
  return investigations.find((i) => i.id === id);
}


export function getFilterOptions(dimension: Dimension): string[] {
  const key = dimension === "fuel" ? "fuels" : "materials";
  return Array.from(new Set(investigations.flatMap((i) => i[key]))).sort();
}

export function filterAndSort(
  dimension: Dimension,
  value: string | null,
  sort: SortKey
): Investigation[] {
  const key = dimension === "fuel" ? "fuels" : "materials";
  const list = value ? investigations.filter((i) => i[key].includes(value)) : [...investigations];
  const sorters: Record<SortKey, (a: Investigation, b: Investigation) => number> = {
    relevance: (a, b) => b.score - a.score,
    o2: (a, b) => b.o2Max - a.o2Max,
    year: (a, b) => b.year - a.year,
  };
  return list.sort(sorters[sort]);
}
