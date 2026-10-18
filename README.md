# JANSETU AI — Adaptive Civic Incident Resolution Platform
### Multi-Agent Civic Triage, Response Planning, Adaptive Recovery, and Independent Verification

**Academic Evaluation Context:** Final Project Deliverable  
**System Invariants Compliance:** 11/11 Verified (100%)  
**Backend Automated Tests:** 194 Passed, 1 Skipped (Live Groq rate-limit guard), 0 Failures  
**Frontend Quality Gate:** Production TypeScript Build: 0 Errors | Linter: 0 Errors  

---

## Executive Overview & Problem Statement

Municipal command centers in developing urban centers struggle with fragmented citizen reporting, uncoordinated inter-departmental dispatch, duplicate complaint flooding, and a complete lack of closed-loop verification. Complaints submitted through public portals often languish because intake systems cannot triage severity, prioritize life-safety hazards, adapt when municipal contractors fail, or objectively verify that repairs were actually completed.

**JanSetu AI** addresses these challenges through a modular, autonomous multi-agent architecture built on **FastAPI**, **LangGraph**, and **React 19 / TypeScript**. The platform models municipal operations through a persistent **Civic Incident Twin**, coordinates **six specialist agents** and an independent **Critic**, executes adaptive recovery workflows under field constraints, and enforces an unbypassable, deterministic **Closure Gate** requiring independent structural verification before any incident can be closed.

> [!TIP]
> 📖 **Deep Technical & Operational Documentation:**  
> For the complete end-to-end technical manual detailing every agent contract, mathematical formula, state machine transition matrix, ML fusion truth table, database schema, and live demo script, see **[JANSETU_SYSTEM_WORKFLOW_AND_TECHNICAL_MANUAL.md](JANSETU_SYSTEM_WORKFLOW_AND_TECHNICAL_MANUAL.md)**.

> [!IMPORTANT]
> **Academic Scope & Simulation Boundary:**  
> JanSetu AI is an educational, prototype-grade multi-agent proof of concept. All work orders, contractor dispatches, resource substitutions, and execution attempts are executed within a software simulation environment (`simulated=True`). No physical municipal crews are dispatched, and the terminal state `VERIFIED_CLOSED` denotes a validated simulation outcome rather than a physical road repair. For full details on academic boundaries, see [docs/limitations.md](docs/limitations.md).

---

## 1. System Architecture

JanSetu AI is structured into clean, decoupled layers:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 PRESENTATION LAYER                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │   Primary React Web Application (Production SPA)                                 │  │
│  │   - Vite 8 + React 19 + TypeScript + Tailwind CSS                                │  │
│  │   - Incident Intake & EXIF Sanitization                                          │  │
│  │   - Multi-Agent Step-by-Step Inspector & Critic Review                           │  │
│  │   - Interactive Agent Graph (@xyflow/react)                                      │  │
│  │   - Geographic Leaflet Map & Filters                                             │  │
│  │   - Simulation Lab & Human Review Console                                        │  │
│  │   - ML Model Lab (Interactive Inference & Metrics)                               │  │
│  │   - Immutable System Audit Trail & CSV/JSON Export                               │  │
│  └────────────────────────────────────────┬─────────────────────────────────────────┘  │
└───────────────────────────────────────────┼────────────────────────────────────────────┘
                                            │ HTTP REST APIs
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI BACKEND & ORCHESTRATION                           │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │   LangGraph Multi-Agent Mesh & State Machine (15 Discrete States)                │  │
│  │                                                                                  │  │
│  │   Parallel Branch 1:                     Parallel Branch 2:                      │  │
│  │   [Agent 1: Incident Intelligence]       [Agent 2: GeoCivic Duplicate Detector]  │  │
│  │     • TF-IDF Classifier (4 Languages)      • Haversine Spatial Radius (<50m)     │  │
│  │     • Groq Vision / Ollama VLM             • Unconfirmed Candidate Preservation  │  │
│  │     • Multimodal Disagreement Resolver   [Agent 3: Priority & Risk Intelligence] │  │
│  │                                            • 0–100 Explainable Priority Score    │  │
│  │                                            • Mandatory Life-Safety Escalation    │  │
│  │                                                                                  │  │
│  │   Converged Response & Planning:                                                 │  │
│  │   [Agent 4: Response Planning Agent]                                             │  │
│  │     • Bifurcated Remediation (Immediate Temporary + Permanent Engineering)       │  │
│  │     • Resource Requirements & Measurable Closure Criteria                        │  │
│  │   [The Critic (Independent Validator)]                                           │  │
│  │     • Municipal Feasibility & Safety Clearance Checks                            │  │
│  │                                                                                  │  │
│  │   Closed-Loop Simulation & Governance:                                           │  │
│  │   [Execution Simulator (app.simulation.simulator)]                               │  │
│  │     • Injected Failures: Crew Deficit, Material Shortage, Weather Block          │  │
│  │   [Agent 5: Adaptive Recovery Agent]                                             │  │
│  │     • Authorized Resource Substitution & Versioned Replanning (Max 2 Retries)    │  │
│  │   [Agent 6: Independent Verification Agent & Closure Gate]                       │  │
│  │     • Post-Intervention Evidence Verification & Mandatory Supervisor Sign-off    │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
┌──────────────────────────────────────────▼─────────────────────────────────────────────┐
│                               DATA & PERSISTENCE LAYER                                 │
│  - Relational Civic Incident Twin (SQLite WAL via SQLAlchemy 2.0 ORM)                  │
│  - Immutable, Append-Only Audit Trail (All state transitions and agent decisions)      │
│  - Plan History Repository & Versioned Execution Attempts (`simulated=True`)           │
│  - Pre-trained ML Artifacts (`data/nlp_model.joblib`) & Geospatial Coordinate Registry │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### The Six Specialist Agents & The Critic

| Agent Component | Core Responsibilities | Key Invariant / Guardrail |
|---|---|---|
| **1. Incident Intelligence** | Multimodal intake; strips EXIF metadata; classifies category across 4 languages (English, Hindi, Marathi, Hinglish); invokes Groq Qwen-2.5-VL / Ollama. | **WF-1**: If NLP and Vision disagree, routes to `DISAGREEMENT` with clarification prompts rather than guessing. |
| **2. Geo-Spatial Intelligence** | Computes Haversine distance (<50m) against active incidents; assesses terrain and transit corridor exposure. | **INV-7**: Nearby matches flagged as `UNCONFIRMED` candidates; zero automatic merging without human dispatcher review. |
| **3. Risk & Priority** | Calculates explainable 0–100 priority score from category baseline, duration, vulnerability, and exposure. | **INV-3**: Direct life-safety triggers (`E01_LIFE_SAFETY`, `E04_VULNERABLE_POPULATION`) instantly force `CRITICAL` priority. |
| **4. Response Planning** | Generates bifurcated remediation plan: Phase 1 Immediate Mitigation (barricading, trench plates) and Phase 2 Permanent Repair (asphalt resurfacing). | Specifies required municipal resources, safety certifications, and objective closure criteria. |
| **Critic (Validator)** | Independently assesses proposed plans against municipal safety codes, material availability, and resource constraints. | Rejects non-compliant plans back to the planner with explicit rejection feedback (bounded replanning). |
| **5. Adaptive Recovery** | Intercepts execution failures (crew shortage, material deficit, weather delays); substitutes certified alternatives. | **INV-4 & INV-6**: Rejects uncertified alternatives; limits autonomous replanning to 2 retries before escalating to `HUMAN_REVIEW`. |
| **6. Independent Verification** | Inspects post-repair photographic evidence, work orders, and field clearance before permitting closure. | **INV-1 & WF-2**: Strictly prevents transition to `VERIFIED_CLOSED` unless `VerificationResult(passed=True)` and supervisor sign-off exist. |

---

## 2. Directory Structure

The repository is organized cleanly with zero redundant, abandoned, or demo-script files:

```
JanSetu AI/
├── backend/                        # FastAPI REST Application & Core AI Engine
│   ├── app/
│   │   ├── agents/                 # 6 Specialist Agents + Critic Validator
│   │   │   ├── incident_intelligence.py   # Agent 1 (Multimodal NLP + Vision)
│   │   │   ├── geospatial.py              # Agent 2 (Haversine Deduplication)
│   │   │   ├── priority.py                # Agent 3 (Heuristic Risk Scoring)
│   │   │   ├── response_planning.py       # Agent 4 (Dual Remediation Plans)
│   │   │   ├── critic.py                  # The Critic (Safety Gatekeeper)
│   │   │   ├── adaptive_recovery.py       # Agent 5 (Failure Diagnosis & Substitution)
│   │   │   └── verification.py            # Agent 6 (Closure Evidence Verifier)
│   │   ├── api/                    # REST API Endpoints (Incidents, Simulation, ML)
│   │   ├── core/                   # Security, Settings, Image EXIF Sanitization
│   │   ├── graph/                  # LangGraph Workflow & 15-State Machine
│   │   │   ├── orchestrator.py            # LangGraph StateGraph Compilation & Node Routing
│   │   │   └── state_machine.py           # Finite State Machine & Validated State Transitions
│   │   ├── ml/                     # Machine Learning Pipeline & Evaluation
│   │   │   ├── classifier.py              # Multilingual TF-IDF + Logistic Classifier
│   │   │   ├── evaluation.py              # Stratified Test & Challenge Set Validator
│   │   │   └── vision_classifier.py       # Groq / Ollama Vision Client
│   │   ├── models/                 # SQLAlchemy 2.0 ORM Database Entities
│   │   ├── repositories/           # Database Repositories (Twin, Plans, Attempts, Audit)
│   │   ├── schemas/                # Pydantic v2 Strong Schemas & Contracts
│   │   ├── simulation/             # Execution Simulator & Injected Obstacles
│   │   └── main.py                 # FastAPI Application Factory & Middleware
│   ├── requirements.txt            # Python Dependencies
│   └── tests/                      # 195 Pytest Unit, Integration, & Contract Tests
├── frontend/                       # Primary React 19 + TypeScript + Vite SPA
│   ├── src/
│   │   ├── components/             # Reusable UI & Operational Views
│   │   │   ├── DashboardView.tsx          # Real-time incident registry & statistics
│   │   │   ├── CitizenSubmissionForm.tsx  # Citizen complaint intake with photo upload
│   │   │   ├── IncidentWorkspaceView.tsx  # Full Civic Twin inspector & audit timeline
│   │   │   ├── AgentCommandCenterView.tsx # Agent step-by-step inspector & Critic review
│   │   │   ├── SystemArchitectureView.tsx # Interactive @xyflow/react graph visualizer
│   │   │   ├── SimulationLabView.tsx      # Failure injection & adaptive recovery lab
│   │   │   ├── IncidentExplorerView.tsx   # Geospatial console, search, & candidate review
│   │   │   ├── MLModelLabView.tsx         # Live ML inference & confusion matrix metrics
│   │   │   └── AuditTimelineView.tsx      # Immutable system audit trail & data export
│   │   ├── services/api.ts         # Centralized Axios REST client
│   │   └── App.tsx                 # View router & layout
│   ├── package.json                # Frontend dependencies (React 19, Lucide, Tailwind, xyflow)
│   └── vite.config.ts              # Code-split production bundle configuration
├── data/                           # Synthetic Datasets & Model Artifacts
│   ├── nlp_model.joblib            # Trained TF-IDF Classifier Artifact
│   ├── synthetic_complaints_300.json      # Stratified Multilingual Dataset (300 samples)
│   └── synthetic_complaints_challenge.json# Disjoint Vocabulary Challenge Dataset (30 samples)
├── docs/                           # Authoritative Academic Documentation
│   ├── architecture.mmd            # Complete Mermaid Architecture Diagram
│   ├── problem_statement.md        # Civic Domain Problem Analysis
│   ├── results_table.md            # Empirical ML & System Invariant Verification Table
│   ├── limitations.md              # Explicit System Limitations & Boundaries
│   ├── future_scope.md             # Prospective Engineering Roadmap
│   ├── ppt_outline.md              # Evaluation & Defense Presentation Outline
│   └── GAP_ANALYSIS.md             # Tracker Gap & Phase Audit Log
├── eval/                           # Invariant Validation & Metric Reports
│   ├── run_validation.py           # Automated 11-Point Invariant & Decision Verifier
│   ├── validation_report.json      # Machine-Readable Invariant Verification Results
│   └── nlp_metrics.json            # Machine-Readable ML Precision/Recall/F1 Results
├── scripts/                        # Utility & Training Scripts
│   └── make_nlp_data.py            # Reproducible Synthetic Dataset Generator (seed=42)
├── JANSETU_TRACKER.md              # Master Multi-Phase Progress & Audit Tracker
└── README.md                       # Master Operating & Inspection Manual (This document)
```

---

## 3. Local Installation & Quickstart

### Prerequisites
- **Python:** Version `3.11` or higher
- **Node.js:** Version `18` or higher (with `npm`)
- **Git**

### Step 1: Clone Repository & Set Up Python Virtual Environment
```bash
# Clone the repository
git clone https://github.com/Harshad2321/JanSetu-AI.git
cd JanSetu-AI

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (CMD):
.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate

# Install backend dependencies
pip install -r backend/requirements.txt
```

### Step 2: Environment Configuration
Create a `.env` file in the project root by copying `.env.example`:
```bash
copy .env.example .env
```
The application runs completely offline without any external API keys using deterministic fallbacks. Optionally, you may supply a Groq API key for live multimodal vision:
```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=qwen/qwen3.8-27b
```

### Step 3: Start the FastAPI Backend
From the repository root (with `.venv` active):
```bash
# Start backend via uvicorn
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```
- **Backend API Base:** `http://127.0.0.1:8000`
- **Interactive Swagger UI (OpenAPI Docs):** `http://127.0.0.1:8000/docs`
- **Health Check Endpoint:** `http://127.0.0.1:8000/health`

### Step 4: Start the Primary React Frontend
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
- **Web Application URL:** `http://localhost:5173`
- The React application connects automatically to `http://127.0.0.1:8000`.

---

## 4. Verification, Tests, & Validation Suite

The project includes automated verification across all engineering tiers. Every test runs locally with zero external network dependencies.

### 1. Full Backend Test Suite
Executes unit tests, agent mock verifications, state-machine transitions, repository operations, API contract validations, and error handling:
```bash
# From project root with .venv active:
pytest backend/tests/ -q
```
**Actual Output:** **194 passed, 1 skipped** (the skipped test is a live Groq API rate-limit test that intentionally skips when no live token is present), **0 failures** in ~31 seconds.

### 2. System Invariant & Decision Validation Suite
The independent validation runner verifies the 11 architectural invariants and workflow decisions defined in `JANSETU_TRACKER.md` (INV-1 through INV-8 and WF-1 through WF-3):
```bash
python eval/run_validation.py
```
**Actual Output:** **11/11 PASSED (100% compliant)**. Generates `eval/validation_report.json` and updates `docs/results_table.md`.

### 3. Machine Learning Reproducibility & Evaluation
Evaluates the multilingual NLP classifier against both the held-out test partition and the disjoint vocabulary challenge set:
```bash
python -m app.ml.evaluation
```
**Actual Output:**
- Held-Out Test Set (60 samples): **100.0% Macro-F1** (zero data leakage detected)
- Challenge Set (30 samples, disjoint vocabulary): **73.33% Macro-F1**
- Output metrics saved to `eval/nlp_metrics.json`.

### 4. Frontend Production Build & Linting
Verifies strict TypeScript typing, JSX validity, and bundle production readiness:
```bash
cd frontend
npm run build   # Compiles TypeScript (tsc -b) and bundles via Vite (0 errors)
npm run lint    # Lints all TypeScript components (0 errors)
```

---

## 5. Comprehensive Professor / Examiner Inspection Guide

JanSetu AI is designed so that an evaluator can inspect, test, and break any component in any order. Follow the walkthroughs below to independently verify each major subsystem.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        EVALUATOR INSPECTION MAP                        │
│                                                                        │
│   [1. Citizen Intake] ───────► [2. Multimodal AI Triage]               │
│          │                                   │                         │
│          ▼                                   ▼                         │
│   [3. Geo Spatial Deduplication]   [4. Risk Scoring & Danger Gate]     │
│          │                                   │                         │
│          └─────────────────┬─────────────────┘                         │
│                            ▼                                           │
│          [5. Response Planning & Critic Clearance]                     │
│                            │                                           │
│                            ▼                                           │
│          [6. Simulation Lab: Injected Obstacles]                       │
│                            │                                           │
│                            ▼                                           │
│          [7. Adaptive Recovery & Bounded Retries]                      │
│                            │                                           │
│                            ▼                                           │
│          [8. Independent Verification & Closure Gate]                  │
│                            │                                           │
│                            ▼                                           │
│          [9. Immutable Audit Trail & Provenance]                       │
└────────────────────────────────────────────────────────────────────────┘
```

### Walkthrough 1: Submit an Original Citizen Incident
1. Open the React frontend at `http://localhost:5173` and click **"New Intake"** in the navigation bar.
2. Enter a realistic civic complaint:
   - *Category:* Pothole / Road Damage
   - *Description:* *"Deep trench across the northbound lane near Sector 4 primary school, exposed rebar causing tire blowouts."*
   - *Location:* Latitude `19.0760`, Longitude `72.8777`
   - *Vulnerability Indicators:* Check *"Near School / Hospital"* and *"Severe Traffic Congestion"*.
3. Click **"Submit Incident Report"**.
4. **Observe:** The incident is assigned a tracking UUID, EXIF metadata is stripped from any attached image, and the incident moves through `INTAKE_PENDING` -> `INCIDENT_ANALYZED` -> `PRIORITIZED` -> `PLAN_PROPOSED` -> `CRITIC_EVALUATED` -> `PLAN_APPROVED`.

### Walkthrough 2: Inspect Multi-Agent Reasoning & The Critic
1. Click **"Agents"** in the top navigation or navigate to an incident and open the **"Agent Reasoning"** tab.
2. Select any submitted incident from the selector dropdown.
3. **Inspect Agent 1 (Incident Intelligence):** Notice the NLP confidence score, extracted primary keywords, and linguistic dialect detection.
4. **Inspect Agent 2 (Geo-Spatial):** Review the 50-meter Haversine radius evaluation and duplicate candidate register.
5. **Inspect Agent 3 (Priority & Risk):** Review the explainable arithmetic calculation breakdown (Base Weight + Hazard Multiplier + Transit Multiplier).
6. **Inspect Agent 4 (Response Planning):** Observe the bifurcated remediation plan showing both **Temporary Mitigation** (e.g., steel trench plates within 4 hours) and **Permanent Repair** (hot-mix asphalt resurfacing within 48 hours).
7. **Inspect The Critic:** Review the safety checklist, feasibility review, and clearance determination.

### Walkthrough 3: Test Life-Safety Priority Escalation (Invariant 3)
1. Go to **"New Intake"** and submit a description containing life-safety hazards:
   - *"Active electrical pole collapsed into flooded water on Main Street with pedestrians nearby."*
2. **Observe:** Regardless of baseline category scoring, the Priority Intelligence Agent triggers `E01_LIFE_SAFETY` and instantly escalates the incident to **CRITICAL** priority band (score 95+), bypassing standard queues.

### Walkthrough 4: Test Geospatial Duplicate Detection (Invariant 7)
1. In **"New Intake"**, submit a pothole report at Coordinates `19.076000`, `72.877700`.
2. Immediately submit a second pothole report at Coordinates `19.076020`, `72.877710` (approx. 3 meters apart).
3. Open the second incident in the **Incident Details** view.
4. **Verify Invariant 7:** The system flags the existing report as a duplicate candidate with status `UNCONFIRMED`. Both records remain distinct; **the system never merges records automatically without explicit human dispatcher confirmation**.

### Walkthrough 5: Injected Failures & Adaptive Recovery in the Simulation Lab
1. Navigate to the **"Simulation Lab"** in the React application.
2. Select an approved incident and choose an injected obstacle:
   - **Scenario: Crew Shortage (`CREW_UNAVAILABLE`)**
     - Click **"Execute Simulation Step"**.
     - **Observe:** The municipal work crew is simulated as absent. The incident transitions to `EXECUTION_FAILED` -> `ADAPTIVE_RECOVERY`.
     - **Adaptive Action:** Agent 5 identifies standby private contractors, generates Plan Version 2, submits it to the Critic, and re-authorizes execution.
   - **Scenario: Retry Exhaustion (Invariant 4)**
     - Inject consecutive failures exceeding `MAX_RECOVERY_RETRIES = 2`.
     - **Observe Invariant 4:** The system halts autonomous replanning and routes the incident to `HUMAN_REVIEW` with an escalation audit notice.

### Walkthrough 6: Independent Verification & The Closure Gate (Invariant 1)
1. In the **Simulation Lab** or **Incident Details**, attempt to mark an incident as `VERIFIED_CLOSED` without providing post-repair evidence.
2. **Observe Invariant 1:** The deterministic Closure Gate rejects the transition with a `TransitionError`.
3. Provide synthetic post-repair photographic evidence but omit the supervisor sign-off for a critical-priority hazard.
4. **Observe:** The Independent Verification Agent rejects closure with `HUMAN_REVIEW_REQUIRED` (missing mandatory supervisor sign-off).
5. Add the supervisor sign-off and valid post-repair evidence:
6. **Observe:** The state transitions cleanly to `VERIFIED_CLOSED`.

### Walkthrough 7: Inspect the Immutable Audit Trail & Provenance
1. Navigate to **"Audit Trail"** in the top navigation.
2. Filter by incident ID or view the full timeline.
3. Every state change, Critic verdict, plan version, simulation attempt, and human intervention is timestamped with actor identity, input snapshot, and transition justification.

### Walkthrough 8: Explore Interactive Architecture Graph
1. Navigate to **"Agent Graph"** in the React application.
2. The interactive node graph powered by `@xyflow/react` displays the live 15-state orchestrator mesh.
3. Click on individual nodes (e.g., `Critic`, `Adaptive Recovery`, `Closure Gate`) to inspect their transition rules and incoming/outgoing guards.

---

## 6. API Reference (FastAPI Backend)

The backend provides complete OpenAPI-documented endpoints accessible at `http://127.0.0.1:8000/docs`:

| HTTP Method | Route | Description |
|---|---|---|
| `GET` | `/health` | Liveness and readiness probe with DB connectivity status |
| `POST` | `/incidents` | Ingests new citizen complaint; sanitizes EXIF; triggers LangGraph triage |
| `GET` | `/incidents` | Queries incident registry with category, status, and priority filters |
| `GET` | `/incidents/{id}` | Fetches full Civic Incident Twin (metadata, plans, attempts, candidates) |
| `GET` | `/incidents/{id}/audit` | Retrieves append-only audit trail and state history for the incident |
| `POST` | `/simulation/step` | Executes a deterministic simulation step with optional injected obstacles |
| `POST` | `/simulation/verify` | Submits post-repair evidence to Agent 6 for closure verification |
| `POST` | `/ml/predict` | Direct REST endpoint for multilingual NLP category classification |
| `GET` | `/ml/metrics` | Returns active ML evaluation metrics and vocabulary leakage reports |

---

## 7. Known Academic Limitations & Operational Boundaries

To maintain academic honesty, the following constraints and boundaries are explicitly acknowledged:

1. **Synthetic Data Performance Discrepancy:** The multilingual NLP classifier attains 100.0% Macro-F1 on the in-domain held-out test set due to structured template generation. On the out-of-domain challenge set with disjoint vocabulary, accuracy drops to **73.33%**. Real-world performance on unconstrained citizen slang would be lower without continuous fine-tuning.
2. **Uncalibrated Vision Probabilities:** Confidence values from Vision-Language Models (Groq Qwen-2.5-VL) reflect language generation heuristics rather than calibrated posterior probabilities.
3. **Simulated Physical Execution:** All field operations (`simulated=True`) simulate workflow logic and resource availability; no physical municipal crews are dispatched.
4. **Photographic Verification Limits:** A post-repair photograph confirms surface cavity filling, but cannot assess asphalt compaction density or structural foundation stability.
5. **Single-Node SQLite Storage:** The prototype uses SQLite with WAL mode, suitable for demonstration and local evaluation, but requires migration to PostgreSQL + PostGIS for enterprise municipal deployments.

*For complete in-depth documentation of limitations and proposed engineering roadmaps, consult:*
- [docs/limitations.md](docs/limitations.md) — Comprehensive failure mode and limitation analysis.
- [docs/future_scope.md](docs/future_scope.md) — Production roadmap (edge models, Open311, sensor fusion).
- [docs/results_table.md](docs/results_table.md) — Empirical validation and invariant test results.

---

## 8. License & Academic Integrity Notice

This project is submitted for academic evaluation. All original code, schemas, orchestration graphs, and documentation are authored for the JanSetu AI research deliverable. Third-party libraries (FastAPI, LangGraph, React, Vite, Leaflet, Tailwind CSS) are used under their respective open-source licenses.
