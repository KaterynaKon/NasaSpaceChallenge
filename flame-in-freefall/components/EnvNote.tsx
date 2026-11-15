import type { EnvironmentInfo } from "@/lib/types";

type Props = {
  environment: EnvironmentInfo;
  measuredCount: number;
  totalCount: number;
};

export default function EnvNote({
  environment,
  measuredCount,
  totalCount,
}: Props) {
  return (
    <aside className="environment-note">
      <strong>{environment.label}:</strong>{" "}
      <span>{environment.description}</span>{" "}
      <span>
        Scores use available experimental evidence for{" "}
        <strong>{measuredCount} of {totalCount}</strong>{" "}
        investigations; the remaining records are ranked using
        the available fuel, platform and fire-safety evidence.
      </span>
    </aside>
  );
}

