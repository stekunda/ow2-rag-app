# Running the App with Docker + Local Ollama

You can run the entire app (backend, frontend, Chroma) in Docker while using your local Ollama LLM on the host machine.

## Quick Start

### 1. Start Ollama on your host machine

```bash
# Terminal 1: Start Ollama server
ollama serve

# In another terminal, pull a model
ollama pull mistral
```

### 2. Configure the app

```bash
# In project root, ensure .env.local has:
export OLLAMA_MODEL=mistral
```

### 3. Run Docker Compose

```bash
# Terminal 2: Start all services in Docker
docker-compose up --build

# Services:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - Chroma DB: http://localhost:8001
```

That's it! The Docker containers can now reach your local Ollama via `host.docker.internal:11434`.

---

## How It Works

### Network Configuration

On **macOS & Windows**, Docker Desktop provides a special DNS name `host.docker.internal` that resolves to the host machine's IP.

**Updated `docker-compose.yml`:**
```yaml
backend:
  environment:
    OLLAMA_BASE_URL: http://host.docker.internal:11434
  extra_hosts:
    - "host.docker.internal:host-gateway"
```

This allows the backend container to call your local Ollama server.

### Flow

```
User Request (Frontend)
    ↓
Backend Container (port 8000)
    ↓ (queries)
Chroma Container (port 8001)
    ↓ (retrieves chunks)
Backend Container
    ↓ (calls)
Ollama on Host Machine (port 11434)
    ↓ (generates answer)
Response back to Frontend
```

---

## Linux Users

If you're on **Linux**, `host.docker.internal` doesn't work by default. Use this instead:

```bash
# Get your host IP
HOST_IP=$(hostname -I | awk '{print $1}')

# Run with environment variable
docker-compose -e OLLAMA_BASE_URL=http://$HOST_IP:11434 up

# Or hardcode in .env:
OLLAMA_BASE_URL=http://192.168.1.100:11434  # Your host IP
```

---

## Troubleshooting

### "Cannot connect to Ollama"

1. **Check Ollama is running:**
   ```bash
   curl http://localhost:11434/api/tags
   ```
   Should see your models listed.

2. **Check container can reach host:**
   ```bash
   # From inside container
   docker exec ow2-rag-app-backend-1 curl http://host.docker.internal:11434/api/tags
   ```

3. **Check firewall:**
   - macOS: System Preferences → Security & Privacy
   - Make sure Docker/Ollama aren't blocked

### "Model not found"

```bash
# Make sure model is pulled on host
ollama list
ollama pull mistral
```

### "Slow responses from Docker"

Docker adds ~100-200ms latency. If too slow:
- Run backend natively instead: `python -m uvicorn backend.main:app`
- Keep Docker for frontend + Chroma only

---

## Configuration Options

### Use Docker Ollama instead of host Ollama

Add Ollama as a service in docker-compose.yml:

```yaml
ollama:
  image: ollama/ollama:latest
  ports:
    - "11434:11434"
  volumes:
    - ollama-data:/root/.ollama
  environment:
    OLLAMA_HOST: 0.0.0.0:11434

backend:
  environment:
    OLLAMA_BASE_URL: http://ollama:11434
  depends_on:
    - ollama

volumes:
  ollama-data:
```

Then:
```bash
docker-compose up --build
# Ollama is now a container too
```

### Use OpenAI instead

```bash
# Set in .env
export OPENAI_API_KEY=sk-...

# The backend will automatically use OpenAI if OLLAMA_MODEL not set
docker-compose up --build
```

---

## Full Docker Setup Checklist

- [ ] Ollama installed and running on host (`ollama serve`)
- [ ] Model pulled (`ollama pull mistral`)
- [ ] `.env.local` has `OLLAMA_MODEL=mistral`
- [ ] `docker-compose.yml` updated with `host.docker.internal` config
- [ ] `docker-compose up --build` runs successfully
- [ ] Test: `curl http://localhost:8000/health` returns `{"status": "ok"}`
- [ ] Test: `curl http://localhost:3000` shows frontend
- [ ] Test: Chat works and shows responses

---

## Performance Tips

1. **Ollama runs faster natively than in Docker**
   - Host: 2-5 sec response time
   - Docker: 2-5 sec + network overhead

2. **Keep Ollama on host, Docker for services**
   - This is the recommended setup
   - Best of both worlds

3. **For production**: Use cloud LLM (OpenAI) or Docker Ollama
   - Simpler to deploy
   - No host dependency

---

## Useful Commands

```bash
# Start services
docker-compose up --build

# Rebuild specific service
docker-compose build backend
docker-compose up backend

# View logs
docker-compose logs -f backend
docker-compose logs -f chroma

# Stop services
docker-compose down

# Clean everything
docker-compose down -v  # Includes volumes
```

---

## If Something Goes Wrong

### Check container can reach Ollama:
```bash
docker exec ow2-rag-app-backend-1 curl -v http://host.docker.internal:11434/api/tags
```

### Check Ollama server is responding:
```bash
curl -v http://localhost:11434/api/tags
```

### Restart everything:
```bash
docker-compose down
docker-compose up --build
```

### Check backend logs:
```bash
docker-compose logs -f backend | grep -i ollama
```

---

## Summary

✅ **Supported:**
- Local Ollama on host + Docker backend/frontend/chroma
- Docker Ollama container (optional)
- OpenAI fallback

✅ **Recommended for development:**
- Ollama running on host
- Backend/Frontend/Chroma in Docker
- Fast iteration, no rebuilds needed for Ollama

✅ **Recommended for production:**
- Everything in Docker
- Or use cloud LLM (OpenAI)
- Single `docker-compose up` deploys everything
