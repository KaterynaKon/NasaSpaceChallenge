"use client";

import type { Environment, EnvironmentInfo, Investigation } from "@/lib/types";

type Props = {
  item: Investigation | null;
  env: Environment;
  envInfo: EnvironmentInfo;
};

export default function DetailPanel({ item, env, envInfo }: Props) {
  if (!item) return null;

  const rows: [string, string][] = [
    ["Platform", item.platform || "—"],
    ["Hardware", item.hardware.name || "—"],
    ["Fuel type", item.fuelLabel || "—"],
    ["Materials", item.testedMaterials?.join(", ") || "—"],
    ["O₂ measured", item.o2Label],
    ["Pressure", item.pressureLabel],
    ["Airflow", item.flowLabel],
    ["Test rows", item.samples ? String(item.samples) : "—"],
    ["Publications", String(item.publications.length)],
    ["Data files", `${item.dataFiles.count} · ${item.dataFiles.sizeGb} GB`],
  ];

const parts = item.scoreParts?.[env] ?? [];
const score = item.scores?.[env] ?? item.score;

  return (
   <aside className="rounded-xl border border-line bg-white p-5">
      <h2 className="mb-1 text-[17px] font-semibold leading-snug tracking-[-0.2px] text-ink">
        {item.name} — {item.fullName}
      </h2>
      <div className="mb-3.5 text-[12px] text-muted">
        {item.id} · {item.category}
      </div>

      <dl className="mb-3.5 grid grid-cols-[120px_1fr] gap-x-2.5 gap-y-1.5 text-[12.5px]">

        {rows.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="text-muted">{label}</dt>
            <dd className="text-ink">{value}</dd>
          </div>
        ))}
      </dl>

      {item.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {item.tags.slice(0, 8).map((tag) => (
            <span
              key={tag}
              className="rounded bg-subtle px-1.5 py-0.5 text-[10.5px] text-muted"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {item.findings.length > 0 && (
        <>
          <h3 className="mb-2 mt-4 border-t border-line pt-3 text-[10.5px] uppercase tracking-[0.11em] text-muted">

            What they found
          </h3>
          <p className="mb-2 mt-1.5 text-[12.5px] leading-[1.55] text-[#2A3B4C]">

            {item.findings[0].text}
          </p>
          <div className="mt-1.5 flex gap-3 text-[11.5px]">
            {item.findings[0].url && (
              <a
                href={item.findings[0].url}
                target="_blank"
                rel="noreferrer"
                className="text-accent underline"
              >
                Source
              </a>
            )}
          </div>
        </>
      )}

      <h3 className="mb-2 mt-4 border-t border-line pt-3 text-[10.5px] uppercase tracking-[0.11em] text-muted">

        Score for {envInfo.label.toLowerCase()} — {score}/100
      </h3>

      <div className="mt-1">
        {parts.map((part) => (
          <div
            key={part.label}
            className="flex items-start justify-between gap-3 border-b border-dashed border-[#EDF1F5] py-1.5 last:border-0"

          >
            <div>
              <div className="text-[12.5px] text-ink">{part.label}</div>
              <div className="mt-0.5 text-[11px] leading-snug text-muted">{part.why}</div>

            </div>
            <div className="whitespace-nowrap text-[12.5px] tabular-nums text-ink">
              {part.points}
              <span className="text-muted">/{part.max}</span>
            </div>
          </div>
        ))}
      </div>

      <h3 className="mb-2 mt-4 border-t border-line pt-3 text-[10.5px] uppercase tracking-[0.11em] text-muted">
        Sources
      </h3>
      <div className="mt-1.5 flex gap-3 text-[11.5px]">
        <a
          href={item.sourceUrl}
          target="_blank"
          rel="noreferrer"
          className="text-accent underline"
        >
          PSI record {item.id}
        </a>
        {item.publications[0]?.url && (
          <a
            href={item.publications[0].url}
            target="_blank"
            rel="noreferrer"
            className="text-accent underline"
          >
            First publication
          </a>
        )}
      </div>

    </aside>
  );
}
