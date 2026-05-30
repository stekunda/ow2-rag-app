"use client";

import type { ChatTurn } from "@/lib/types";

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
      </div>
    </article>
  );
}
