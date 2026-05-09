# Chroma Data Flow Documentation

## Overview
This document explains the complete data pipeline from raw scraped documents to vectorized chunks stored in Chroma DB.

---

## Stage 1: Raw Scraped Documents

**Source**: `backend/data/scraped_hero_docs.json`
**Format**: JSON array of `ScrapedDocument` objects

### Example Raw Document:
```json
{
  "title": "Tracer - Special Abilities",
  "text": "Special Abilities. Blink LSHIFT 3 seconds , 3 charges Type Ability Effect Type Movement Teleport in the direction you are moving. Ability cooldown 3 seconds...",
  "hero": "Tracer",
  "category": "ability",
  "date": null,
  "url": "https://overwatch.fandom.com/wiki/Tracer#Special_Abilities"
}
```

### Current Cache Statistics:
- **Total Documents**: 69
- **Heroes**: Genji (26), Symmetra (22), Tracer (21)
- **Categories**:
  - ability: 15 documents
  - patch: 6 documents  
  - stats: 48 documents

---

## Stage 2: Semantic Chunking

**Function**: `semantic_chunks()` in `ingest.py` (lines 16-36)

### Purpose:
- Breaks long text into smaller, semantically meaningful chunks
- Improves embedding quality and retrieval precision
- Enables overlapping context between chunks

### Parameters:
- **max_chars**: 900 characters per chunk
- **overlap**: 120 characters overlap between consecutive chunks

### How It Works:
1. Split text by sentence boundaries (`(?<=[.!?])\s+`)
2. Group sentences into chunks ≤ 900 chars
3. Add 120-char overlap from previous chunk to current

### Example:
**Raw text (excerpt)**:
```
"Pulse Pistols: Tracer's primary weapon. Her primary fire rapidly shoots both pistols. 
Each bullet deals 6 damage. Her secondary fire shoots both pistols at once..."
```

**After Chunking** (with overlap):
```
Chunk 1:
"Pulse Pistols: Tracer's primary weapon. Her primary fire rapidly shoots both pistols. 
Each bullet deals 6 damage."

Chunk 2 (with 120-char overlap from Chunk 1):
"...deals 6 damage. Her secondary fire shoots both pistols at once..."
```

---

## Stage 3: Chroma Payload Construction

**Function**: `documents_to_chroma_payload()` (lines 79-96)

### Input:
- List of 69 `ScrapedDocument` objects

### Processing:
For each document:
1. Chunk the text using `semantic_chunks()`
2. Create metadata entry for each chunk
3. Generate deterministic UUID for each chunk

### Outputs (3 parallel lists):

#### 1. **texts** - The actual text content
```python
[
  "Pulse Pistols: Tracer's primary weapon...",
  "...Her primary fire rapidly shoots...",
  "Blink allows Tracer to teleport...",
  # ... more chunks
]
```

#### 2. **metadatas** - Context for each chunk
```python
[
  {
    "title": "Tracer - Special Abilities",
    "hero": "Tracer",
    "category": "ability",
    "date": "",
    "url": "https://overwatch.fandom.com/wiki/Tracer#Special_Abilities",
    "chunk": 0
  },
  {
    "title": "Tracer - Special Abilities",
    "hero": "Tracer",
    "category": "ability",
    "date": "",
    "url": "https://overwatch.fandom.com/wiki/Tracer#Special_Abilities",
    "chunk": 1
  },
  # ... more metadata
]
```

#### 3. **ids** - Unique identifiers
```python
[
  "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",  # UUID for chunk 0
  "b2c3d4e5-f6a7-48b9-c0d1-e2f3a4b5c6d7",  # UUID for chunk 1
  "c3d4e5f6-a7b8-49ca-d1e2-f3a4b5c6d7e8",  # UUID for chunk 2
  # ...
]
```

**UUID Generation** (line 94):
```python
uuid.uuid5(
  uuid.NAMESPACE_URL,
  f"{doc.url}:{doc.title}:{chunk_index}:{chunk[:80]}"
)
```
This ensures:
- Same document always produces same UUID
- UUID includes position (chunk_index) so multiple chunks from same doc have different IDs
- Deterministic: reproducible across runs

---

## Stage 4: Embedding Function

**Function**: `get_embedding_function()` (lines 98-102)

### Model:
- **Name**: `all-MiniLM-L6-v2`
- **Source**: SentenceTransformers library
- **Dimensions**: 384-dimensional vectors
- **Purpose**: Convert text → numeric vectors for semantic search

### Example:
```
Input text chunk:
"Pulse Pistols: Tracer's primary weapon. Her primary fire rapidly shoots both pistols."

↓ (Embedding)

Output vector:
[0.123, -0.456, 0.789, ..., 0.234]  # 384 dimensions
```

---

## Stage 5: Chroma Collection

**Function**: `get_chroma_client()` and `ingest_documents()` (lines 104-122)

### Collection Configuration:
```python
collection = client.get_or_create_collection(
    name="ow2_hero_intel",
    embedding_function=get_embedding_function(),  # all-MiniLM-L6-v2
    metadata={"hnsw:space": "cosine"}             # Cosine similarity search
)
```

### Collection Parameters:
- **name**: `ow2_hero_intel` (retrieved from env var)
- **embedding_function**: SentenceTransformer (all-MiniLM-L6-v2)
- **search metric**: Cosine similarity
  - Measures angle between vectors
  - 1.0 = identical meaning
  - 0.0 = perpendicular (no relation)
  - -1.0 = opposite meaning

### Storage Location:
```
If CHROMA_HOST env var set:
  → Remote HTTP client (production)
Else:
  → Local persistent storage at: backend/data/chroma/
```

### Upsert Operation:
```python
collection.upsert(
    documents=texts,      # The 900-char chunks
    metadatas=metadatas,  # Title, hero, category, etc.
    ids=ids                # UUIDs for deduplication
)
```

**Upsert** = Update or Insert
- If UUID already exists: replace with new data
- If UUID is new: add to collection
- Handles incremental updates from multiple scrapes

---

## Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  Overwatch Fandom Wiki                                      │
│  (https://overwatch.fandom.com/wiki/[Hero])                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ (cloudscraper)
┌─────────────────────────────────────────────────────────────┐
│  Raw HTML                                                   │
│  (Hero ability descriptions, patch notes, stats)            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ (BeautifulSoup parsing)
┌─────────────────────────────────────────────────────────────┐
│  ScrapedDocument Objects (69 total)                         │
│  {                                                          │
│    title: "Hero - Section",                                │
│    text: "Full section text...",                            │
│    hero: "HeroName",                                        │
│    category: "ability|patch|stats",                         │
│    url: "https://...",                                      │
│    date: null                                               │
│  }                                                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ (scraped_hero_docs.json)
┌─────────────────────────────────────────────────────────────┐
│  Cache: backend/data/scraped_hero_docs.json                 │
│  (119.5 KB, 69 documents)                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ (semantic_chunks)
┌─────────────────────────────────────────────────────────────┐
│  Chunked Text (900 chars, 120-char overlap)                 │
│  [                                                          │
│    "Chunk 1...",                                            │
│    "...overlap... Chunk 2...",                              │
│    "...overlap... Chunk 3...",                              │
│  ]                                                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ (all-MiniLM-L6-v2 embedder)
┌─────────────────────────────────────────────────────────────┐
│  Embedded Vectors (384-dimensional)                         │
│  [                                                          │
│    [0.123, -0.456, 0.789, ..., 0.234],  # Chunk 1         │
│    [0.345, -0.678, 0.901, ..., 0.456],  # Chunk 2         │
│    [0.567, -0.890, 0.123, ..., 0.678],  # Chunk 3         │
│  ]                                                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ (upsert with metadata)
┌─────────────────────────────────────────────────────────────┐
│  Chroma Collection: "ow2_hero_intel"                        │
│  Storage: backend/data/chroma/                              │
│                                                             │
│  For each chunk:                                            │
│  {                                                          │
│    id: "a1b2c3d4-...",     # UUID (deterministic)          │
│    embedding: [0.123, ...],  # 384-dim vector              │
│    text: "Chunk 1...",       # Raw text                     │
│    metadata: {               # Searchable context           │
│      title: "Hero - Section",                              │
│      hero: "HeroName",                                      │
│      category: "ability",                                   │
│      url: "https://...",                                    │
│      chunk: 0                                               │
│    }                                                        │
│  }                                                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ (Cosine similarity search)
┌─────────────────────────────────────────────────────────────┐
│  RAG Agent Query                                            │
│  "What are Tracer's abilities?"                             │
│                                                             │
│  → Embed query to vector                                    │
│  → Find closest chunks (cosine similarity)                  │
│  → Return top K results with metadata                       │
│  → Feed to LLM for answer generation                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Statistics

### Documents & Chunks:
| Metric | Value |
|--------|-------|
| Raw Documents | 69 |
| Average text per doc | ~2,000 chars |
| Max chunks per doc | 3-5 chunks |
| Estimated total chunks | ~300-350 chunks |
| File size (cached) | 119.5 KB |
| Embedding dimensions | 384 |
| Vector storage size | ~13-15 MB (300-350 chunks × 384 dims × 4 bytes) |

### By Hero:
| Hero | Documents | Est. Chunks |
|------|-----------|-------------|
| Genji | 26 | ~80-100 |
| Symmetra | 22 | ~65-85 |
| Tracer | 21 | ~60-80 |

### By Category:
| Category | Documents | Examples |
|----------|-----------|----------|
| ability | 15 | Weapon stats, ability descriptions, cooldowns |
| patch | 6 | Balance history, damage changes |
| stats | 48 | Matchups, lore, character info |

---

## Search Example

**User Query**: "How do I counter Tracer?"

### Step 1: Embed Query
```python
query_vector = embedding_function.encode(
    "How do I counter Tracer?"
)
# Result: [0.234, -0.567, 0.890, ..., 0.123]  (384 dims)
```

### Step 2: Vector Search
```python
results = collection.query(
    query_embeddings=[query_vector],
    n_results=5,  # Top 5 chunks
    where={"hero": "Tracer"}  # Optional filter
)
```

### Step 3: Retrieved Chunks (sorted by cosine similarity):
```
1. [0.92 similarity]
   "Against Tracer: Her high mobility makes her difficult to pin down.
    Hitscan heroes can pressure her effectively. Use large hitbox abilities..."
   {hero: "Widowmaker", category: "stats", title: "Widowmaker - Matchups"}

2. [0.88 similarity]
   "Tracer struggles against heroes with area-of-effect abilities that she
    cannot easily escape from. Junkrat and Pharah provide good counterplay..."
   {hero: "Tracer", category: "stats", title: "Tracer - Counters"}

3. [0.85 similarity]
   "Blink has a 3-second cooldown and 3 charges maximum. Without Blink,
    Tracer becomes vulnerable to dive attacks and burst damage..."
   {hero: "Tracer", category: "ability", title: "Tracer - Special Abilities"}

4-5. [lower similarity scores]...
```

### Step 4: Feed to LLM
```
Context from Chroma:
- Tracer struggles vs AoE
- Hitscan heroes pressure her
- She's weak without Blink

LLM generates answer:
"To counter Tracer, pick heroes with large hitbox abilities like Junkrat
or Pharah. Widowmaker and hitscan heroes can also pressure her effectively..."
```

---

## Configuration

### Environment Variables:
```bash
CHROMA_COLLECTION=ow2_hero_intel      # Collection name
CHROMA_HOST=                           # Optional remote host
CHROMA_PORT=8000                       # Remote port (if CHROMA_HOST set)
```

### Semantic Chunking:
```python
max_chars=900          # Chunk size
overlap=120            # Overlap length
                       # Ensures context continuity between chunks
```

### Embedding Model:
```python
model_name="all-MiniLM-L6-v2"
# - Small (22MB): Fast, good for semantic search
# - 384 dimensions: Balanced precision/storage
# - Sentence-level: Works well for ability descriptions
```

### Search Configuration:
```python
hnsw:space=cosine      # Hierarchical Navigable Small World
                       # Fast approximate nearest neighbor search
```

---

## Workflow Commands

### 1. Scrape & Cache Only
```bash
python3 -m backend.ingestion.ingest --scrape-only --heroes Hanzo
# → Adds Hanzo docs to scraped_hero_docs.json (merges with existing)
```

### 2. Scrape & Ingest to Chroma
```bash
python3 -m backend.ingestion.ingest --scrape --heroes Hanzo
# → Scrapes Hanzo
# → Merges with cached docs
# → Chunks all 69 docs
# → Embeds chunks
# → Upserts to Chroma collection
```

### 3. Ingest Cached Docs to Chroma
```bash
python3 -m backend.ingestion.ingest --ingest-scraped
# → Loads all 69 cached docs
# → Chunks them
# → Embeds them
# → Upserts to Chroma
```

### 4. View Statistics
```bash
python3 -m backend.ingestion.ingest --stats
# Shows: seed docs, scraped docs, heroes, categories, vector chunks
```

---

## Troubleshooting

### Issue: "Failed to send telemetry event"
**Cause**: Chroma telemetry callback signature mismatch
**Solution**: Set `CHROMA_TELEMETRY_ENABLED=false` or upgrade chromadb

### Issue: 403 Forbidden when scraping
**Cause**: Cloudflare protection on Fandom wiki
**Solution**: cloudscraper automatically handles this (installed in venv)

### Issue: Chunks in Chroma seem incomplete
**Possible causes**:
- Text doesn't have enough sentences for 900-char chunks
- Overlap setting removing context
- Metadata not properly serialized

### Issue: Search results not relevant
**Checks**:
1. Verify chunks exist: `collection.count()`
2. Check embedding function: `embedding_function.encode("test")`
3. Test query on known content
4. Try different `n_results` or similarity threshold

---

## Next Steps

1. **Start the backend**: `uvicorn backend.main:app --reload`
2. **Query via API**: POST `/chat` with question
3. **Monitor Chroma**: Check `backend/data/chroma/` directory
4. **Expand heroes**: Scrape more heroes incrementally
5. **Monitor retrieval**: Add logging to see which chunks are retrieved

