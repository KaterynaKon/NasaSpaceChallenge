"use client";

import type {
  Environment,
  Investigation,
} from "@/lib/types";

import InvestigationCard from "@/components/InvestigationCard";

type Props = {
  items: Investigation[];
  environment: Environment;
  selectedId: string;
  onSelect: (id: string) => void;
};

export default function RankingList({
  items,
  environment,
  selectedId,
  onSelect,
}: Props) {
  if (items.length === 0) {
    return (
      <div className="empty-ranking">
        <strong>No investigations found</strong>

        <p>
          Try selecting another fuel type or clearing
          the filters.
        </p>
      </div>
    );
  }

  return (
    <section className="ranking-list">
      {items.map((item, index) => (
        <InvestigationCard
          key={item.id}
          item={item}
          environment={environment}
          rank={index + 1}
          selected={selectedId === item.id}
          onSelect={onSelect}
        />
      ))}
    </section>
  );
}