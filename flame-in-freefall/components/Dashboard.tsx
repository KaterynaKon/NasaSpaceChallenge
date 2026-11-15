"use client";

import { useMemo, useState } from "react";
import { filterAndSort, getFilterOptions } from "@/lib/data";
import type { Dimension, Environment } from "@/lib/types";
import EnvironmentTabs from "./EnvironmentTabs";



export default function Dashboard() {

  return (
    <>
      <header className="bg-slate-900 px-6 py-4 text-sm font-bold tracking-wide text-white">
        FLAME <span className="text-orange-500">IN</span> FREEFALL
      </header>

    </>
  );
}
