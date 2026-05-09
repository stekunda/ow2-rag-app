import json
import os
import re
import uuid
import argparse
import asyncio
from pathlib import Path
from typing import Any, Iterable

from backend.ingestion.scraper import DEFAULT_HEROES, ScrapedDocument, scrape_heroes

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SEED_DOCS = DATA_DIR / "seed_docs.json"
SCRAPED_DOCS = DATA_DIR / "scraped_hero_docs.json"


def semantic_chunks(text: str, max_chars: int = 900, overlap: int = 120) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if not sentence:
            continue
        if len(current) + len(sentence) + 1 <= max_chars:
            current = f"{current} {sentence}".strip()
            continue
        if current:
            chunks.append(current)
        current = sentence
    if current:
        chunks.append(current)
    if overlap <= 0 or len(chunks) < 2:
        return chunks
    overlapped: list[str] = []
    for index, chunk in enumerate(chunks):
        prefix = chunks[index - 1][-overlap:] if index else ""
        overlapped.append(f"{prefix} {chunk}".strip())
    return overlapped


def load_seed_documents() -> list[ScrapedDocument]:
    raw = json.loads(SEED_DOCS.read_text())
    return [ScrapedDocument(**item) for item in raw]


def load_scraped_documents() -> list[ScrapedDocument]:
    if not SCRAPED_DOCS.exists():
        return []
    raw = json.loads(SCRAPED_DOCS.read_text())
    return [ScrapedDocument(**item) for item in raw]


def save_documents(docs: Iterable[ScrapedDocument], path: Path = SCRAPED_DOCS, merge: bool = True) -> int:
    docs = list(docs)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # If merge is True and file exists, merge with existing documents
    if merge and path.exists():
        existing = load_scraped_documents()
        # Create a dict keyed by (hero, title, url) to avoid duplicates
        existing_dict = {(d.hero, d.title, d.url): d for d in existing}
        new_dict = {(d.hero, d.title, d.url): d for d in docs}
        # Merge: new docs override existing ones with same key
        existing_dict.update(new_dict)
        docs = list(existing_dict.values())
    
    path.write_text(json.dumps([doc.__dict__ for doc in docs], indent=2))
    return len(docs)


def corpus_stats() -> dict[str, Any]:
    seed_docs = load_seed_documents()
    scraped_docs = load_scraped_documents()
    by_hero: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for doc in [*seed_docs, *scraped_docs]:
        by_hero[doc.hero or "global"] = by_hero.get(doc.hero or "global", 0) + 1
        by_category[doc.category] = by_category.get(doc.category, 0) + 1
    stats: dict[str, Any] = {
        "seed_documents": len(seed_docs),
        "scraped_documents": len(scraped_docs),
        "heroes": by_hero,
        "categories": by_category,
        "scraped_docs_path": str(SCRAPED_DOCS),
    }
    try:
        stats["vector_chunks"] = get_chroma_client().get_or_create_collection(
            name=os.getenv("CHROMA_COLLECTION", "ow2_hero_intel"),
            embedding_function=get_embedding_function(),
        ).count()
    except Exception:
        stats["vector_chunks"] = None
    return stats


def documents_to_chroma_payload(docs: Iterable[ScrapedDocument]) -> tuple[list[str], list[dict[str, Any]], list[str]]:
    texts: list[str] = []
    metadatas: list[dict[str, Any]] = []
    ids: list[str] = []
    for doc in docs:
        for chunk_index, chunk in enumerate(semantic_chunks(doc.text)):
            texts.append(chunk)
            metadatas.append(
                {
                    "title": doc.title,
                    "hero": doc.hero or "",
                    "category": doc.category,
                    "date": doc.date or "",
                    "url": doc.url,
                    "chunk": chunk_index,
                }
            )
            ids.append(str(uuid.uuid5(uuid.NAMESPACE_URL, f"{doc.url}:{doc.title}:{chunk_index}:{chunk[:80]}")))
    return texts, metadatas, ids


def get_embedding_function():
    from chromadb.utils import embedding_functions

    return embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")


def get_chroma_client():
    import chromadb

    host = os.getenv("CHROMA_HOST")
    if host:
        return chromadb.HttpClient(host=host, port=int(os.getenv("CHROMA_PORT", "8000")))
    return chromadb.PersistentClient(path=str(DATA_DIR / "chroma"))


def ingest_documents(docs: Iterable[ScrapedDocument] | None = None) -> int:
    docs = list(docs or load_seed_documents())
    texts, metadatas, ids = documents_to_chroma_payload(docs)
    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=os.getenv("CHROMA_COLLECTION", "ow2_hero_intel"),
        embedding_function=get_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )
    if texts:
        collection.upsert(documents=texts, metadatas=metadatas, ids=ids)
    return len(texts)


async def scrape_documents(heroes: Iterable[str] | None = None, persist: bool = True) -> list[ScrapedDocument]:
    docs = await scrape_heroes(heroes or DEFAULT_HEROES)
    if not docs:
        docs = load_seed_documents()
    if persist:
        save_documents(docs)
    return docs


async def scrape_and_ingest(heroes: Iterable[str] | None = None, persist: bool = True) -> int:
    docs = await scrape_documents(heroes, persist)
    return ingest_documents(docs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Overwatch 2 hero intelligence documents.")
    parser.add_argument("--scrape", action="store_true", help="Scrape hero pages, write JSON, then ingest into Chroma.")
    parser.add_argument("--scrape-only", action="store_true", help="Scrape hero pages and write JSON without requiring Chroma.")
    parser.add_argument("--ingest-scraped", action="store_true", help="Ingest backend/data/scraped_hero_docs.json into Chroma.")
    parser.add_argument("--heroes", help="Comma-separated hero list, for example: Genji,Ana")
    parser.add_argument("--stats", action="store_true", help="Print corpus stats instead of ingesting.")
    args = parser.parse_args()

    if args.stats:
        print(json.dumps(corpus_stats(), indent=2))
    elif args.scrape_only:
        hero_list = [hero.strip() for hero in args.heroes.split(",")] if args.heroes else None
        docs = asyncio.run(scrape_documents(hero_list, persist=True))
        print(f"Scraped {len(docs)} documents to {SCRAPED_DOCS}")
    elif args.ingest_scraped:
        print(f"Ingested {ingest_documents(load_scraped_documents())} scraped chunks")
    elif args.scrape:
        hero_list = [hero.strip() for hero in args.heroes.split(",")] if args.heroes else None
        print(f"Ingested {asyncio.run(scrape_and_ingest(hero_list))} scraped chunks")
    else:
        print(f"Ingested {ingest_documents()} chunks")
