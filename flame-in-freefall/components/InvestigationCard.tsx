"use client";

import type {
  Investigation,
  Environment,
} from "@/lib/types";

import { scoreFor } from "@/lib/data";

type Props = {
  item: Investigation;
  environment: Environment;
  rank: number;
  selected: boolean;
  onSelect: (id: string) => void;
};

const badgeLabels: Record<Investigation["badge"], string> = {
  "table parsed": "Table parsed",
  "samples only": "Samples only",
  "from report": "From report",
  estimated: "Estimated",
};

export default function InvestigationCard({
  item,
  environment,
  rank,
  selected,
  onSelect,
}: Props) {
  const score = scoreFor(item, environment);

  return (
    <button
      type="button"
      className={`investigation-card ${
        selected ? "is-selected" : ""
      }`}
      onClick={() => onSelect(item.id)}
      aria-pressed={selected}
    >
      <span className="investigation-rank">
        {rank}
      </span>

      <span className="investigation-main">
        <strong className="investigation-title">
          {item.fullName || item.name}
        </strong>

        <span className="investigation-meta">
          <span>{item.id}</span>
          <span>{item.category}</span>
          <span>{item.platform}</span>

          <span
            className={`data-badge badge-${item.badge.replaceAll(
              " ",
              "-"
            )}`}
          >
            {badgeLabels[item.badge]}
          </span>
        </span>
      </span>

      <span className="investigation-score">
        <strong>{score}</strong>
        <small>/ 100</small>

        <span className="score-track">
          <span
            style={{
              width: `${Math.max(0, Math.min(100, score))}%`,
            }}
          />
        </span>
      </span>
    </button>
  );
}