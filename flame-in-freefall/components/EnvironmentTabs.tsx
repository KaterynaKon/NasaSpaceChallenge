import type { Dimension } from "@/lib/types";

type Props = {
  dimension: Dimension;
  onDimension: (d: Dimension) => void;
  options: string[];
  value: string | null;
  onValue: (v: string | null) => void;
};

const chip = (active: boolean) =>
  `rounded-md border px-3 py-1.5 text-xs transition ${
    active
      ? "border-orange-500 bg-orange-50 font-medium text-orange-600"
      : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
  }`;

export default function EnvironmentTabs({ dimension, onDimension, options, value, onValue }: Props) {
  const allLabel = dimension === "fuel" ? "All fuels" : "All materials";
  return (
    <div className="flex flex-wrap items-center gap-3 border-b border-slate-200 bg-white px-6 py-3">
      <span className="text-xs text-slate-500">Filter by</span>

      <div className="flex gap-1.5">
        {(["fuel", "material"] as Dimension[]).map((d) => (
          <button
            key={d}
            onClick={() => {
              onDimension(d);
              onValue(null);
            }}
            className={`rounded-md px-3 py-1.5 text-xs font-medium capitalize ${
              dimension === d ? "bg-orange-500 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            {d}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-1.5">
        <button onClick={() => onValue(null)} className={chip(value === null)}>
          {allLabel}
        </button>
        {options.map((o) => (
          <button key={o} onClick={() => onValue(o)} className={chip(value === o)}>
            {o}
          </button>
        ))}
      </div>

      <button
        onClick={() => onValue(null)}
        className="ml-auto rounded-md border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50"
      >
        Clear filters
      </button>
    </div>
  );
}
