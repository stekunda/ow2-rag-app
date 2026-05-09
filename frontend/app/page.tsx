"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Send, Square, Zap } from "lucide-react";
import { HeroSidebar } from "@/components/HeroSidebar";
import { ChatMessage } from "@/components/ChatMessage";
import { API_BASE, fetchHeroes } from "@/lib/api";
import type { ChatTurn, Hero, Source, ToolCall } from "@/lib/types";

const starterTurns: ChatTurn[] = [
  {
    id: "welcome",
    role: "assistant",
    content:
      "Ask for hero counters, patch context, map-specific comps, or lore. Try: build me a comp to counter an Orisa/Mauga/Ana frontline on Dorado.",
    reasoning: [],
    sources: []
  }
];

function sessionId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `session-${Date.now()}`;
}

export default function Home() {
  const [heroes, setHeroes] = useState<Hero[]>([]);
  const [selectedHero, setSelectedHero] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>(starterTurns);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [session] = useState(sessionId);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    fetchHeroes().then(setHeroes).catch(() => {
      setHeroes([
        { name: "D.Va", role: "Tank" },
        { name: "Orisa", role: "Tank" },
        { name: "Mauga", role: "Tank" },
        { name: "Ana", role: "Support" },
        { name: "Tracer", role: "Damage" },
        { name: "Sombra", role: "Damage" },
        { name: "Kiriko", role: "Support" },
        { name: "Lucio", role: "Support" }
      ]);
    });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  const selectedRole = useMemo(() => heroes.find((hero) => hero.name === selectedHero)?.role, [heroes, selectedHero]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = input.trim();
    if (!message || isStreaming) {
      return;
    }

    const assistantId = crypto.randomUUID();
    setTurns((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", content: message },
      { id: assistantId, role: "assistant", content: "", reasoning: [], sources: [] }
    ]);
    setInput("");
    setIsStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, session_id: session, selected_hero: selectedHero }),
        signal: controller.signal
      });
      if (!response.ok || !response.body) {
        throw new Error("Streaming request failed");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";
        for (const raw of events) {
          const event = raw.match(/^event: (.+)$/m)?.[1];
          const data = raw.match(/^data: (.+)$/m)?.[1];
          if (!event || !data) continue;
          if (event === "token") {
            const token = JSON.parse(data) as string;
            setTurns((current) => current.map((turn) => (turn.id === assistantId ? { ...turn, content: turn.content + token } : turn)));
          }
          if (event === "reasoning") {
            const call = JSON.parse(data) as ToolCall;
            setTurns((current) =>
              current.map((turn) => (turn.id === assistantId ? { ...turn, reasoning: [...(turn.reasoning ?? []), call] } : turn))
            );
          }
          if (event === "done") {
            const donePayload = JSON.parse(data) as { sources: Source[]; reasoning: ToolCall[]; model_source: string | null };
            setTurns((current) =>
              current.map((turn) =>
                turn.id === assistantId ? { ...turn, reasoning: donePayload.reasoning, sources: donePayload.sources, model_source: donePayload.model_source } : turn
              )
            );
          }
        }
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        setTurns((current) =>
          current.map((turn) =>
            turn.id === assistantId
              ? { ...turn, content: "The backend stream could not be reached. Start Docker Compose or run FastAPI locally, then try again." }
              : turn
          )
        );
      }
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  }

  return (
    <main className="flex h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(249,158,26,.16),transparent_34%),#070b16]">
      <div className="hidden w-80 shrink-0 md:block">
        <HeroSidebar heroes={heroes} selectedHero={selectedHero} onSelectHero={setSelectedHero} filter={filter} onFilter={setFilter} />
      </div>
      <section className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-white/10 bg-navy-900/80 px-4 py-3 backdrop-blur md:px-8">
          <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-ow-amber">
                <Zap className="h-4 w-4" aria-hidden />
                Production RAG demo
              </div>
              <p className="mt-1 text-sm text-ow-steel">
                {selectedHero ? `${selectedHero}${selectedRole ? ` / ${selectedRole}` : ""}` : "All heroes"} context active
              </p>
            </div>
            <button
              type="button"
              onClick={() => abortRef.current?.abort()}
              disabled={!isStreaming}
              title="Stop streaming"
              className="grid h-10 w-10 place-items-center rounded border border-white/10 bg-navy-950 text-slate-200 transition enabled:hover:border-ow-orange disabled:opacity-40"
            >
              <Square className="h-4 w-4" aria-hidden />
            </button>
          </div>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto">
          {turns.map((turn) => (
            <ChatMessage key={turn.id} turn={turn} />
          ))}
          <div ref={bottomRef} />
        </div>
        <form onSubmit={submit} className="border-t border-white/10 bg-navy-900/95 p-4 md:p-6">
          <div className="mx-auto flex max-w-5xl gap-3">
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
              placeholder="Ask for counters, map plans, patch history, or lore..."
              className="min-h-12 flex-1 resize-none rounded border border-white/10 bg-navy-950 px-4 py-3 text-sm text-slate-100 outline-none ring-0 placeholder:text-ow-steel focus:border-ow-orange"
            />
            <button
              type="submit"
              disabled={isStreaming || !input.trim()}
              title="Send"
              className="grid h-12 w-12 place-items-center rounded bg-ow-orange text-navy-950 transition hover:bg-ow-amber disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Send className="h-5 w-5" aria-hidden />
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
