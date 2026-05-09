import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.agents.ow2_agent import run_agent, stream_agent
from backend.config import get_settings
from backend.ingestion.ingest import corpus_stats, ingest_documents, scrape_and_ingest
from backend.schemas import BenchmarkResult, ChatRequest, ChatResponse, EvalCase, EvalResponse, EvalResult


settings = get_settings()

if settings.langchain_api_key:
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    os.environ["LANGCHAIN_TRACING_V2"] = "true" if settings.langchain_tracing_v2 else "false"


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        ingest_documents()
    except Exception:
        pass
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


EVAL_CASES = [
    EvalCase(question="What role is Ana and what is Biotic Grenade used for?", expected_facts=["Support", "prevents enemy healing"]),
    EvalCase(question="What does Defense Matrix do?", expected_facts=["absorb", "projectiles"]),
    EvalCase(question="How should I play against Mauga sustain?", expected_facts=["line of sight", "sustain"]),
    EvalCase(question="Build a comp to counter Orisa Mauga Ana on Dorado", expected_facts=["Dorado", "Ana"]),
    EvalCase(question="What kind of map is Dorado?", expected_facts=["Escort", "high ground"]),
    EvalCase(question="What kind of map is King's Row?", expected_facts=["Hybrid", "chokes"]),
    EvalCase(question="Name one Orisa defensive ability", expected_facts=["Fortify"]),
    EvalCase(question="What changed in Season 9?", expected_facts=["health", "Damage role passive"]),
    EvalCase(question="What does Mauga use for sustain?", expected_facts=["Cardiac Overdrive"]),
    EvalCase(question="How do you counter Ana in a tank-heavy comp?", expected_facts=["pressure Ana"]),
]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    return await run_agent(request)


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(stream_agent(request), media_type="text/event-stream")


@app.post("/ingest")
async def ingest() -> dict[str, int]:
    return {"chunks": ingest_documents()}


@app.post("/ingest/scrape")
async def scrape_ingest(heroes: str | None = None) -> dict[str, int | str]:
    hero_list = [hero.strip() for hero in heroes.split(",")] if heroes else None
    chunks = await scrape_and_ingest(hero_list)
    return {"chunks": chunks, "mode": "scraped_heroes"}


@app.get("/corpus/stats")
async def stats() -> dict:
    return corpus_stats()


@app.get("/heroes")
async def heroes() -> list[dict[str, str]]:
    from backend.agents.tools import HERO_ROLES

    return [{"name": name, "role": role} for name, role in sorted(HERO_ROLES.items())]


@app.get("/eval", response_model=EvalResponse)
async def eval_suite() -> EvalResponse:
    results: list[EvalResult] = []
    hallucinations: list[str] = []
    for case in EVAL_CASES:
        start = time.perf_counter()
        response = await run_agent(ChatRequest(message=case.question, session_id="eval"))
        latency_ms = (time.perf_counter() - start) * 1000
        lowered = response.answer.lower()
        missing = [fact for fact in case.expected_facts if fact.lower() not in lowered]
        if missing:
            hallucinations.append(f"Question '{case.question}' missed facts: {', '.join(missing)}")
        results.append(EvalResult(question=case.question, passed=not missing, missing_facts=missing, latency_ms=latency_ms, answer=response.answer))
    accuracy = sum(1 for result in results if result.passed) / len(results)
    return EvalResponse(accuracy=accuracy, hallucinations=hallucinations, results=results)


@app.get("/benchmark", response_model=list[BenchmarkResult])
async def benchmark() -> list[BenchmarkResult]:
    queries = [
        "Build a comp to counter Orisa Mauga Ana on Dorado",
        "What about on King's Row instead?",
    ]
    rows: list[BenchmarkResult] = []
    for query in queries:
        naive_start = time.perf_counter()
        naive = await run_agent(ChatRequest(message=query, session_id="benchmark-naive", stream_reasoning=False))
        naive_latency = (time.perf_counter() - naive_start) * 1000
        agent_start = time.perf_counter()
        agent = await run_agent(ChatRequest(message=query, session_id="benchmark-agent", stream_reasoning=True))
        agent_latency = (time.perf_counter() - agent_start) * 1000
        rows.append(
            BenchmarkResult(
                query=query,
                naive_answer=naive.answer,
                agent_answer=agent.answer,
                naive_latency_ms=naive_latency,
                agent_latency_ms=agent_latency,
            )
        )
    return rows
