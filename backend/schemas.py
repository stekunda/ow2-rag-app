from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


HeroRole = Literal["Tank", "Damage", "Support"]


class Source(BaseModel):
    title: str
    url: str | None = None
    hero: str | None = None
    category: str | None = None
    date: str | None = None
    excerpt: str | None = None


class ToolCall(BaseModel):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float | None = None
    sources: list[Source] = Field(default_factory=list)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    selected_hero: str | None = None
    stream_reasoning: bool = True


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    model_source: str | None = None  # Which LLM was used (e.g., "Ollama (mistral)" or "OpenAI (gpt-4o-mini)")
    reasoning: list[ToolCall] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)


class EvalCase(BaseModel):
    question: str
    expected_facts: list[str]


class EvalResult(BaseModel):
    question: str
    passed: bool
    missing_facts: list[str]
    latency_ms: float
    answer: str


class EvalResponse(BaseModel):
    accuracy: float
    hallucinations: list[str]
    results: list[EvalResult]


class BenchmarkResult(BaseModel):
    query: str
    naive_answer: str
    agent_answer: str
    naive_latency_ms: float
    agent_latency_ms: float
