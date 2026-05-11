"use client";

import { Activity, Database, Timer } from "lucide-react";
import type { ToolCall } from "@/lib/types";

export function ReasoningTrace({ calls }: { calls: ToolCall[] }) {
  if (!calls.length) {
    return null;
  }

  return (
    <div className="mt-4 border-t border-[#f99e1a]/10 pt-3">
      <div className="mb-2 flex items-center gap-2 text-xs font-medium text-[#8fa0b8]">
        <Activity className="h-4 w-4" aria-hidden />
        Agent trace
      </div>
      <div className="grid gap-2">
        {calls.map((call, index) => (
          <div key={`${call.name}-${index}`} className="rounded-2xl border border-[#f99e1a]/10 bg-[#151922] p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-mono text-xs text-[#61d8ff]">{call.name}</span>
              <span className="inline-flex items-center gap-1 text-xs text-[#8fa0b8]">
                <Timer className="h-3.5 w-3.5" aria-hidden />
                {Math.round(call.latency_ms ?? 0)}ms
              </span>
            </div>
            <div className="mt-2 flex items-center gap-2 text-xs text-[#8fa0b8]">
              <Database className="h-3.5 w-3.5" aria-hidden />
              <span>{call.sources.length} source chunks</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
