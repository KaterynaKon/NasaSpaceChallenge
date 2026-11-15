"use client";

import type { Environment, EnvironmentInfo } from "@/lib/types";

type Props = {
  environments: EnvironmentInfo[];
  activeEnvironment: Environment;
  onChange: (environment: Environment) => void;
};

export default function EnvironmentTabs({
  environments,
  activeEnvironment,
  onChange,
}: Props) {
  return (
    <section className="dashboard-toolbar environment-toolbar">
      <span className="toolbar-label">Environment</span>

      <div className="environment-options">
        {environments.map((environment) => (
          <button
            key={environment.id}
            type="button"
            className={`environment-tab ${
              activeEnvironment === environment.id ? "is-active" : ""
            }`}
            onClick={() => onChange(environment.id)}
            aria-pressed={activeEnvironment === environment.id}
          >
            <span>{environment.label}</span>
            <small>
              {environment.o2} O₂ · {environment.pressure}
            </small>
          </button>
        ))}
      </div>
    </section>
  );
}



