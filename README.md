# Agentic Contract Intelligence System

Minimal local MVP: upload PDF/DOCX, extract structured data with **Groq** LLM, generate tasks and risks, monitor deadlines with **APScheduler**, optional **ChromaDB** RAG, and a **React** dashboard.

## Project structure

```
Khushi/
├── Agentic_Project_Overview.docx
├── README.md
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── requirements-chroma.txt   # optional ChromaDB
│   └── app/
│       ├── main.py              # FastAPI routes, scheduler lifecycle
│       ├── config.py            # Settings (GROQ_API_KEY, paths)
│       ├── database.py          # SQLite + SQLAlchemy
│       ├── models.py            # Contract, Task, Risk, Alert
│       ├── schemas.py           # Pydantic response models
│       └── services/
│           ├── document_service.py   # PDF/DOCX text extraction
│           ├── groq_llm.py           # Groq client + JSON parsing
│           ├── pipeline.py           # Parse → Plan → Risk + RAG helpers
│           ├── chroma_rag.py         # Chroma indexing & query
│           └── monitor_service.py    # Deadline sweep → alerts
└── frontend/
    ├── package.json
    ├── vite.config.js         # Dev proxy /api → backend
    └── src/
        ├── App.jsx            # Dashboard UI
        └── ...
```

## Prerequisites

- Python 3.10+
- Node.js 18+ (for the React UI)
- A [Groq](https://console.groq.com/) API key (free tier)

If the project folder is under **OneDrive**, Python sometimes hits file locks while installing into `.venv`. Retry `pip install`, or move the project to a non-synced folder (for example `C:\dev\Khushi`).

## Backend setup

### Option 1: Using Startup Scripts (Recommended)

**Windows (Batch):**
```powershell
cd backend
./run.bat
```

**Windows (PowerShell):**
```powershell
cd backend
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\run.ps1
```

Both scripts will:
- ✓ Activate the virtual environment
- ✓ Create `.env` from template if missing
- ✓ Create required data directories
- ✓ Start the server with proper configuration

### Option 2: Manual Setup

1. Open a terminal and navigate to backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Create `.env` (copy from `.env.example`):

```env
GROQ_API_KEY=gsk_your_key_here
```

3. Run the API (from the `backend` folder):

```powershell
# IMPORTANT: Use --no-reload to avoid Windows subprocess issues
uvicorn app.main:app --no-reload --host 127.0.0.1 --port 8000
```

**Note:** Always use `--no-reload` flag on Windows. The reload feature spawns subprocesses that don't properly inherit the venv environment on Windows systems.

- SQLite file: `backend/data/contracts.db`
- Uploads: `backend/data/uploads`
- Chunk store: SQLite table `contract_chunks` (always used for RAG fallback)
- Optional Chroma: `backend/data/chroma` if you `pip install -r requirements-chroma.txt` (may require [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) on Windows)

## Frontend setup

```powershell
cd "c:\Users\Sunoy Roy\OneDrive\Desktop\Khushi\frontend"
npm install
npm run dev
```

Open `http://localhost:5173`. The UI calls the API via Vite proxy (`/api` → `http://127.0.0.1:8000`).

## API overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness + whether Groq key is set |
| POST | `/upload` | Multipart file upload; runs full LLM pipeline |
| GET | `/dashboard` | Aggregated stats, risk histogram, contracts, alerts |
| GET | `/contracts/{id}` | Contract detail, tasks, risks, alerts, parsed JSON |
| POST | `/contracts/{id}/query` | RAG question (`{"question":"..."}`) |
| POST | `/monitor/run` | Run deadline sweep once |
| POST | `/alerts/{id}/draft-email` | LLM email draft for an alert |
| POST | `/tasks/{id}/resolve` | Mark task done; resolve linked alerts |
| POST | `/alerts/{id}/resolve` | Dismiss an alert |

## Sample requests (curl)

Replace `path\to\file.pdf` with a real path.

```powershell
# Health
curl http://127.0.0.1:8000/health

# Upload
curl -X POST http://127.0.0.1:8000/upload -F "file=@path\to\contract.pdf"

# Dashboard
curl http://127.0.0.1:8000/dashboard

# Contract detail (id 1)
curl http://127.0.0.1:8000/contracts/1

# RAG query
curl -X POST http://127.0.0.1:8000/contracts/1/query -H "Content-Type: application/json" -d "{\"question\":\"What are the payment terms?\"}"

# Force monitor sweep
curl -X POST http://127.0.0.1:8000/monitor/run
```

## LLM pipeline (lightweight)

1. **Parsing** — structured JSON: parties, dates, payment, penalties, SLA, termination, obligations.
2. **Planning** — tasks with `task_name`, `due_date`, `priority`.
3. **Risk** — risk items + `overall_risk_score` (0–100).
4. **Monitoring** — APScheduler + `monitor_service.sweep_deadlines` for upcoming/overdue tasks.
5. **Action** — `draft-email` uses an LLM pass to produce subject/body.

Prompts live in `backend/app/services/pipeline.py` (`SYSTEM_PARSE`, `SYSTEM_PLAN`, `SYSTEM_RISK`, `SYSTEM_ACTION`).

## Optional model override

In `.env`:

```env
GROQ_MODEL=llama-3.3-70b-versatile
```

Use a model your Groq account supports; JSON mode is used when available.

## Notes

- **ChromaDB** is optional. By default, RAG uses SQLite-stored chunks plus keyword overlap (no extra install). Install `requirements-chroma.txt` for embedding-based semantic search when your environment can build or fetch native wheels.
- If Chroma is installed, first use may download a small embedding model.
- Very long documents are truncated before LLM calls (see `MAX_CHARS` in `pipeline.py`).
- The overview document envisioned Ollama/LangChain; this repo follows your Groq + simple pipeline spec instead.
