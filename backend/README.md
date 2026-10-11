# JanSetu AI — Backend Architecture & REST API Documentation

JanSetu AI is an adaptive, multi-agent civic incident resolution and evidence verification engine built with **FastAPI**, **LangGraph**, and **Pydantic**.

---

## 1. Architecture Overview

JanSetu AI coordinates six specialized agents through an asynchronous LangGraph workflow:

1. **Incident Intelligence Agent:** Ingests citizen reports, sanitizes attached photographs via Pillow (stripping all EXIF and GPS tags), downscales dimensions safely, and extracts structured incident facts with multimodal verification.
2. **GeoCivic Agent:** Performs geospatial duplicate detection against historical and synthetic municipal incidents using the Haversine formula (< 50m threshold). Executes concurrently with Priority Intelligence.
3. **Priority Intelligence Agent:** Calculates transparent, explainable hazard scores (0–100) and priority tiers based on hazard severity and public exposure. Executes concurrently with GeoCivic.
4. **Resolution Planning Agent:** Synthesizes outputs from both parallel branches into actionable remediation plans with immediate mitigation, permanent repairs, resource allocations, and measurable closure criteria.
5. **Critic and Verification Agent:** Evaluates plan feasibility, safety constraints, and criteria completeness with bounded retries (maximum 2 replanning attempts before supervisor escalation).
6. **Adaptive Recovery Agent:** Responds to deterministic simulation obstacles (e.g., crew shortages, material deficits, utility conflicts) by proposing materially distinct alternatives and rerouting back through the Critic gate.
7. **Deterministic Closure Gate:** Strictly controls state transitions to `SIMULATED_RESOLVED`. Never allows LLM output, matched photos, or successful function executions alone to resolve an incident without verified synthetic completion evidence.

---

## 2. Configuration & Environment Variables

All settings are managed via `app.config.Settings` with `.env` file support:

| Variable | Default Value | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | Runtime mode (`development`, `production`). |
| `DATABASE_URL` | `sqlite:///./data/jansetu.db` | SQLAlchemy connection URI for incident records and telemetry. |
| `STORAGE_DIR` | `./data/uploads` | Local private directory for storing sanitized photographs (not exposed via static URLs). |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000` | Comma-separated allowed origins for the React frontend. |
| `GROQ_API_KEY` | `None` | Optional Groq API key for vision analysis (`qwen/qwen3.8-27b`). |
| `GROQ_MODEL` | `qwen/qwen3.8-27b` | Multimodal vision model identifier. |

> [!NOTE]
> Local SQLite storage is configured for the PoC. For production deployments with ephemeral containers, configure `DATABASE_URL` to point to a persistent managed database (PostgreSQL/Cloud SQL) and `STORAGE_DIR` to a secure bucket (S3/GCS).

---

## 3. Database Persistence

- **Persistence Engine:** SQLAlchemy with SQLite (`sqlite:///./data/jansetu.db`).
- **Safety Guarantee:** Database initialization (`init_db()`) is idempotent and non-destructive—existing tables and historical civic records are never wiped or dropped on server startup.
- **Explicit Demo Seeding:** Demonstration incidents (`INC-DEMO-01` through `04`) are seeded only via explicit administrative triggers (`POST /api/v1/incidents/seed`), never automatically on boot.

---

## 4. REST API Endpoints

### Health & Aggregates
- `GET /health` or `GET /api/v1/health`: Health status and service environment without credential exposure.
- `GET /api/v1/dashboard/summary`: Incident metrics, operational status counts, evidence outcomes, categories, and priority bands.

### Incident Management
- `GET /api/v1/incidents`: List incidents with optional filtering (`status`, `category`, `evidence_status`, `limit`, `offset`).
- `POST /api/v1/incidents`: Submit a new citizen incident report. Accepts both:
  - `multipart/form-data`: `complaint`, `category`, `latitude`, `longitude`, `accuracy_meters`, `location_source`, `address_text`, `is_user_confirmed`, and binary `image`.
  - `application/json`: Standard JSON payload with optional `image_base64`.
- `GET /api/v1/incidents/{incident_id}`: Retrieve detailed incident record, current operational status, evidence outcome, and resolution plan.

### Workflow Execution & Telemetry
- `POST /api/v1/incidents/{incident_id}/run`: Execute the multi-agent LangGraph workflow for an incident. Accepts optional scenario parameters (`simulation_scenario`, `failure_reason`).
- `GET /api/v1/incidents/{incident_id}/trace`: Retrieve execution traces for specialist agents.
- `GET /api/v1/incidents/{incident_id}/audit`: Retrieve full chronological audit timeline events.

### Simulation Lab Scenarios
- `POST /api/v1/incidents/{incident_id}/simulate`: Run a deterministic simulation scenario for demonstration:
  - `normal`: Simulates successful intervention and passes verified completion evidence to the closure gate (`SIMULATED_RESOLVED`).
  - `crew_unavailable`: Simulates field crew shortage, invoking Adaptive Recovery to dispatch standby contractors.
  - `materials_unavailable`: Simulates asphalt deficit, invoking Adaptive Recovery to substitute steel trench plates.
  - `critic_rejection`: Injects a Critic safety violation triggering bounded replanning.
  - `insufficient_closure_evidence`: Simulates physical work without required completion evidence, transitioning to `CLOSURE_BLOCKED`.
  - `retry_exhaustion`: Simulates repeated unrecoverable failures, triggering supervisor escalation (`ESCALATED`).

---

## 5. Local Setup & Launch

### Prerequisites
- Python 3.11+
- Virtual environment with dependencies installed:

```bash
cd backend
python -m pip install -r requirements.txt
```

### Running the API Server
Launch the FastAPI development server with automatic reload:

```bash
python run.py
```
Or directly with Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The interactive OpenAPI documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 6. Running the Test Suite

Execute all 86 unit, integration, and orchestration tests:

```bash
pytest tests -v
```

All external model calls and database operations are mocked/isolated using temporary in-memory or on-disk SQLite files. Running the test suite consumes zero Groq API credits.
