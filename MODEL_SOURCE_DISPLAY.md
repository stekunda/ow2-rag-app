# Model Source Display Feature

Now you can see which LLM model is being used to generate each answer on the frontend!

## What Changed

### Backend Changes

**1. `backend/schemas.py`** - Added `model_source` field
```python
class ChatResponse(BaseModel):
    answer: str
    session_id: str
    model_source: str | None = None  # NEW: Shows which LLM was used
    reasoning: list[ToolCall] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
```

**2. `backend/agents/ow2_agent.py`** - Updated LLM function to return model source
```python
# _llm_answer() now returns a tuple:
async def _llm_answer(...) -> tuple[str | None, str | None]:
    # Returns: (answer, model_source)
    # Example: ("Tracer is a Damage hero...", "Ollama (mistral)")
```

The function now tracks:
- `Ollama (mistral)` - Using local Ollama
- `OpenAI (gpt-4o-mini)` - Using OpenAI fallback
- `Hugging Face (Llama-2-7b-chat)` - Using HF fallback
- `Heuristic (no LLM)` - Using hardcoded responses (no API)

### Frontend Changes

**1. `frontend/lib/types.ts`** - Added `model_source` to ChatTurn
```typescript
export type ChatTurn = {
  id: string;
  role: "user" | "assistant";
  content: string;
  reasoning?: ToolCall[];
  sources?: Source[];
  model_source?: string | null;  // NEW
};
```

**2. `frontend/app/page.tsx`** - Extract model_source from API response
```typescript
if (event === "done") {
  const donePayload = JSON.parse(data) as {
    sources: Source[];
    reasoning: ToolCall[];
    model_source: string | null;  // NEW: Now captured from response
  };
  // Store model_source in ChatTurn
}
```

**3. `frontend/components/ChatMessage.tsx`** - Display model source badge
```tsx
<div className="mb-2 text-xs font-semibold uppercase tracking-wide text-ow-steel">
  {isAssistant ? "Agent" : "You"}
  {isAssistant && turn.model_source && (
    <span className="ml-2 inline-block rounded bg-ow-orange/10 px-2 py-1 text-ow-orange">
      {turn.model_source}  {/* Shows like: Ollama (mistral) */}
    </span>
  )}
  {isAssistant && !turn.model_source && (
    <span className="ml-2 inline-block rounded bg-yellow-500/10 px-2 py-1 text-yellow-400">
      No LLM
    </span>
  )}
</div>
```

## What You'll See

**When using Ollama locally:**
```
Agent | Ollama (mistral)
Tracer is a Damage hero with high mobility...
```

**When falling back to OpenAI:**
```
Agent | OpenAI (gpt-4o-mini)
Tracer is an offensive damage hero in Overwatch 2...
```

**When using Hugging Face:**
```
Agent | Hugging Face (Llama-2-7b-chat)
Tracer excels at dealing burst damage...
```

**When no LLM available (fallback):**
```
Agent | No LLM (shown in yellow)
Tracer is a damage hero who excels at close range...
```

## How to Test

1. **With Ollama running:**
   ```bash
   docker-compose up --build
   # or
   python -m uvicorn backend.main:app
   ```
   You should see: `Ollama (mistral)` badge

2. **Without Ollama (force fallback):**
   - Stop Ollama server
   - Unset `OPENAI_API_KEY` env var
   - Restart backend
   - You should see: `No LLM` badge

3. **With OpenAI (if configured):**
   ```bash
   export OPENAI_API_KEY=sk-...
   # Restart backend
   ```
   You should see: `OpenAI (gpt-4o-mini)` badge

## Data Flow

```
User asks question
    ↓
Frontend sends to /chat/stream
    ↓
Backend runs agent:
  1. Try Ollama → model_source = "Ollama (mistral)"
  2. Fallback OpenAI → model_source = "OpenAI (gpt-4o-mini)"
  3. Fallback HF → model_source = "Hugging Face (Llama-2-7b-chat)"
  4. Fallback heuristic → model_source = "Heuristic (no LLM)"
    ↓
ChatResponse returned with model_source in "done" event
    ↓
Frontend displays badge next to "Agent"
```

## Troubleshooting

**"No LLM" appears but Ollama is running:**
- Check that `OLLAMA_MODEL` env var is set
- Verify Ollama is accessible: `curl http://localhost:11434/api/tags`
- Check backend logs: `docker-compose logs -f backend`

**Wrong model showing:**
- Check `OLLAMA_MODEL` value: should be `mistral` or similar
- Check `OPENAI_API_KEY` if you expect OpenAI
- Frontend shows whatever the backend reports

**Badge not appearing at all:**
- Refresh the page (may need F5, not just cmd+R)
- Check browser console for errors
- Verify frontend is receiving `model_source` in response

## Performance Notes

- Badge appears as soon as the answer finishes streaming
- Model source is logged but doesn't affect latency
- All models try in order; each one adds ~0.1-0.5s if it fails

## Future Enhancements

Possible additions:
- Color-code badges by model type (local = green, paid = orange, heuristic = yellow)
- Show token count / inference time for each model
- Track which model performs best by user feedback
- A/B test different models
