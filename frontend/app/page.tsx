"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import {
  ArrowUp,
  Sparkle,
  Square
} from "lucide-react";
import { ChatMessage } from "@/components/ChatMessage";
import { API_BASE } from "@/lib/api";
import type { ChatTurn, Source, ToolCall } from "@/lib/types";

const heroPanels = [
  { name: "ANRAN", role: "DAMAGE", image: "/heroes/anran.avif", position: "48% 50%" },
  { name: "D.VA", role: "TANK", image: "/heroes/dva.jpg", position: "75% 50%" },
  { name: "ANA", role: "SUPPORT", image: "/heroes/ana.jpg", position: "71% 50%" },
  { name: "HANZO", role: "DAMAGE", image: "/heroes/hanzo.jpg", position: "66% 50%" }
];

function sessionId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `session-${Date.now()}`;
}

export default function Home() {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [session] = useState(sessionId);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const hasChat = turns.length > 0;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  async function sendMessage(message: string) {
    const trimmed = message.trim();
    if (!trimmed || isStreaming) {
      return;
    }

    const assistantId = crypto.randomUUID();
    setTurns((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", content: trimmed },
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
        body: JSON.stringify({ message: trimmed, session_id: session }),
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
                turn.id === assistantId
                  ? { ...turn, reasoning: donePayload.reasoning, sources: donePayload.sources, model_source: donePayload.model_source }
                  : turn
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

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendMessage(input);
  }

  return (
    <main className="flex h-screen overflow-hidden bg-[#11151d] text-[#e6edf6]">
      <section className="relative flex min-w-0 flex-1 flex-col">
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div
            className={
              hasChat
                ? "absolute inset-0 bg-[radial-gradient(circle_at_80%_15%,rgba(249,158,26,0.08),transparent_30%),radial-gradient(circle_at_20%_85%,rgba(60,160,255,0.07),transparent_34%)]"
                : "absolute inset-0 bg-[radial-gradient(circle_at_75%_18%,rgba(249,158,26,0.20),transparent_32%),radial-gradient(circle_at_25%_80%,rgba(60,160,255,0.14),transparent_36%)]"
            }
          />
          {!hasChat && (
            <>
              <div className="absolute right-0 top-0 hidden h-full w-[56%] md:block">
                <div className="absolute right-16 top-1/2 flex -translate-y-1/2 rotate-[-7deg] gap-4 opacity-70">
                  {heroPanels.map((hero, index) => (
                    <div
                      key={hero.name}
                      className="relative h-[430px] w-28 overflow-hidden rounded-2xl border border-white/10 bg-[#1b2230] shadow-2xl"
                      style={{ transform: `translateY(${index % 2 === 0 ? 28 : -22}px)` }}
                    >
                      <div
                        className="absolute inset-0 bg-cover bg-no-repeat saturate-125"
                        style={{ backgroundImage: `url(${hero.image})`, backgroundPosition: hero.position }}
                      />
                      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#11151d]/10 to-[#11151d]/85" />
                      <div className="absolute inset-0 ring-1 ring-inset ring-white/10" />
                      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-4">
                        <div className="text-lg font-black italic tracking-wide text-white">{hero.name}</div>
                        <div className="mt-1 text-[10px] font-bold tracking-[0.2em] text-[#f99e1a]">{hero.role}</div>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="absolute inset-0 bg-gradient-to-r from-[#11151d] via-[#11151d]/70 to-[#11151d]/35" />
                <div className="absolute inset-0 bg-gradient-to-b from-[#11151d]/20 via-transparent to-[#11151d]" />
              </div>
              <div className="absolute -right-28 top-24 h-80 w-80 rotate-45 border border-[#f99e1a]/20" />
              <div className="absolute -right-10 top-44 h-48 w-48 rotate-45 border border-[#61d8ff]/15" />
            </>
          )}
        </div>

        {!hasChat ? (
          <div className="relative z-[1] flex min-h-0 flex-1 flex-col items-center justify-center px-5 pb-20">
            <div className="mb-10 text-center">
              <div className="mx-auto mb-5 flex w-fit items-center gap-3 rounded-full border border-[#f99e1a]/25 bg-[#f99e1a]/10 px-4 py-2 text-xs font-bold uppercase tracking-[0.22em] text-[#ffd27a]">
                <Sparkle className="h-4 w-4" aria-hidden />
                OW2 intelligence online
              </div>
              <h1 className="text-5xl font-black uppercase italic tracking-[-0.04em] text-[#f8fbff] md:text-7xl">
                Overwatch 2
                <span className="block text-[#f99e1a] [text-shadow:0_0_34px_rgba(249,158,26,0.32)]">Intel Hub</span>
              </h1>
              <p className="mx-auto mt-4 max-w-xl text-sm leading-6 text-[#9fb0c8] md:text-base">
                Ask about hero damage, counters, comps, maps, and patch context from your indexed RAG corpus.
              </p>
            </div>

            <form onSubmit={submit} className="w-full max-w-[1054px]">
              <div className="relative overflow-hidden rounded-[30px] border border-[#f99e1a]/20 bg-[#1b2230]/90 px-8 py-7 shadow-[0_24px_90px_rgba(0,0,0,0.34),0_0_0_1px_rgba(97,216,255,0.06)] backdrop-blur">
                <div className="pointer-events-none absolute left-0 top-0 h-1 w-full bg-gradient-to-r from-[#f99e1a] via-[#ffd27a] to-[#61d8ff]" />
                <div className="pointer-events-none absolute -right-16 -top-16 h-32 w-32 rotate-45 border border-[#f99e1a]/20" />
                <textarea
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      event.currentTarget.form?.requestSubmit();
                    }
                  }}
                  placeholder="Ask for hero stats, counters, comps, patch notes..."
                  rows={3}
                  className="min-h-[76px] w-full resize-none bg-transparent text-xl leading-8 text-[#f8fbff] outline-none placeholder:text-[#718198]"
                />
                <div className="mt-2 flex justify-end">
                  <button
                    type="submit"
                    disabled={isStreaming || !input.trim()}
                    title="Send"
                    className="grid h-10 w-10 place-items-center rounded-full bg-[#f99e1a] text-[#11151d] transition hover:bg-[#ffd27a] disabled:bg-transparent disabled:text-[#718198]"
                  >
                    <ArrowUp className="h-5 w-5" aria-hidden />
                  </button>
                </div>
              </div>
            </form>
          </div>
        ) : (
          <>
            <div className="relative z-[1] min-h-0 flex-1 overflow-y-auto">
              <div className="mx-auto flex min-h-full max-w-3xl flex-col px-4 pb-36 pt-16">
                <div className="flex-1">
                  {turns.map((turn) => (
                    <ChatMessage key={turn.id} turn={turn} />
                  ))}
                  <div ref={bottomRef} />
                </div>
              </div>
            </div>

            <form onSubmit={submit} className="relative z-[1] shrink-0 border-t border-[#f99e1a]/10 bg-[#11151d]/95 p-4 backdrop-blur">
              <div className="mx-auto max-w-3xl">
                <div className="flex items-end gap-3 rounded-3xl border border-[#f99e1a]/20 bg-[#1b2230] px-4 py-3 shadow-2xl">
                  <textarea
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && !event.shiftKey) {
                        event.preventDefault();
                        event.currentTarget.form?.requestSubmit();
                      }
                    }}
                    placeholder="Message OW2 Hero Intelligence"
                    rows={1}
                    className="max-h-40 min-h-9 flex-1 resize-none bg-transparent py-2 text-sm leading-6 text-[#f8fbff] outline-none placeholder:text-[#718198]"
                  />
                  <button
                    type="button"
                    onClick={() => abortRef.current?.abort()}
                    disabled={!isStreaming}
                    title="Stop streaming"
                    className="grid h-9 w-9 shrink-0 place-items-center rounded-full border border-white/[0.08] text-[#cbd5e1] transition enabled:hover:bg-white/10 disabled:hidden"
                  >
                    <Square className="h-4 w-4" aria-hidden />
                  </button>
                  <button
                    type="submit"
                    disabled={isStreaming || !input.trim()}
                    title="Send"
                    className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[#f99e1a] text-[#11151d] transition hover:bg-[#ffd27a] disabled:bg-[#293241] disabled:text-[#718198]"
                  >
                    <ArrowUp className="h-5 w-5" aria-hidden />
                  </button>
                </div>
              </div>
            </form>
          </>
        )}
      </section>
    </main>
  );
}
