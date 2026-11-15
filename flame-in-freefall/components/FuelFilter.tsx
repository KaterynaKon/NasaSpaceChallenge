"use client";

import type { FuelKey } from "@/lib/data";

type Props = {
  counts: Record<FuelKey, number>;
  selectedFuel: FuelKey;
  onChange: (fuel: FuelKey) => void;
  onClear: () => void;
};

const options: FuelKey[] = [
  "all",
  "solid",
  "liquid",
  "gaseous",
  "unknown",
];

const labels: Record<FuelKey, string> = {
  all: "All",
  solid: "Solid",
  liquid: "Liquid",
  gaseous: "Gas",
  unknown: "Unknown",
};

export default function FuelFilter({
  counts,
  selectedFuel,
  onChange,
  onClear,
}: Props) {
  return (
    <section className="dashboard-toolbar fuel-toolbar">
      <span className="toolbar-label">Fuel</span>

      <div className="fuel-options">
        {options.map((fuel) => (
          <button
            key={fuel}
            type="button"
            className={`fuel-chip ${
              selectedFuel === fuel ? "is-active" : ""
            }`}
            onClick={() => onChange(fuel)}
            aria-pressed={selectedFuel === fuel}
          >
            {labels[fuel]} <span>{counts[fuel]}</span>
          </button>
        ))}

        <span className="fuel-divider" />

        <button
          type="button"
          className="clear-filters"
          onClick={onClear}
        >
          Clear filters
        </button>
      </div>
    </section>
  );
}


