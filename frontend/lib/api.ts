import type { Hero } from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export async function fetchHeroes(): Promise<Hero[]> {
  const response = await fetch(`${API_BASE}/heroes`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Unable to load heroes");
  }
  return response.json();
}
