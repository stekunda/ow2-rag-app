# OW2 Hero Intelligence RAG Chatbot

A full-stack Overwatch 2 hero intelligence chatbot that demonstrates production-grade AI engineering patterns: RAG ingestion, LangGraph ReAct tool orchestration, FastAPI streaming, ChromaDB retrieval, session memory, LangSmith observability hooks, evals, and a polished Next.js interface.

## Architecture

```text
User
  |
  v
Next.js 14 chat UI --SSE--> FastAPI /chat/stream
                              |
                              v
                        OW2 ReAct Agent
                              |
          +-------------------+-------------------+
          |                   |                   |
 search_hero_lore   find_counters/build_team_comp  get_patch_history
          |                   |                   |
          +-------------------+-------------------+
                              |
                              v
                  ChromaDB + sentence-transformers
                              |
                              v
       Overwatch Wiki scraper + semantic chunk ingestion
```

## Features

- FastAPI backend with async endpoints and Server-Sent Events token streaming.
- Agent tools: `search_hero_lore`, `get_patch_history`, `find_counters`, and `build_team_comp`.
- ChromaDB vector store with `all-MiniLM-L6-v2` sentence-transformer embeddings.
- BeautifulSoup scraper for Overwatch Wiki hero pages.
- Metadata-aware semantic chunking with hero, category, date, title, and URL tags.
- LangSmith environment integration for trace logging when keys are provided.
- Pydantic request and response schemas.
- Session memory for follow-up questions such as "what about on King's Row instead?"
- `/eval` endpoint with 10 ground-truth checks and hallucination logging.
- `/benchmark` endpoint comparing two RAG execution modes.
- Docker Compose for backend, ChromaDB, and frontend.

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Open the app at [http://localhost:3000](http://localhost:3000).

The backend is available at [http://localhost:8000](http://localhost:8000), and Chroma is exposed at `localhost:8001`.

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
uvicorn backend.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Environment

```text
OPENAI_API_KEY=             # Optional; enables LLM synthesis. Fallback synthesis works without it.
LANGCHAIN_API_KEY=          # Optional; enables LangSmith tracing.
LANGCHAIN_PROJECT=ow2-rag
LANGCHAIN_TRACING_V2=true
CHROMA_HOST=localhost
CHROMA_PORT=8001
CHROMA_COLLECTION=ow2_hero_intel
VECTOR_STORE=chroma         # Stretch hook for pgvector.
FRONTEND_ORIGIN=http://localhost:3000
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

## API

- `GET /health` returns service status.
- `GET /heroes` returns all OW2 heroes with roles.
- `POST /chat` returns a complete agent answer.
- `POST /chat/stream` streams `reasoning`, `token`, and `done` SSE events.
- `POST /ingest` loads seed documents into Chroma.
- `POST /ingest/scrape?heroes=Genji,Ana` scrapes selected hero pages, writes `backend/data/scraped_hero_docs.json`, and ingests the chunks.
- `GET /corpus/stats` shows seed document counts, scraped document counts, categories, heroes, and vector chunk count when Chroma is available.
- `GET /eval` runs 10 ground-truth QA checks.
- `GET /benchmark` compares naive RAG and agent-style responses.

## Scraping Hero Data

Start small with one hero:

```bash
python -m backend.ingestion.ingest --scrape-only --heroes Genji
python -m backend.ingestion.ingest --stats
```

When ChromaDB and backend dependencies are available, ingest the scraped JSON:

```bash
python -m backend.ingestion.ingest --ingest-scraped
```

Or through the running API:

```bash
curl -X POST "http://localhost:8000/ingest/scrape?heroes=Genji"
curl "http://localhost:8000/corpus/stats"
```

Once the generated `backend/data/scraped_hero_docs.json` looks good, expand to all heroes:

```bash
python -m backend.ingestion.ingest --scrape-only
```

## Example Queries

- `Build me a comp to counter an Orisa/Mauga/Ana frontline on Dorado.`
- `What about on King's Row instead?`
- `What does Defense Matrix do and when should I hold it?`
- `Summarize Ana's utility and cite the source.`
- `What changed in the Season 9 global patch?`

## Notes

The repo includes seed OW2 documents so the demo starts even without external scraping or API keys. Running `/ingest` uses those seeds by default. The scraper in `backend/ingestion/scraper.py` can be extended or scheduled to refresh Overwatch Wiki content.

The `VECTOR_STORE=pgvector` option is reserved as a stretch hook; the current implementation uses Chroma in both Docker and local fallback modes.
