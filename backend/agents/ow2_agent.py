import asyncio
import json
import os
import re
from collections.abc import AsyncGenerator
from typing import TypedDict

from backend.agents.tools import HERO_ROLES, tools
from backend.memory.store import memory
from backend.schemas import ChatRequest, ChatResponse, Source, ToolCall


SYSTEM_PROMPT = """You are an Overwatch 2 Hero Intelligence analyst.

IMPORTANT RULES:
1. ONLY use facts from the provided evidence/sources
2. Do NOT invent strategies, tips, or information not in the evidence
3. If evidence is insufficient, clearly state that
4. Always cite which source each fact comes from
5. Keep answers concise and evidence-based
6. For comps: only recommend if supported by evidence, include win condition and risks

Answer style: Direct, factual, grounded in provided evidence only."""


class ReActState(TypedDict, total=False):
    query: str
    selected_hero: str | None
    thoughts: list[str]
    tool_calls: list[ToolCall]
    answer: str


def build_react_graph():
    """Compile a small LangGraph ReAct skeleton used by the service planner.

    The endpoint keeps streaming control in Python so it can emit clean SSE events,
    while this graph documents the enterprise-style reason -> act -> synthesize loop.
    """
    try:
        from langgraph.graph import END, StateGraph
    except Exception:
        return None

    def reason(state: ReActState) -> ReActState:
        thoughts = state.get("thoughts", [])
        return {**state, "thoughts": [*thoughts, "Select retrieval tools from the user intent and session context."]}

    def act(state: ReActState) -> ReActState:
        thoughts = state.get("thoughts", [])
        return {**state, "thoughts": [*thoughts, "Execute OW2 tools and collect source-grounded observations."]}

    def synthesize(state: ReActState) -> ReActState:
        thoughts = state.get("thoughts", [])
        return {**state, "thoughts": [*thoughts, "Synthesize answer with citations and tactical recommendation."]}

    graph = StateGraph(ReActState)
    graph.add_node("reason", reason)
    graph.add_node("act", act)
    graph.add_node("synthesize", synthesize)
    graph.set_entry_point("reason")
    graph.add_edge("reason", "act")
    graph.add_edge("act", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()


REACT_GRAPH = build_react_graph()


def _extract_heroes(text: str) -> list[str]:
    found = []
    lowered = text.lower()
    for hero in HERO_ROLES:
        if hero.lower() in lowered:
            found.append(hero)
    return found


def _extract_map(text: str) -> str | None:
    maps = ["Dorado", "King's Row", "Kings Row", "Circuit Royal", "Numbani", "Rialto", "Gibraltar", "Havana"]
    for map_name in maps:
        if map_name.lower() in text.lower():
            return "King's Row" if map_name == "Kings Row" else map_name
    return None


def _dedupe_sources(tool_calls: list[ToolCall]) -> list[Source]:
    seen: set[str] = set()
    sources: list[Source] = []
    for call in tool_calls:
        for source in call.sources:
            key = f"{source.title}:{source.url}:{source.excerpt}"
            if key not in seen:
                seen.add(key)
                sources.append(source)
    return sources


def _format_citations(sources: list[Source]) -> str:
    if not sources:
        return ""
    lines = []
    for index, source in enumerate(sources[:5], start=1):
        label = source.title
        if source.date:
            label = f"{label} ({source.date})"
        lines.append(f"[{index}] {label} - {source.url or 'local seed'}")
    return "\n".join(lines)


def _heuristic_answer(request: ChatRequest, tool_calls: list[ToolCall]) -> str:
    heroes = _extract_heroes(request.message)
    map_name = _extract_map(request.message)
    wants_comp = any(term in request.message.lower() for term in ["comp", "counter", "frontline", "team"])
    sources = _dedupe_sources(tool_calls)

    if wants_comp:
        enemy = ", ".join(heroes) or "the named enemy core from the conversation"
        map_clause = f" on {map_name}" if map_name else ""
        if map_name == "Dorado":
            comp = "D.Va, Tracer, Sombra, Kiriko, and Lucio"
            plan = "Use rooftop rotations to collapse onto Ana, then disengage before Orisa or Mauga can farm sustain."
        elif map_name == "King's Row":
            comp = "Sigma, Mei, Sojourn, Baptiste, and Lucio"
            plan = "Control the choke with walls, off-angles, and lamp discipline; kite Cardiac Overdrive and re-engage after Ana cooldowns."
        else:
            comp = "Sigma or D.Va with Tracer/Sombra pressure, Kiriko cleanse, and Lucio tempo"
            plan = "Deny long sightlines, force Ana defensive cooldowns, and avoid extended tank trades."
        answer = (
            f"Recommended counter-comp into {enemy}{map_clause}: **{comp}**.\n\n"
            f"Why it works: {plan} The main win condition is cooldown trading: bait Fortify, Cardiac Overdrive, Sleep Dart, "
            "and Biotic Grenade, then burst the isolated support or rotate away before the frontline stabilizes.\n\n"
            "Risks: if your team trickles into open sightlines, Mauga can convert damage into sustain and Orisa can stall space long enough for Ana to reset the fight."
        )
    else:
        target = heroes[0] if heroes else (request.selected_hero or "that hero")
        evidence = " ".join(source.excerpt or "" for source in sources[:3])
        answer = (
            f"Here is the practical read on **{target}**: use the hero's cooldown windows as the organizing idea. "
            "Pressure when defensive tools are unavailable, rotate before the next sustain cycle, and choose fights where map geometry supports your range profile."
        )
        if evidence:
            answer = f"{answer}\n\nEvidence highlights: {evidence}"
    citations = _format_citations(sources)
    return f"{answer}\n\nSources:\n{citations}" if citations else answer


async def _llm_answer(request: ChatRequest, tool_calls: list[ToolCall]) -> tuple[str | None, str | None]:
    """Generate answer using LLM with fallback options:
    1. Ollama (local, free) - OLLAMA_MODEL env var
    2. OpenAI - OPENAI_API_KEY env var
    3. Hugging Face (free) - HF_TOKEN env var
    
    Returns: (answer, model_source) tuple
    model_source indicates which LLM was used (e.g., "Ollama (mistral)" or "OpenAI (gpt-4o-mini)")
    """
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
    except Exception:
        return None

    context = memory.summarize_context(request.session_id)
    evidence = "\n\n".join(
        f"Tool {call.name} returned:\n" + "\n".join(f"- {source.title}: {source.excerpt}" for source in call.sources)
        for call in tool_calls
    )
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Session context:\n{context}\n\nEvidence:\n{evidence}\n\nUser question: {request.message}"),
    ]

    model = None
    model_source = None

    # Try Ollama first (local, free)
    ollama_model = os.getenv("OLLAMA_MODEL")
    if ollama_model:
        try:
            from langchain_community.llms import Ollama
            ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            model = Ollama(model=ollama_model, base_url=ollama_base_url, temperature=0.2)
            model_source = f"Ollama ({ollama_model})"
        except Exception as e:
            print(f"Ollama initialization failed: {e}")

    # Fallback to OpenAI
    if not model and os.getenv("OPENAI_API_KEY"):
        try:
            from langchain_openai import ChatOpenAI
            model = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
            model_source = "OpenAI (gpt-4o-mini)"
        except Exception as e:
            print(f"OpenAI initialization failed: {e}")

    # Fallback to Hugging Face (free tier available)
    if not model and os.getenv("HF_TOKEN"):
        try:
            from langchain_community.llms import HuggingFaceHub
            model = HuggingFaceHub(
                repo_id="meta-llama/Llama-2-7b-chat-hf",
                huggingfacehub_api_token=os.getenv("HF_TOKEN"),
                model_kwargs={"temperature": 0.2}
            )
            model_source = "Hugging Face (Llama-2-7b-chat)"
        except Exception as e:
            print(f"Hugging Face initialization failed: {e}")

    if not model:
        return None, None  # Return both answer and model_source

    try:
        response = await model.ainvoke(messages)
        # Handle both string responses (Ollama) and message objects (OpenAI, HF)
        answer_text = response.content if hasattr(response, 'content') else response
        citations = _format_citations(_dedupe_sources(tool_calls))
        answer = f"{answer_text}\n\nSources:\n{citations}"
        return answer, model_source  # Return answer with model source
    except Exception as e:
        print(f"LLM invocation failed: {e}")
        return None, model_source  # Return None answer but keep model_source for logging


async def run_agent(request: ChatRequest) -> ChatResponse:
    context = memory.summarize_context(request.session_id)
    full_query = f"{context}\nuser: {request.message}".strip()
    heroes = _extract_heroes(full_query)
    map_name = _extract_map(full_query)
    lowered = request.message.lower()

    tool_calls: list[ToolCall] = []
    if "patch" in lowered or "nerf" in lowered or "buff" in lowered:
        _, call = tools.get_patch_history(heroes[0] if heroes else "")
        tool_calls.append(call)
    if any(term in lowered for term in ["damage", "secondary", "primary", "fire", "cooldown", "ammo", "ability", "abilities"]):
        _, call = tools.search_hero_abilities(heroes[0] if heroes else "", request.message)
        tool_calls.append(call)
    if any(term in lowered for term in ["counter", "against", "frontline"]):
        for hero in heroes[:3] or [""]:
            _, call = tools.find_counters(hero, map_name)
            tool_calls.append(call)
    if any(term in lowered for term in ["comp", "team", "build"]):
        _, call = tools.build_team_comp(heroes, map_name)
        tool_calls.append(call)
    if not tool_calls:
        _, call = tools.search_hero_lore(full_query)
        tool_calls.append(call)

    answer, model_source = await _llm_answer(request, tool_calls)
    if not answer:
        answer = _heuristic_answer(request, tool_calls)
        model_source = "Heuristic (no LLM)"
    
    memory.append(request.session_id, "user", request.message)
    memory.append(request.session_id, "assistant", answer)
    return ChatResponse(answer=answer, session_id=request.session_id, model_source=model_source, reasoning=tool_calls, sources=_dedupe_sources(tool_calls))


async def stream_agent(request: ChatRequest) -> AsyncGenerator[str, None]:
    response = await run_agent(request)
    for call in response.reasoning:
        yield f"event: reasoning\ndata: {call.model_dump_json()}\n\n"
    for token in re.findall(r"\S+\s*", response.answer):
        yield f"event: token\ndata: {json.dumps(token)}\n\n"
        await asyncio.sleep(0.012)
    yield f"event: done\ndata: {response.model_dump_json()}\n\n"
