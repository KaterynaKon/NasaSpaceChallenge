"use client";

import {
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  DEFAULT_ENV,
  environments,
  filterByFuel,
  fuelCounts,
  investigations,
  rankBy,
  countWithTable,
  type FuelKey,
} from "@/lib/data";

import type {
  Environment,
  Investigation,
} from "@/lib/types";

import EnvironmentTabs from "@/components/EnvironmentTabs";
import FuelChips from "@/components/FuelFilter";
import EnvNote from "@/components/EnvNote";


import "./dashboard.css";

type DashboardProps = {
  renderDetails?: (
    selected: Investigation | undefined
  ) => ReactNode;

  initialEnvironment?: Environment;
  initialFuel?: FuelKey;
};
export default function Dashboard({
  renderDetails,
  initialEnvironment = DEFAULT_ENV,
  initialFuel = "all",
}: DashboardProps) {

  // Selected environment
  const [environment, setEnvironment] =
    useState<Environment>(initialEnvironment);

  // Selected fuel filter
  const [fuel, setFuel] =
    useState<FuelKey>(initialFuel);

  // Selected investigation
  const [selectedId, setSelectedId] = useState<string>(
    () => rankBy(initialEnvironment)[0]?.id ?? ""
  );

  // Change environment
  const handleEnvironmentChange = (
    nextEnvironment: Environment
  ) => {
    setEnvironment(nextEnvironment);

    const nextList = filterByFuel(
      rankBy(nextEnvironment),
      fuel
    );

    setSelectedId(nextList[0]?.id ?? "");
  };

  // Change fuel filter
  const handleFuelChange = (nextFuel: FuelKey) => {
    setFuel(nextFuel);

    const nextList = filterByFuel(
      rankBy(environment),
      nextFuel
    );

    if (
      !nextList.some((item) => item.id === selectedId)
    ) {
      setSelectedId(nextList[0]?.id ?? "");
    }
  };

  // Clear fuel filter
  const clearFilters = () => {
    setFuel("all");

    const nextList = rankBy(environment);

    setSelectedId(nextList[0]?.id ?? "");
  };

  // Data for environment note
  const environmentInfo = environments.find(
    (item) => item.id === environment
  ) ?? environments[0];

  const reportCount = investigations.filter(
    (item) => item.badge === "from report"
  ).length;

  const evidenceCount = countWithTable() + reportCount;

  return (
    <main className="flame-dashboard">

      {/* Header */}

      <header className="dashboard-header">

        <div className="dashboard-heading">
          <h1>Flame in Freefall</h1>

          <span>
            Fire Safety Explorer · NASA PSI
          </span>
        </div>

        <p>
          Which microgravity combustion experiment tells
          you the most about fire risk in a given
          environment? Pick an environment; every rank
          is a sum of five explicit components you can
          inspect.
        </p>

      </header>

      {/* Environment selection */}

      <EnvironmentTabs
        environments={environments}
        activeEnvironment={environment}
        onChange={handleEnvironmentChange}
      />

      {/* Fuel filters */}

      <FuelChips
        counts={fuelCounts()}
        selectedFuel={fuel}
        onChange={handleFuelChange}
        onClear={clearFilters}
      />

    
    </main>
    
  );
}
