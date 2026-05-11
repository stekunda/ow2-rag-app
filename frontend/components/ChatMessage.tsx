"use client";

import { ExternalLink } from "lucide-react";
import type { ChatTurn } from "@/lib/types";
import { ReasoningTrace } from "./ReasoningTrace";

export function ChatMessage({ turn }: { turn: ChatTurn }) {
  const isAssistant = turn.role === "assistant";

  return (
    <article className={isAssistant ? "py-5" : "flex justify-end py-5"}>
      <div className={isAssistant ? "min-w-0" : "max-w-[82%] rounded-3xl bg-[#1b2230] px-4 py-3"}>
        {isAssistant && (
          <div className="mb-2 text-xs font-medium text-[#8fa0b8]">
            OW2 Hero Intelligence
            {turn.model_source && <span className="ml-2 inline-block rounded-full bg-[#1b2230] px-2 py-0.5 text-[#ffd27a]">{turn.model_source}</span>}
          </div>
        )}
        <div className="whitespace-pre-wrap text-[15px] leading-7 text-[#f8fbff]">{turn.content}</div>
        {isAssistant && <ReasoningTrace calls={turn.reasoning ?? []} />}
        {isAssistant && Boolean(turn.sources?.length) && (
          <div className="mt-4 grid gap-2 border-t border-[#f99e1a]/10 pt-3">
            <div className="text-xs font-medium text-[#8fa0b8]">Sources</div>
            {turn.sources?.slice(0, 5).map((source, index) => (
              <a
                key={`${source.title}-${index}`}
                href={source.url ?? "#"}
                target="_blank"
                rel="noreferrer"
                className="flex items-start justify-between gap-3 rounded-2xl border border-[#f99e1a]/10 bg-[#151922] p-3 text-sm text-[#dce6f5] transition hover:border-[#f99e1a]/35"
              >
                <span>
                  <span className="block font-medium">{source.title}</span>
                  <span className="mt-1 block text-xs text-[#8fa0b8]">{[source.category, source.date].filter(Boolean).join(" / ")}</span>
                </span>
                <ExternalLink className="mt-1 h-4 w-4 shrink-0 text-[#f99e1a]" aria-hidden />
              </a>
            ))}
          </div>
        )}
      </div>
    </article>
  );
}
