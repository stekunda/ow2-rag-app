"use client";

import { Bot, ExternalLink, User } from "lucide-react";
import type { ChatTurn } from "@/lib/types";
import { ReasoningTrace } from "./ReasoningTrace";

export function ChatMessage({ turn }: { turn: ChatTurn }) {
  const isAssistant = turn.role === "assistant";

  return (
    <article className={isAssistant ? "bg-navy-850" : "bg-transparent"}>
      <div className="mx-auto flex max-w-5xl gap-4 px-4 py-5 md:px-8">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded border border-white/10 bg-navy-950">
          {isAssistant ? <Bot className="h-5 w-5 text-ow-orange" aria-hidden /> : <User className="h-5 w-5 text-ow-cyan" aria-hidden />}
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-ow-steel">
            {isAssistant ? "Agent" : "You"}
            {isAssistant && turn.model_source && (
              <span className="ml-2 inline-block rounded bg-ow-orange/10 px-2 py-1 text-ow-orange">
                {turn.model_source}
              </span>
            )}
            {isAssistant && !turn.model_source && (
              <span className="ml-2 inline-block rounded bg-yellow-500/10 px-2 py-1 text-yellow-400">
                No LLM
              </span>
            )}
          </div>
          <div className="whitespace-pre-wrap text-sm leading-7 text-slate-100 md:text-base">{turn.content}</div>
          {isAssistant && <ReasoningTrace calls={turn.reasoning ?? []} />}
          {isAssistant && Boolean(turn.sources?.length) && (
            <div className="mt-4 grid gap-2">
              <div className="text-xs font-semibold uppercase tracking-wide text-ow-steel">Sources</div>
              {turn.sources?.slice(0, 5).map((source, index) => (
                <a
                  key={`${source.title}-${index}`}
                  href={source.url ?? "#"}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-start justify-between gap-3 rounded border border-white/10 bg-navy-950/70 p-3 text-sm text-slate-200 transition hover:border-ow-orange/70"
                >
                  <span>
                    <span className="block font-medium">{source.title}</span>
                    <span className="mt-1 block text-xs text-ow-steel">{[source.category, source.date].filter(Boolean).join(" / ")}</span>
                  </span>
                  <ExternalLink className="mt-1 h-4 w-4 shrink-0 text-ow-orange" aria-hidden />
                </a>
              ))}
            </div>
          )}
        </div>
      </div>
    </article>
  );
}
