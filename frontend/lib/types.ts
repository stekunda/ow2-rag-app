export type HeroRole = "Tank" | "Damage" | "Support";

export type Hero = {
  name: string;
  role: HeroRole;
};

export type Source = {
  title: string;
  url?: string | null;
  hero?: string | null;
  category?: string | null;
  date?: string | null;
  excerpt?: string | null;
};

export type ToolCall = {
  name: string;
  args: Record<string, unknown>;
  latency_ms?: number | null;
  sources: Source[];
};

export type ChatTurn = {
  id: string;
  role: "user" | "assistant";
  content: string;
  reasoning?: ToolCall[];
  sources?: Source[];
  model_source?: string | null;  // Which LLM was used (e.g., "Ollama (mistral)")
};
