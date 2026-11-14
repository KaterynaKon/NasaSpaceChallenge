"use client";

import { useMemo, useState } from "react";
import { filterAndSort, getFilterOptions } from "@/lib/data";
import type { Dimension, SortKey } from "@/lib/types";
import EnvironmentTabs from "./EnvironmentTabs";


export default function Dashboard() {
  const [dimension, setDimension] = useState<Dimension>("material");
  const [value, setValue] = useState<string | null>(null);
  const [sort, setSort] = useState<SortKey>("relevance");
  const [selectedId, setSelectedId] = useState<string | undefined>();

  const options = useMemo(() => getFilterOptions(dimension), [dimension]);
  const items = useMemo(() => filterAndSort(dimension, value, sort), [dimension, value, sort]);
  const selected = items.find((i) => i.id === selectedId) ?? items[0];

  return (
    <>
      <header className="bg-slate-900 px-6 py-4 text-sm font-bold tracking-wide text-white">
        FLAME <span className="text-orange-500">IN</span> FREEFALL
      </header>

      <EnvironmentTabs
        dimension={dimension}
        onDimension={setDimension}
        options={options}
        value={value}
        onValue={setValue}
      />

      <main className="grid grid-cols-1 bg-slate-100 lg:h-[calc(100vh-7.5rem)] lg:grid-cols-[340px_1fr_360px]">
       
      </main>
    </>
  );
}
