import json
import math
import os
import time
from pathlib import Path
from typing import Any, Callable

from backend.ingestion.ingest import documents_to_chroma_payload, get_chroma_client, get_embedding_function, load_scraped_documents, load_seed_documents
from backend.schemas import Source, ToolCall


HERO_ROLES = {
    "D.Va": "Tank", "Doomfist": "Tank", "Junker Queen": "Tank", "Mauga": "Tank", "Orisa": "Tank",
    "Ramattra": "Tank", "Reinhardt": "Tank", "Roadhog": "Tank", "Sigma": "Tank", "Winston": "Tank",
    "Wrecking Ball": "Tank", "Zarya": "Tank", "Ana": "Support", "Baptiste": "Support", "Brigitte": "Support",
    "Illari": "Support", "Kiriko": "Support", "Lifeweaver": "Support", "Lucio": "Support", "Mercy": "Support",
    "Moira": "Support", "Zenyatta": "Support", "Ashe": "Damage", "Bastion": "Damage", "Cassidy": "Damage",
    "Echo": "Damage", "Genji": "Damage", "Hanzo": "Damage", "Junkrat": "Damage", "Mei": "Damage",
    "Pharah": "Damage", "Reaper": "Damage", "Sojourn": "Damage", "Soldier: 76": "Damage", "Sombra": "Damage",
    "Symmetra": "Damage", "Torbjorn": "Damage", "Tracer": "Damage", "Venture": "Damage", "Widowmaker": "Damage",
}


class LocalRetriever:
    def __init__(self) -> None:
        self.docs = [*load_seed_documents(), *load_scraped_documents()]

    def query(self, query: str, n_results: int = 5, where: dict[str, str] | None = None) -> dict[str, Any]:
        query_terms = set(query.lower().replace("/", " ").replace(",", " ").split())
        scored = []
        for doc in self.docs:
            if where:
                skip = False
                for key, value in where.items():
                    if str(getattr(doc, key) or "") != value:
                        skip = True
                if skip:
                    continue
            text = f"{doc.title} {doc.text}".lower()
            score = sum(1 for term in query_terms if term in text) / math.sqrt(max(len(text.split()), 1))
            scored.append((score, doc))
        scored.sort(key=lambda item: item[0], reverse=True)
        selected = [doc for score, doc in scored[:n_results] if score > 0] or [doc for _, doc in scored[:n_results]]
        return {
            "documents": [[doc.text for doc in selected]],
            "metadatas": [[{"title": doc.title, "hero": doc.hero or "", "category": doc.category, "date": doc.date or "", "url": doc.url} for doc in selected]],
        }


class HeroIntelTools:
    def __init__(self) -> None:
        self._collection = None
        self._local = LocalRetriever()
        try:
            client = get_chroma_client()
            self._collection = client.get_or_create_collection(
                name=os.getenv("CHROMA_COLLECTION", "ow2_hero_intel"),
                embedding_function=get_embedding_function(),
            )
            if self._collection.count() == 0:
                texts, metadatas, ids = documents_to_chroma_payload(load_seed_documents())
                self._collection.upsert(documents=texts, metadatas=metadatas, ids=ids)
        except Exception:
            self._collection = None

    @staticmethod
    def _sources(result: dict[str, Any]) -> list[Source]:
        docs = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        sources: list[Source] = []
        for text, meta in zip(docs, metadatas):
            sources.append(
                Source(
                    title=meta.get("title", "OW2 source"),
                    url=meta.get("url") or None,
                    hero=meta.get("hero") or None,
                    category=meta.get("category") or None,
                    date=meta.get("date") or None,
                    excerpt=text[:320],
                )
            )
        return sources

    def retrieve(self, query: str, n_results: int = 5, where: dict[str, str] | None = None) -> list[Source]:
        if self._collection is not None:
            try:
                result = self._collection.query(query_texts=[query], n_results=n_results, where=where)
                return self._sources(result)
            except Exception:
                pass
        return self._sources(self._local.query(query, n_results=n_results, where=where))

    def _timed(self, name: str, args: dict[str, Any], fn: Callable[[], list[Source]]) -> tuple[str, ToolCall]:
        start = time.perf_counter()
        sources = fn()
        latency_ms = (time.perf_counter() - start) * 1000
        body = "\n".join(f"- {source.title}: {source.excerpt}" for source in sources)
        return body, ToolCall(name=name, args=args, latency_ms=latency_ms, sources=sources)

    def search_hero_lore(self, query: str) -> tuple[str, ToolCall]:
        return self._timed("search_hero_lore", {"query": query}, lambda: self.retrieve(f"lore story biography {query}", 5))

    def search_hero_abilities(self, hero: str, query: str) -> tuple[str, ToolCall]:
        return self._timed("search_hero_abilities", {"hero": hero, "query": query}, lambda: self.retrieve(f"ability stats damage cooldown ammo {hero} {query}", 7))

    def get_patch_history(self, hero: str) -> tuple[str, ToolCall]:
        return self._timed("get_patch_history", {"hero": hero}, lambda: self.retrieve(f"{hero} patch notes balance changes", 5))

    def find_counters(self, hero: str, map_type: str | None = None) -> tuple[str, ToolCall]:
        query = f"counterplay counters against {hero} {map_type or ''}"
        return self._timed("find_counters", {"hero": hero, "map_type": map_type}, lambda: self.retrieve(query, 5))

    def build_team_comp(self, enemy_team: list[str], map_type: str | None = None) -> tuple[str, ToolCall]:
        enemy = ", ".join(enemy_team)
        query = f"build team comp counter {enemy} {map_type or ''} high ground sustain dive brawl"
        return self._timed("build_team_comp", {"enemy_team": enemy_team, "map_type": map_type}, lambda: self.retrieve(query, 6))


tools = HeroIntelTools()
