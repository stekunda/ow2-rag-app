"use client";

import { Shield, Crosshair, PlusCircle, Search } from "lucide-react";
import { clsx } from "clsx";
import type { Hero, HeroRole } from "@/lib/types";

const roleIcon = {
  Tank: Shield,
  Damage: Crosshair,
  Support: PlusCircle
};

const roleColor: Record<HeroRole, string> = {
  Tank: "text-ow-cyan",
  Damage: "text-ow-orange",
  Support: "text-emerald-300"
};

export function HeroSidebar({
  heroes,
  selectedHero,
  onSelectHero,
  filter,
  onFilter
}: {
  heroes: Hero[];
  selectedHero: string | null;
  onSelectHero: (hero: string | null) => void;
  filter: string;
  onFilter: (value: string) => void;
}) {
  const visible = heroes.filter((hero) => hero.name.toLowerCase().includes(filter.toLowerCase()));

  return (
    <aside className="flex h-full min-h-0 w-full flex-col border-r border-white/10 bg-navy-900/92">
      <div className="border-b border-white/10 p-4">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded bg-ow-orange text-lg font-black text-navy-950">OW</div>
          <div>
            <h1 className="text-base font-bold tracking-wide">Hero Intelligence</h1>
            <p className="text-xs text-ow-steel">Agentic RAG workspace</p>
          </div>
        </div>
        <label className="mt-4 flex items-center gap-2 rounded border border-white/10 bg-navy-950 px-3 py-2 text-sm text-ow-steel">
          <Search className="h-4 w-4" aria-hidden />
          <input
            value={filter}
            onChange={(event) => onFilter(event.target.value)}
            placeholder="Filter heroes"
            className="w-full bg-transparent text-slate-100 outline-none placeholder:text-ow-steel"
          />
        </label>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        <button
          onClick={() => onSelectHero(null)}
          className={clsx(
            "mb-2 flex w-full items-center justify-between rounded px-3 py-2 text-left text-sm transition",
            selectedHero === null ? "bg-ow-orange text-navy-950" : "text-slate-200 hover:bg-white/10"
          )}
        >
          <span>All heroes</span>
          <span className="text-xs opacity-75">{heroes.length}</span>
        </button>
        <div className="grid gap-1">
          {visible.map((hero) => {
            const Icon = roleIcon[hero.role];
            return (
              <button
                key={hero.name}
                onClick={() => onSelectHero(hero.name)}
                title={`${hero.name} - ${hero.role}`}
                className={clsx(
                  "flex h-10 items-center gap-3 rounded px-3 text-left text-sm transition",
                  selectedHero === hero.name ? "bg-white text-navy-950" : "text-slate-200 hover:bg-white/10"
                )}
              >
                <Icon className={clsx("h-4 w-4 shrink-0", selectedHero === hero.name ? "text-navy-950" : roleColor[hero.role])} aria-hidden />
                <span className="truncate">{hero.name}</span>
              </button>
            );
          })}
        </div>
      </div>
    </aside>
  );
}
