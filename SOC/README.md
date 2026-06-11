# SOC — AI Agent Bridge

## Quick Start

### 1. Start the SOC backend
```bash
cd backend
pip install flask flask-socketio flask-cors eventlet
python app.py
```
Dashboard → http://localhost:5000

---

### 2. Start Ollama + pull model
```bash
# Install Ollama from https://ollama.com
ollama serve
ollama pull llama3.2
```

---

### 3. Run the AI agent
```bash
pip install requests
python agent.py
```

Commands inside the agent:
| Command | What it does |
|---------|-------------|
| `run`    | Fetch pending logs from SOC and analyze them |
| `status` | Show current config |
| `quit`   | Exit |

---

## Full Flow

```
1. You send a log      →  POST http://localhost:5000/api/ingest
2. You type "run"      →  Agent fetches logs from /api/agent/pending-logs
3. llama3.2 analyzes   →  Agent posts decision to /api/agent/decision
4. Modal appears       →  On the SOC dashboard
5. You approve/reject  →  Your ACTION HOOK fires in backend/app.py
```

---

## Send a test log (curl)
```bash
curl -X POST http://localhost:5000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source": "firewall",
    "severity": "high",
    "message": "Multiple failed SSH login attempts from 192.168.1.100",
    "raw": {
      "src_ip": "192.168.1.100",
      "attempts": 47,
      "target": "ssh",
      "port": 22
    }
  }'
```

Then type `run` in the agent — decision appears on the dashboard.

---

## Config (top of agent.py)
| Variable | Default | Description |
|----------|---------|-------------|
| `SOC_BASE_URL` | `http://localhost:5000` | SOC backend address |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama address |
| `MODEL` | `llama3.2` | Ollama model name |
| `MAX_LOGS_BATCH` | `20` | Max logs per run |
# Digi-graduation-soc
