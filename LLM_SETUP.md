# LLM Configuration Guide

Your backend now supports **3 LLM options** with automatic fallback:

## 1. **Ollama (LOCAL - RECOMMENDED)** ⭐

### Setup:
```bash
# Install Ollama from https://ollama.ai
# Start the Ollama server
ollama serve

# In another terminal, pull a model
ollama pull mistral    # Fast, lightweight (~4GB)
# or
ollama pull neural-chat  # Fast, good quality (~4GB)
ollama pull llama2     # Larger, better quality (~7GB)
ollama pull zephyr     # Optimized for Q&A (~7GB)
```

### Configuration:
```bash
# Set in .env.local or export
export OLLAMA_MODEL=mistral
export OLLAMA_BASE_URL=http://localhost:11434  # Default
```

### Advantages:
- ✅ Completely free (no API costs)
- ✅ Runs locally (privacy, no data sent to cloud)
- ✅ Fast responses (GPU accelerated if available)
- ✅ Works offline
- ✅ No API keys needed

### Models to try:
| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| mistral | 4GB | Fast | Good | Default choice |
| neural-chat | 4GB | Fast | Good | Conversational |
| zephyr | 7GB | Medium | Excellent | Technical Q&A |
| llama2 | 7GB | Medium | Good | General purpose |
| openchat | 3GB | Very Fast | Fair | Fast responses |

---

## 2. **OpenAI (Cloud, Paid)**

### Setup:
```bash
export OPENAI_API_KEY=sk-your-key-here
```

### Cost:
- ~$0.15 per 1K input tokens
- ~$0.60 per 1K output tokens
- GPT-4o-mini is the cheapest option

### Advantages:
- ✅ Best quality responses
- ✅ Most reliable
- ❌ Costs money per request
- ❌ Data sent to OpenAI servers

---

## 3. **Hugging Face (Cloud, Free Tier)**

### Setup:
```bash
# 1. Get free token from https://huggingface.co/settings/tokens
# 2. Set environment variable
export HF_TOKEN=hf_your_token_here
```

### Cost:
- Free tier: Limited (inference API)
- Paid tier: $9/month+

### Advantages:
- ✅ Free to start
- ✅ Good models available
- ❌ Limited free tier requests/hour
- ❌ Slower than local/OpenAI
- ❌ Data sent to Hugging Face

---

## Current Code Behavior

The `_llm_answer()` function tries in this order:

```
1. OLLAMA_MODEL set? → Use Ollama (local)
   └─ If fails or not set...
   
2. OPENAI_API_KEY set? → Use OpenAI
   └─ If fails or not set...
   
3. HF_TOKEN set? → Use Hugging Face
   └─ If fails or not set...
   
4. Fall back to → _heuristic_answer() (hardcoded rules)
```

So you can:
- Try Ollama first (free, local)
- Keep OpenAI as backup
- Fallback to heuristic if both fail

---

## Testing Your Setup

### Test Ollama locally:
```bash
# 1. Start Ollama server
ollama serve

# 2. In another terminal, test the model
curl http://localhost:11434/api/generate -d '{
  "model": "mistral",
  "prompt": "Why is Tracer good in Overwatch?",
  "stream": false
}'
```

### Test in your app:
```bash
# 1. Set environment
export OLLAMA_MODEL=mistral
export DEBUG=true

# 2. Start backend
cd backend
python -m uvicorn main:app --reload

# 3. Send a query
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are Tracer abilities?",
    "session_id": "test-session"
  }'
```

Look for `[Using Ollama (mistral)]` in the response if DEBUG=true.

---

## .env.local Example

```bash
# Use Ollama (LOCAL)
OLLAMA_MODEL=mistral

# Or use OpenAI (PAID)
# OPENAI_API_KEY=sk-...

# Or use Hugging Face (FREE TIER)
# HF_TOKEN=hf_...

# Debugging
DEBUG=false
```

---

## Performance Expectations

### Ollama (Local)
- First response: 5-15 seconds (model loading)
- Subsequent: 2-5 seconds per response
- Quality: Good (7B models) to Excellent (13B+)

### OpenAI
- Response time: 1-3 seconds
- Quality: Excellent
- Cost: ~$0.001-$0.003 per response

### Hugging Face
- Response time: 5-30 seconds (depends on queue)
- Quality: Good to Excellent
- Cost: Free (limited)

---

## Recommended Setup for Development

1. **Start with Ollama** (free, local, privacy)
   - Pull `mistral` for speed or `zephyr` for quality
   - Zero cost, works offline

2. **Keep OpenAI as fallback** (paid backup)
   - Add API key to `.env` for when you want better quality
   - Automatically used if Ollama fails

3. **Test both** before going to production
   - Compare response quality
   - Compare response times
   - Check costs (OpenAI)

---

## Troubleshooting

### "Ollama connection refused"
```bash
# Make sure Ollama server is running
ollama serve

# Check it's accessible
curl http://localhost:11434/api/tags
```

### "Model not found"
```bash
# List available models
ollama list

# Pull the model
ollama pull mistral
```

### "OPENAI_API_KEY not set" (but I want to use Ollama)
```bash
# Make sure OLLAMA_MODEL is exported
export OLLAMA_MODEL=mistral

# And Ollama server is running
ollama serve
```

### "Slow responses"
- Local: Use smaller model (mistral instead of llama2)
- Cloud: OpenAI is fastest option

### "Poor quality responses"
- Switch to better model: `zephyr` or `neural-chat`
- Or use OpenAI (better but costs money)

---

## Next Steps

1. **Try Ollama first:**
   ```bash
   ollama pull mistral
   export OLLAMA_MODEL=mistral
   # Run your app
   ```

2. **Add OpenAI as fallback** (optional)
   ```bash
   export OPENAI_API_KEY=sk-...
   ```

3. **Test in your app:**
   ```bash
   # Query endpoint and check which model was used
   ```

4. **Adjust as needed:**
   - Need faster? Switch to OpenAI
   - Need cheaper? Stick with Ollama
   - Need better quality? Use zephyr or OpenAI
