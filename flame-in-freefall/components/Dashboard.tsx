"use client";

import { useMemo, useState } from "react";

import {
  DEFAULT_ENV,
  environments,
  filterByFuel,
  fuelCounts,
  investigations,
  rankBy,
  type FuelKey,
} from "@/lib/data";

import type {
  Environment,
} from "@/lib/types";

import EnvironmentTabs from "@/components/EnvironmentTabs";
import FuelFilter from "@/components/FuelFilter";
import EnvNote from "@/components/EnvNote";
import RankingList from "@/components/RankingList";
import DetailPanel from "@/components/DetailPanel";

import "./dashboard.css";

export default function Dashboard() {
  const [environment, setEnvironment] =
    useState<Environment>(DEFAULT_ENV);

  const [fuel, setFuel] =
    useState<FuelKey>("all");

  const [selectedId, setSelectedId] =
    useState<string>(() => rankBy(DEFAULT_ENV)[0]?.id ?? "");

  const rankedItems = useMemo(() => {
    return filterByFuel(rankBy(environment), fuel);
  }, [environment, fuel]);

  const selectedItem =
    rankedItems.find((item) => item.id === selectedId) ?? null;

  const environmentInfo =
    environments.find((item) => item.id === environment) ??
    environments[0];

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

  const handleFuelChange = (nextFuel: FuelKey) => {
    setFuel(nextFuel);

    const nextList = filterByFuel(
      rankBy(environment),
      nextFuel
    );

    if (!nextList.some((item) => item.id === selectedId)) {
      setSelectedId(nextList[0]?.id ?? "");
    }
  };

  const clearFilters = () => {
    setFuel("all");

    const nextList = rankBy(environment);
    setSelectedId(nextList[0]?.id ?? "");
  };

  const evidenceCount = investigations.filter(
    (item) =>
      item.badge === "table parsed" ||
      item.badge === "from report"
  ).length;

  return (
    <main className="flame-dashboard">

      <header className="dashboard-header">
        <div className="dashboard-heading">
          <h1>Flame in Freefall</h1>
          <span>Fire Safety Explorer · NASA PSI</span>
        </div>

        <p>
          Which microgravity combustion experiment tells
          you the most about fire risk in a given
          environment? Pick an environment; every rank
          is a sum of five explicit components you can
          inspect.
        </p>
      </header>

      <EnvironmentTabs
        environments={environments}
        activeEnvironment={environment}
        onChange={handleEnvironmentChange}
      />

      <FuelFilter
        counts={fuelCounts()}
        selectedFuel={fuel}
        onChange={handleFuelChange}
        onClear={clearFilters}
      />

      <div className="dashboard-content">

        <section className="ranking-column">

          <EnvNote
            environment={environmentInfo}
            measuredCount={evidenceCount}
            totalCount={investigations.length}
          />

          <div className="ranking-summary">
            <strong>{rankedItems.length}</strong>
            {" "}investigations
            <span> · </span>
            Sorted by relevance
          </div>

          <RankingList
            items={rankedItems}
            environment={environment}
            selectedId={selectedItem?.id ?? ""}
            onSelect={setSelectedId}
          />

        </section>

        <section className="details-column">

          <DetailPanel
            item={selectedItem}
            env={environment}
            envInfo={environmentInfo}
          />

        </section>

      </div>

    </main>
  );
}