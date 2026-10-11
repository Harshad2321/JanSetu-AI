# JANSETU AI — Adaptive Civic Incident Resolution
### Multi-Agent Civic Triage, Planning, and Adaptive Recovery Platform

JanSetu AI is an autonomous, agentic civic-technology operations system designed for municipal command centers. It ingests citizen complaints with optional photographs and GPS snapshots, sanitizes uploads to protect reporter privacy, coordinates a six-agent LangGraph orchestration mesh, and executes adaptive recovery workflows under field resource constraints.

---

## 1. System Architecture & Dual-Interface Model

The primary platform consists of three integrated layers:

```
                  ┌────────────────────────────────────────┐
                  │       Shared FastAPI REST Backend      │
                  │   LangGraph 6-Agent Mesh + SQLite WAL  │
                  └───────────────────┬────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
┌───────────────────────────┐                   ┌───────────────────────────┐
│ Primary React Application │                   │   Streamlit Companion     │
│   (Production Command     │                   │     (CA-3 Compliance      │
│         Center)           │                   │        PoC Client)        │
│                           │                   │                           │
│ - Vite + React 19 + TS    │                   │ - Streamlit Python Client │
│ - Midnight Navy Theme     │                   │ - Operations Dashboard    │
│ - Recharts Analytics      │                   │ - Citizen Intake Form     │
│ - Leaflet OpenStreetMap   │                   │ - Multi-Agent Inspector   │
│ - @xyflow/react Mesh      │                   │ - Deterministic Sim Lab   │
│ - Simulation Lab & Audit  │                   │ - Audit Trail & Provenance│
└───────────────────────────┘                   └───────────────────────────┘
```

Both user interfaces act strictly as REST clients of the same FastAPI backend (`http://localhost:8000`). **Neither frontend duplicates backend agent logic, priority algorithms, Critic validation rules, or the deterministic closure gate.**

---

## 2. Six-Agent Orchestration Mesh

1. **Incident Intelligence Agent:** Evaluates citizen reports and optional photos. Ingests images through an EXIF-stripping sanitization pipeline and performs multimodal triage via Groq Vision (`qwen/qwen3.8-27b`) or deterministic fallback.
2. **GeoCivic Agent:** Performs geospatial duplicate detection using the Haversine spherical formula (< 50m radius) against historical and active incident registries. Executes concurrently with Priority Intelligence.
3. **Priority Intelligence Agent:** Calculates explainable 0–100 priority scores weighting hazard severity, pedestrian exposure, arterial transit flags, and duplicate penalties. Executes concurrently with GeoCivic.
4. **Resolution Planning Agent:** Merges outputs from both parallel branches into bifurcated remediation plans: immediate temporary mitigation, permanent engineering repairs, resource allocations, and measurable closure criteria.
5. **Critic and Verification Gatekeeper:** Evaluates plan feasibility, municipal safety protocols, and resource constraints with bounded replanning retries (maximum 2 retries before supervisor escalation).
6. **Adaptive Recovery Agent:** Responds dynamically to simulation obstacles (crew shortages, material deficits) by substituting resources and resubmitting revised plans to the Critic.
7. **Deterministic Closure Gate:** Strictly controls transitions to `SIMULATED_RESOLVED`. Never allows LLM outputs or matched photos alone to close an incident without verified post-intervention evidence.

---

## 3. Local Setup & Quickstart

### Step 1: Environment & Virtual Environment
Ensure Python 3.11+ and Node.js 18+ are installed.

```bash
# Clone repository
git clone https://github.com/Harshad2321/JanSetu-AI.git
cd JanSetu-AI

# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install backend & Streamlit dependencies
pip install -r backend/requirements.txt
```

### Step 2: Start the FastAPI Backend
```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Base URL: `http://127.0.0.1:8000`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`
- Health Probe: `http://127.0.0.1:8000/health`

### Step 3: Run the Primary React Application (Primary Product)
```bash
cd frontend
npm install
npm run dev
```
- Opens at: `http://localhost:5173` (or `http://localhost:5174`)
- Connects to FastAPI via `VITE_API_BASE_URL` (defaults to `http://localhost:8000`).

### Step 4: Run the Streamlit Companion (CA-3 Compliance Deliverable)
```bash
# From workspace root with .venv activated:
streamlit run streamlit_app/app.py --server.port 8501
```
- Opens at: `http://localhost:8501`
- Connects to FastAPI via `FASTAPI_BASE_URL` or `API_BASE_URL` (defaults to `http://localhost:8000`).

---

## 4. Deterministic Simulation Scenarios

The platform includes 6 deterministic demonstration scenarios:

| Scenario ID | Injected Obstacle | Agent System Behavior | Final Outcome |
|---|---|---|---|
| `normal` | None | Standard repair execution with synthetic closure evidence | `SIMULATED_RESOLVED` |
| `crew_unavailable` | Municipal road crew unavailable | Adaptive Recovery engages standby private contractor | `CLOSURE_BLOCKED` / Revised Plan |
| `materials_unavailable` | Hot-mix asphalt deficit | Adaptive Recovery substitutes heavy steel trench plates | `CLOSURE_BLOCKED` / Revised Plan |
| `critic_rejection` | Safety violation injected | Critic rejects plan; planner regenerates compliant plan | Replanned / Bounded Retry |
| `insufficient_closure_evidence` | No post-repair photo | Deterministic closure gate blocks resolution | `CLOSURE_BLOCKED` |
| `retry_exhaustion` | 3+ consecutive failures | Bounded retry cap reached; auto-escalated to Supervisor | `ESCALATED` |

---

## 5. Verification & Testing

### Running the Backend & Cross-Application Test Suite
```bash
cd backend
pytest tests -v
```
- **116 / 116 Tests Passing** across schemas, image sanitization, storage abstraction, PostgreSQL/SQLite engine pooling, Groq Vision integration, LangGraph orchestrator, REST APIs, production security guards, and cross-application integration contracts.
- Tests execute with zero network requirements and zero Groq API token consumption.

### Running the Frontend Build & Linter
```bash
cd frontend
npm run build   # TypeScript type checks (tsc -b) and Vite bundle (0 errors)
npm run lint    # oxlint verification (0 errors)
```

---

## 6. Cloud Deployment Architecture (Production Ready)

JanSetu AI is pre-configured and verified for cloud deployment without code modifications:

| Component | Target Hosting Platform | Deployment Configuration |
| :--- | :--- | :--- |
| **Frontend SPA** | **Vercel** | `frontend/vercel.json` with SPA routing rewrites and asset caching |
| **Backend API** | **Render** | `render.yaml` Blueprint, `backend/.python-version` (3.11.9), dynamic `$PORT` binding |
| **Persistent DB** | **Supabase PostgreSQL** | Transaction Pooler (Port 6543) via `psycopg2-binary`, connection pooling, Alembic migration |
| **Private Photos** | **Supabase Storage** | Private bucket (`jansetu-evidence`), backend-mediated 15-minute signed URLs |
| **Companion UI** | **Streamlit Community Cloud** | Dedicated `streamlit_app/requirements.txt`, secret management via `st.secrets` |
| **Multimodal LLM**| **Groq Cloud** | Server-side only via `GROQ_API_KEY` (never exposed to frontend clients) |

For complete, dashboard-by-dashboard deployment steps, environment variable tables, and security guidelines, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

---

## 7. Responsible Data & Simulation Disclaimers

> [!IMPORTANT]
> **Demonstration & Synthetic Scope:** All incident reports, work orders, contractor dispatches, resource estimates, and intervention closures in this demonstration are synthetic or simulated. No real municipal repair crews are dispatched. An incident marked `SIMULATED_RESOLVED` explicitly designates a validated synthetic simulation outcome, never an unqualified claim of real-world physical road repair.
