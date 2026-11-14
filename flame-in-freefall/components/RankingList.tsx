import type { Investigation } from "@/lib/types";



type Props = {
  items: Investigation[];
  selectedId?: string;
  onSelect: (id: string) => void;
};

export default function RankingList({ items, selectedId, onSelect}: Props) {
  return (
    <div className="p-4">

      {items.length === 0 && (
        <p className="text-sm text-slate-500">No investigations match this filter. Clear filters to see all.</p>
      )}

      <ul className="space-y-3">
        {items.map((it) => {
          const active = it.id === selectedId;
          return (
            <li key={it.id}>
              <button
                onClick={() => onSelect(it.id)}
                className={`flex w-full gap-3 rounded-xl border bg-white p-3 text-left transition ${
                  active ? "border-orange-500 ring-1 ring-orange-500" : "border-slate-200 hover:border-slate-300"
                }`}
              >
                <span
                  className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-lg font-semibold ${
                    active ? "bg-orange-500 text-white" : "bg-orange-50 text-orange-600"
                  }`}
                >
                  {it.score}
                </span>
                <span className="min-w-0">
                  <span className="block font-semibold">{it.name}</span>
                  <span className="mt-1.5 flex flex-wrap gap-1">
                    {it.tags.map((t) => (
                      <span key={t} className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600">
                        {t}
                      </span>
                    ))}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
