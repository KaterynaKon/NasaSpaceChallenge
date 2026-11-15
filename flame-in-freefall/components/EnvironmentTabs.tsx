"use client";

import type { Environment, EnvironmentInfo } from "@/lib/types";
import type { IconType } from "react-icons";
import { GiSpaceship, GiHabitatDome, GiSpaceSuit, GiRobotGrab } from "react-icons/gi";


type Props = {
  environments: EnvironmentInfo[];
  activeEnvironment: Environment;
  onChange: (environment: Environment) => void;
};

// Keys must match your Environment ids. These are placeholders.
const environmentIcons: Record<Environment, IconType> = {
  cabin: GiSpaceship,
  habitat: GiHabitatDome,
  suit: GiSpaceSuit,
  rover: GiRobotGrab,
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
        {environments.map((environment) => {
          const isActive = activeEnvironment === environment.id;
          const Icon = environmentIcons[environment.id];

          return (
            <button
              key={environment.id}
              type="button"
              className={`environment-tab ${isActive ? "is-active" : ""}`}
              onClick={() => onChange(environment.id)}
              aria-pressed={isActive}
            >
              <span className="environment-icon">
                <Icon size={20} />
              </span>

              <span className="environment-text">
                <span className="environment-name">{environment.label}</span>
                <small>
                  {environment.o2} O₂ · {environment.pressure}
                </small>
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

