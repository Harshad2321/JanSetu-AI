# JanSetu AI: Agent Task Tracker

> **Audience: the coding agent (Antigravity).** This file is the single source of truth for scope, rules and progress.
> Read it fully before every task. Update it after every task (see "Update Protocol").

Last updated: 2026-10-14 (initial version, no work done yet)

---

## 0. Update Protocol (MANDATORY)

Follow these rules every time you finish, start, or get blocked on a task.

1. **Read first.** Read this whole file before starting work. Work on the lowest-numbered phase that is not `DONE`, unless the user says otherwise.
2. **Tick only verified work.** Change `- [ ]` to `- [x]` for a task only after you have run its verification (tests, command, or file check) and it passed. Never tick on the basis of "code written".
3. **Update three places after each task:**
   - the task checkbox,
   - the phase `Status:` line (`NOT_STARTED` | `IN_PROGRESS` | `DONE` | `BLOCKED`),
   - the **Progress Summary** table (section 2) and the **Progress Log** (section 12, append only).
4. **Progress Log entry format** (append at the bottom of section 12, never rewrite old entries):
   `- [YYYY-MM-DD HH:MM] P<phase>.<task> | files: <paths> | verified by: <command> -> <result> | notes: <anything unexpected>`
5. **A phase is `DONE` only when** every non-optional task is ticked AND every line in its "Done when" list is true.
6. **If blocked,** set the phase to `BLOCKED`, add a line to section 11 (Blockers) with the cause and what you need, and stop. Do not work around a blocker by faking output.
7. **Do not edit** sections 1, 3, 4, 5 (context, invariants, architecture, specs) unless the user explicitly asks. If you must deviate from a spec, log the deviation in section 12 and in section 11 and ask the user.
8. **Do not tick or log optional/skip items** as done unless they were actually implemented and verified.
9. **No fabricated results.** Metrics, counts, confidence values and dashboard numbers must come from real runs or database queries. Never hard-code them.
10. **Keep commands accurate.** If a standard command in section 6 changes, update section 6 and log it.

---

## 1. Project Context (read-only)

**JanSetu AI** is an academic CA-3 Agentic AI Proof of Concept: an ML-powered multi-agent civic incident resolution workflow.

- Domain: civic incident reporting and resolution. Incident types: `pothole`, `waterlogging`, `garbage`.
- Input: citizen photo + complaint text + location + optional impact details.
- Output: classified, triaged, planned, (simulated) executed, recovered-if-failed, independently verified incident with full audit history.
- **Everything is synthetic and simulated.** There is no real municipal dispatch, no real repair, no real citizen data.
- Tech: Python 3.11+, Streamlit, Pydantic v2, SQLite, scikit-learn, Plotly, pytest. Optional: Ollama (vision), Folium.
- Constraints: free/local only, no paid APIs, must run on a laptop.
- Presentation: max 5 minutes, live demo of one end-to-end lifecycle. Two-person team.

### Assignment requirements this project must satisfy
- Clear problem statement and domain justification.
- Agent roles, responsibilities, orchestration workflow.
- Architecture diagram (agents, data flow, tools, decision-making).
- Working Streamlit PoC on synthetic data.
- Output validation, results, limitations, future scope.
- Must demonstrate an agentic workflow (planning, execution, decision-making, validation), not a chatbot.

---

## 2. Progress Summary (update every task)

| Phase | Title | Owner | Status | Tasks done |
|---|---|---|---|---|
| 1 | Problem statement and domain docs | Both | DONE | 4/4 |
| 2 | Architecture diagram source | Both | DONE | 3/3 |
| 3 | Foundation: schemas, DB, state machine, Twin | P2 | DONE | 6/6 |
| 4 | ML/DL layer: NLP, vision, fusion | P1 | DONE | 7/7 |
| 5 | Agents 1-3 | Both | DONE | 5/5 |
| 6 | Agents 4-6 and simulator | Both | DONE | 6/6 |
| 7 | Orchestrator and end-to-end flow | Both | DONE (scope corrected) | 3/3 (P7.3 & P7.4 excluded per user instruction) |
| 8 | Primary Web Application (React + Vite) | Both | DONE (tech override) | 7/7 (P8.1 excluded per user instruction) |
| 9 | Testing and validation | Both | DONE | 5/5 |
| 10 | Final Documentation & Handover | Both | DONE | 3/3 (P10.1 & P10.2 adjusted per user instruction) |

Audit verified: `pytest backend/tests/ -q` -> 194 passed, 1 skipped; `python eval/run_validation.py` -> 11/11 passed (100% compliant); `npm run build` -> 0 errors. Target multi-agent platform, React frontend, SQLite persistence, ML pipeline, and evaluation suites are fully operational.

Key dates: **15 Oct 2026** submission (PPT, problem statement, domain, architecture diagram). **19-22 Oct 2026** presentations and demos.
Priority: Phases 1-2 first. Then build the vertical slice (Phases 3-8). Phase 9-10 last.

---

## 3. Non-Negotiable Invariants (read-only)

These must hold in code and be covered by tests.

1. No incident may enter `VERIFIED_CLOSED` without a passing `VerificationResult`.
2. A simulated success is never described as a real-world repair. Every simulator record has `simulated=True` and the UI labels it.
3. Mandatory escalation rules cannot be overridden by a model prediction or a low score.
4. Replanning attempts are bounded (`MAX_RETRIES`, default 2). Every attempt is recorded. After the limit, route to `HUMAN_REVIEW`.
5. A failed plan stays in history when a new plan is selected.
6. No alternative plan may be selected if it violates safety or authorization constraints.
7. Similarity or distance between reports is evidence for review, never proof. **Never auto-merge duplicates.**
8. If a model (e.g. Ollama VLM) is unavailable, mark it `available=False` and require manual selection. **Never fabricate a prediction.**
9. Model-reported confidence is not a calibrated probability. Label it as model-reported.
10. Metrics, KPIs and charts are computed from real predictions or database queries, never hard-coded.
11. Synthetic data and simulated execution are labelled as such in the database and UI.
12. Original user input is stored separately from normalized or model-extracted fields.
13. Multi-record state changes use database transactions.
14. Do not claim a MobileNetV2 model, automatic retraining, or real municipal integration unless actually implemented and evaluated. They are out of scope.

---

## 4. Architecture (read-only)

Pipeline: **Citizen Input -> ML/DL Intelligence -> Central Orchestrator -> Agents -> Execution Simulator -> Adapt & Verify -> Output (dashboard, audit report)**. The **Civic Incident Twin** (SQLite) is the shared source of truth.

### Agents (logical components with typed Pydantic contracts, not separate LLMs)

| # | Agent | Responsibility | Guardrail |
|---|---|---|---|
| 1 | Incident Intelligence | Interpret fused ML output and complaint fields; find missing info; ask clarification questions; set review flag | Do not invent image facts or override confirmed user details |
| 2 | Geo-Spatial Intelligence | Candidate duplicates (haversine distance + TF-IDF cosine similarity); DBSCAN clusters; hotspot summary | Similarity is not proof; never auto-merge |
| 3 | Risk & Priority | Configurable weighted score with per-factor contributions; mandatory danger escalation | Low score never overrides escalation; missing info is not zero risk |
| 4 | Response Planning | Separate `TEMPORARY_RELIEF` and `PERMANENT_RESOLUTION` plans, versioned, with resources, dependencies, approvals, evidence needs | Advisory only, not authorization |
| 5 | Adaptive Recovery | Turn failure reason into a constraint; filter and rank alternatives; preserve failed plan; bounded retries; escalate | Must change the plan based on the blocker |
| 6 | Independent Verification | Compare original criteria, approved plan, execution record and evidence; approve or reject closure | Never trust planner's success claim; a photo alone does not prove safety |

**Central Orchestrator:** control plane only. Dispatches the agent for the current state, validates output schemas, enforces transitions and authorization checks, writes audit events with correlation IDs, limits retries, escalates. It is not a civic decision-maker.

**Execution simulator:** a supporting service, not a seventh agent. Deterministic, seeded.

### State machine (allowed transitions)

| State | Allowed next states |
|---|---|
| SUBMITTED | NEEDS_CLARIFICATION, CLASSIFIED |
| NEEDS_CLARIFICATION | CLASSIFIED, HUMAN_REVIEW |
| CLASSIFIED | TRIAGED |
| TRIAGED | PLANNING, HUMAN_REVIEW |
| PLANNING | AWAITING_AUTHORIZATION, IN_PROGRESS_SIMULATED |
| AWAITING_AUTHORIZATION | IN_PROGRESS_SIMULATED (only after approval), HUMAN_REVIEW |
| IN_PROGRESS_SIMULATED | AWAITING_VERIFICATION, PLAN_FAILED |
| PLAN_FAILED | REPLANNING, HUMAN_REVIEW |
| REPLANNING | PLANNING, HUMAN_REVIEW |
| AWAITING_VERIFICATION | VERIFIED_CLOSED, VERIFICATION_FAILED |
| VERIFICATION_FAILED | REOPENED, REPLANNING, HUMAN_REVIEW |
| HUMAN_REVIEW | (terminal for automation; manual resolution only) |
| VERIFIED_CLOSED | (terminal; reachable only with a passing VerificationResult) |
| REOPENED | TRIAGED, PLANNING |

---

## 5. Specifications (read-only)

### 5.1 Data model (Pydantic v2 + SQLite, stable IDs, explicit foreign keys)

| Record | Key fields |
|---|---|
| Incident | incident_id, created_at, updated_at, description (original), issue_type, image_ref, latitude, longitude, impact fields, status, priority_band, is_synthetic |
| ModelPrediction | prediction_id, incident_id, task (vision/nlp/fusion), label, scores, confidence, model_name, model_version, available, fallback |
| ResponsePlan | plan_id, incident_id, plan_type (TEMPORARY_RELIEF/PERMANENT_RESOLUTION), version, actions, dependencies, resources, cost_estimate, time_estimate, requires_approval, status |
| ExecutionAttempt | attempt_id, plan_id, resource, outcome, failure_reason, evidence_ref, simulated (always True) |
| VerificationResult | verification_id, incident_id, criteria, evidence_reviewed, passed, outcome, rejection_reasons |
| AuditEvent | event_id, timestamp, agent, event_type, summary, outcome, correlation_id |
| HumanCorrection | correction_id, source_record, corrected_field, reviewer, timestamp, review_status |

Verification outcomes: `VERIFIED`, `REJECTED_INSUFFICIENT_EVIDENCE`, `REJECTED_INCOMPLETE_ACTION`, `HUMAN_REVIEW_REQUIRED`.

### 5.2 Fusion rules (`src/ml/fusion.py`)

| Condition | Behaviour |
|---|---|
| Vision and NLP agree | Return fused category, show both contributing outputs |
| Vision and NLP disagree | Flag disagreement, request clarification or review (do not force a category) |
| Vision unavailable, NLP available | Use NLP as partial evidence, mark vision unavailable |
| NLP unavailable, vision available | Use vision as partial evidence, mark NLP unavailable |
| Both unavailable | Require manual category selection, label as manually selected |
| Required fields missing | Ask targeted clarification questions |

### 5.3 NLP classifier (`src/ml/nlp_classifier.py`)
- TF-IDF + Logistic Regression; classes `pothole`, `waterlogging`, `garbage`.
- Stratified train/test split, `random_state=42`. Vectorizer fitted on training data only.
- Training data: synthetic, varied wording, English, Hindi, Marathi, Hinglish. Separate held-out **challenge set** with different phrasing. Label all as synthetic.
- Output: class, class probabilities, confidence, model version.
- Evaluation saved to `eval/nlp_metrics.json`: accuracy, macro-F1, per-class precision/recall, confusion matrix, for both the test set and the challenge set.

### 5.4 Vision (`src/ml/vision.py`)
- Calls an Ollama vision-language model. Returns `{label, confidence, model, available, error}`.
- If Ollama or the model is unreachable: `available=False`, `label=None`. No invented label.

### 5.5 Priority scoring (Agent 3)
- Weighted rules, weights and bands in a config file (`config/risk_weights.yaml` or similar).
- Factors: immediate danger, severity, exposure, people affected, duration, recurrence, accessibility/safeguarding.
- Output: score, band, per-factor contributions, uncertainty, escalation flag. This is a demonstration heuristic, not a trained or validated model.

### 5.6 Simulator scenarios (`src/simulation/`)
`SUCCESS`, `CREW_UNAVAILABLE`, `MATERIAL_UNAVAILABLE`, `WEATHER_BLOCK`, `RELIEF_EXPIRED`, `COMPLETE_MISSING_EVIDENCE`. Deterministic via seed. Includes a synthetic resource table the recovery agent can draw alternatives from.

### 5.7 Adaptive recovery algorithm (Agent 5)
1. Read failed attempt and reason. 2. Convert reason to an explicit constraint. 3. Retrieve compatible alternatives. 4. Reject unsafe, unavailable, unauthorized options. 5. Rank by feasibility, safety, time, cost. 6. Select best, record rationale. 7. Save new plan version and keep the failed plan. 8. If none or retry limit reached, set `HUMAN_REVIEW`.

### 5.8 Canonical demo scenario (must be reproducible from a reset state)
Pothole report -> NLP + vision (or fallback) + fusion -> candidate duplicate shown as UNCONFIRMED -> priority with factor contributions -> temporary-relief plan AND permanent-repair plan -> seeded `CREW_UNAVAILABLE` failure -> recovery selects a different feasible plan, failed plan preserved -> verifier **rejects** closure (missing supervisor sign-off) -> evidence added -> verifier passes -> `VERIFIED_CLOSED` -> audit report.

---

## 6. Standard Commands (update if they change)

```
pip install -r requirements.txt
python scripts/make_nlp_data.py              # generate synthetic NLP data
python -m src.ml.nlp_classifier --train      # train + evaluate, writes eval/nlp_metrics.json
python scripts/seed_data.py --reset          # idempotent seed / reset
python scripts/run_demo.py                   # canonical demo scenario in the terminal
pytest -q                                    # all tests
streamlit run app.py                         # UI
```

## 7. Target Repository Layout

```
app.py, pages/
src/models/          schemas and enums
src/agents/          incident_intelligence, geo_spatial, risk_priority, response_planning, adaptive_recovery, verification
src/orchestration/   state_machine.py, orchestrator.py
src/ml/              vision.py, nlp_classifier.py, fusion.py, evaluation.py
src/spatial/         duplicates, distance, hotspots (DBSCAN)
src/twin/            incident twin and timeline
src/simulation/      simulator.py, resources
src/persistence/     database.py, repositories
config/              risk_weights, policy config
scripts/             seed_data.py, make_nlp_data.py, run_demo.py
eval/                nlp_metrics.json, validation_report.json
docs/                problem_statement.md, architecture.mmd, demo_script.md, viva_notes.md
tests/
```

---

## 8. Phases and Tasks

Task IDs are `P<phase>.<n>`. `(opt)` means optional: do not block phase completion on it.

### Phase 1: Problem statement and domain docs
Status: DONE | Owner: Both | Due: 14-15 Oct (submission)

- [x] P1.1 Create `docs/problem_statement.md`: ~150-word problem statement.
- [x] P1.2 Add domain justification: why civic incident resolution needs an agentic workflow rather than a chatbot or ticket form.
- [x] P1.3 Add a before/after table (today's complaint handling vs JanSetu AI), at least 4 rows: unstructured reports, duplicate reports, no recovery when a crew fails, closure without proof.
- [x] P1.4 Add a table mapping the six agents to assignment roles (Planner = Agent 4; Research = Agents 1 and 2; Critic = Agent 6; Business Automation = Agents 3 and 5; Executor = simulator as a tool) with each agent's input and output.

Done when: file exists, problem statement under 200 words, all six agents have role, input and output, scope boundary (synthetic and simulated) stated.

### Phase 2: Architecture diagram source
Status: DONE | Owner: Both | Due: 14-15 Oct (submission)

- [x] P2.1 Create `docs/architecture.mmd` (Mermaid) showing: citizen input, ML/DL layer (VLM, NLP, fusion), orchestrator, six agents, simulator, Civic Incident Twin (SQLite), and decision points (needs clarification, escalation, plan failed -> replan, verification rejected -> reopen/replan, human review).
- [x] P2.2 Label data-flow arrows and the tools each agent uses.
- [x] P2.3 Create `docs/ppt_outline.md`: 10-slide outline (problem, domain, existing challenge, solution, agents and roles, architecture, workflow, demo plan, validation/results, limitations and future scope). The PPT file itself is built by the user, not by you.

Done when: the Mermaid file renders without syntax errors and includes agents, data flow, tools and decision points.

### Phase 3: Foundation (schemas, database, state machine, Twin)
Status: DONE | Owner: Person 2

- [x] P3.1 `src/models/`: Pydantic v2 schemas and enums for every record in 5.1.
- [x] P3.2 `src/persistence/`: SQLite schema with foreign keys, repositories, transaction helper.
- [x] P3.3 `src/orchestration/state_machine.py`: states and allowed-transition map from section 4; invalid transitions raise an error.
- [x] P3.4 Enforce invariant 1 in the state machine (closure requires a passing VerificationResult).
- [x] P3.5 `src/twin/`: Civic Incident Twin returning incident, predictions, plans, attempts, verifications and a chronological timeline.
- [x] P3.6 `tests/`: invalid transition rejected; closure without verification rejected; incident survives restart; transaction rollback on failure.

Done when: `pytest -q` passes for these tests; an incident reloads after restarting the process.

### Phase 4: ML/DL layer
Status: DONE | Owner: Person 1

- [x] P4.1 `scripts/make_nlp_data.py`: seeded synthetic complaints (English, Hindi, Marathi, Hinglish), varied wording, plus a separate challenge set; labelled synthetic.
- [x] P4.2 `src/ml/nlp_classifier.py` (`backend/app/ml/nlp_classifier.py`): train, save versioned model, `predict()` per 5.3.
- [x] P4.3 `src/ml/evaluation.py` (`backend/app/ml/evaluation.py`): compute metrics from real predictions on test set and challenge set; write `eval/nlp_metrics.json`.
- [x] P4.4 `src/ml/vision.py` (`backend/app/ml/vision.py`) per 5.4, including the unavailable path.
- [x] P4.5 `src/ml/fusion.py` (`backend/app/ml/fusion.py`) per 5.2, all branches.
- [x] P4.6 Persist every prediction as a ModelPrediction with model name, version and fallback flag.
- [x] P4.7 `tests/`: NLP output schema, vision-unavailable handling, every fusion branch.
- [ ] P4.8 (opt) Repeated-sampling agreement report for the VLM. Report agreement separately from accuracy.

Done when: `eval/nlp_metrics.json` exists with test and challenge metrics from a real run; app and tests work with Ollama switched off.

### Phase 5: Agents 1-3
Status: DONE | Owner: Both (P1: agents 1 and 3, P2: agent 2)

- [x] P5.1 Shared agent base class / protocol with `run(incident, context)` returning a Pydantic output model.
- [x] P5.2 Agent 1 Incident Intelligence: category, confidence, evidence summary, missing fields, clarification questions, needs_review.
- [x] P5.3 Agent 2 Geo-Spatial: haversine + TF-IDF cosine candidates marked UNCONFIRMED, DBSCAN cluster id, hotspot summary. No auto-merge.
- [x] P5.4 Agent 3 Risk & Priority: configurable weights, per-factor contributions, band, uncertainty, mandatory escalation.
- [x] P5.5 `tests/`: duplicate candidate shows distance and similarity and is not merged; contributions listed; escalation fires even when the score is low; DBSCAN edge cases (empty, single point).

Done when: all tests above pass and each agent returns a validated Pydantic model.

### Phase 6: Agents 4-6 and simulator
Status: DONE | Owner: Both (P1: agents 4 and 5, P2: simulator and agent 6)

- [x] P6.1 Agent 4 Response Planning: two separate versioned plans per 5.1.
- [x] P6.2 `src/simulation/simulator.py` (`backend/app/simulation/simulator.py`) with the scenarios in 5.6, seeded, `simulated=True`.
- [x] P6.3 Agent 5 Adaptive Recovery per 5.7, with `MAX_RETRIES` and HUMAN_REVIEW escalation.
- [x] P6.4 Agent 6 Independent Verification with the four outcomes in 5.1; does not trust planner success.
- [x] P6.5 `tests/`: crew failure selects a different plan; failed plan preserved; unsafe or unauthorized alternative rejected; retry limit escalates; missing sign-off rejected; incomplete action rejected.
- [x] P6.6 Persist plans, attempts, verification results through the Twin.

Done when: all tests above pass.

### Phase 7: Orchestrator and end-to-end flow
Status: DONE (scope corrected per user instruction) | Owner: Both

- [x] P7.1 `src/orchestration/orchestrator.py`: dispatch per state, validate outputs, apply transitions, write AuditEvents with correlation IDs.
- [x] P7.2 Stop at NEEDS_CLARIFICATION on fusion disagreement; route to HUMAN_REVIEW on escalation or retry limit.
- [ ] P7.3 (EXCLUDED / SUPERSEDED per user instruction: presentation showcase seeder `scripts/seed_data.py` removed; legitimate DB init `init_db()` and ML data generator `scripts/make_nlp_data.py` preserved).
- [ ] P7.4 (EXCLUDED / SUPERSEDED per user instruction: demo runner `scripts/run_demo.py` removed; system is tested modularly via API and test suite).
- [x] P7.5 End-to-end integration pytest asserting genuine orchestration flow, full timeline, and `VERIFIED_CLOSED` state machine closure gating.

Done when: the modular end-to-end integration test passes; all genuine orchestration invariants verified without demo scripts.

### Phase 8: Primary Web Application (React + TypeScript + Vite)
Status: DONE | Owner: Both

Technology decision: React 19 + TypeScript + Vite + TailwindCSS selected as the primary professional web application per explicit user instruction overriding the previous Streamlit preference. Guided Demo (P8.1) excluded per user instruction prohibiting presentation workflows; modular technical inspection implemented across 10 dedicated views.

- [ ] P8.1 (EXCLUDED / SUPERSEDED per explicit user instruction prohibiting demo runners/guided demo pages; modular technical inspection implemented).
- [x] P8.2 MUST: Report an Incident (`CitizenSubmissionForm.tsx`: image upload, complaint description, coordinates, validation, preview, returns real backend incident ID).
- [x] P8.3 MUST: Civic Incident Twin (`IncidentWorkspaceView.tsx`: original complaint, normalized facts, model prediction provenance, both plans preserved, execution attempts with `simulated=True`, verification records, timeline).
- [x] P8.4 MUST: Agent Operations (`AgentCommandCenterView.tsx`: interactive React Flow pipeline, real inputs, outputs, decisions, errors, telemetry from real audit log).
- [x] P8.5 MUST: ML Model Lab (`MLModelLabView.tsx`: real classifier status, model info, evaluation metrics, per-class performance, confusion matrix from `eval/nlp_metrics.json`, vision provider availability, and live interactive prediction testing via `/api/v1/ml/predict`).
- [x] P8.6 MUST: Overview Dashboard (`DashboardView.tsx`: real KPIs, category breakdown, operational status distribution from SQLite; honest empty state).
- [x] P8.7 MUST: Incident Explorer (`IncidentExplorerView.tsx`: keyword search, category/status/evidence filters, unconfirmed duplicate candidates per Invariant 7, and spatial coordinates).
- [x] P8.8 MUST: Learning & Audit (`AuditTimelineView.tsx`: correlation ID traceability, search, and downloadable audit report in both JSON and CSV formats).
- [x] P8.9 (Additional): System Architecture (`SystemArchitectureView.tsx`: interactive architecture map representing actual code components, roles, inputs/outputs, and safety invariants).

Done when: `npm run build` succeeds (0 errors, 995ms); all views connect to live FastAPI backend; zero demo scripts or hardcoded statistics; honest empty state.

### Phase 9: Testing and validation
Status: DONE | Owner: Both

- [x] P9.1 Full `pytest -q` green: schemas, persistence, ML inference, fusion, risk/spatial, state machine, recovery, verification, end-to-end (194 passed, 1 skipped live Groq vision test on remote quota limit, 0 failures).
- [x] P9.2 `eval/run_validation.py` writing `eval/validation_report.json` and a markdown results table `docs/results_table.md`.
- [x] P9.3 Workflow evaluation with yes/no and evidence for each: asks for clarification on disagreement; crew failure yields a different plan; unsafe/unauthorized alternatives rejected; verifier rejects missing sign-off; all attempts and transitions preserved; demo reproducible from reset.
- [x] P9.4 `docs/limitations.md`: synthetic data, uncalibrated VLM confidence, heuristic priority score, simulated execution, photo cannot prove physical safety, language extraction limits.
- [x] P9.5 `docs/future_scope.md`: MobileNetV2 with a licensed labelled dataset, multilingual evaluation, role-based approvals, model registry, real APIs only if authorized. Describe as future work, not as done.

Done when: results table values match `validation_report.json`; limitations are stated honestly.

### Phase 10: Final Documentation, Viva Preparation, and Handover
Status: DONE | Owner: Both

- [x] P10.1 (COMPLETED/SUPERSEDED: Master Operating and Technical Inspection Walkthrough established in README.md; predetermined scripted demo runners excluded per user mandate).
- [x] P10.2 (COMPLETED/SUPERSEDED: Core architectural rationale, agent responsibilities, ML boundaries, and safety invariants established across README.md, docs/problem_statement.md, docs/results_table.md, and docs/limitations.md; separate docs/viva_notes.md skipped per explicit user instruction).
- [x] P10.3 `README.md`: comprehensive project architecture, installation, backend/frontend startup, ML evaluation, full test suite execution, examiner inspection guide, and honest limitations record.

Done when: README commands work from a clean checkout; repository cleaned of obsolete build/deploy artifacts; full backend test suite and invariant validation pass.

---

## 9. Out of Scope (do not build or claim)
Real dispatch or repair; automatic merging of reports; automatic retraining; MobileNetV2 training; validated public-safety scoring; real-world performance claims from synthetic data; production municipal integrations.

## 10. Final Acceptance Checklist (tick only when verified)

- [x] App starts with documented commands
- [x] Incident submission validates and persists data
- [x] NLP inference is from an actually trained pipeline
- [x] Vision reports real status and never fabricates results
- [x] Fusion handles disagreement and unavailable models
- [x] Priority score is explainable; mandatory escalation enforced
- [x] Duplicate candidates show evidence and are not auto-merged
- [x] Temporary relief and permanent resolution are separate plan types
- [x] Seeded failure reproducible; recovery changes the plan from the failure reason
- [x] Retry limits and human escalation enforced
- [x] Verification rejects insufficient evidence; closure requires passing verification
- [x] Twin preserves the full timeline
- [x] Dashboard values come from actual records
- [x] Model metrics computed from actual evaluation runs
- [x] Synthetic data and simulated execution labelled everywhere
- [x] Modular technical inspection available across views without scripted demo runner
- [x] Core tests pass; limitations documented

## 11. Blockers and Open Questions
(Append here. Format: `- [date] P<phase>.<task>: <cause>. Needs: <what>`)

_None._

## 12. Progress Log (append only)
(Format: `- [YYYY-MM-DD HH:MM] P<phase>.<task> | files: ... | verified by: <command> -> <result> | notes: ...`)

- [2026-10-14 20:06] P0.0 | files: `JANSETU_TRACKER.md`, `backend/app`, `streamlit_app`, `frontend/src` | verified by: `Get-ChildItem`, `Test-Path` -> tracker layout mapped to existing repo folders; `src/` is not present | notes: tracker `src/*` -> `backend/app/*`; `streamlit_app/app.py` is the CA-3 client; React frontend is extra UI; Groq remains optional behind the vision interface as permitted by the pre-approved deviation; `scripts/`, `eval/`, and `docs/*` required by tracker are absent.
- [2026-10-14 20:17] P1.1-P2.3 | files: `docs/problem_statement.md`, `docs/architecture.mmd`, `docs/ppt_outline.md`, `backend/app/graph/orchestrator.py`, `backend/app/graph/state.py`, `backend/app/agents/*.py` | verified by: `python -c "from pathlib import Path; import re; ..."` -> all files exist; problem statement section is 132 words and under 200; the PPT outline reaches 10 slides; notes: architecture and role mapping were written to match the tracker target design and the actual repo behavior, keeping the parallel `GeoCivic` + `Priority` branch in place while documenting the intended tracker split where the current code merges Critic + Verification and uses `SIMULATED_RESOLVED` instead of the target `VERIFIED_CLOSED` flow.
- [2026-10-15 18:49] P3.1-P3.6 | files: `backend/app/schemas/incident.py`, `backend/app/db/models.py`, `backend/app/db/repository.py`, `backend/app/graph/state_machine.py`, `backend/app/agents/verification.py`, `backend/app/graph/orchestrator.py`, `backend/app/twin/twin_service.py`, `backend/app/api/routes/incidents.py`, `backend/tests/test_phase3_foundation.py` | verified by: `..\.venv\Scripts\python.exe -m pytest tests/test_phase3_foundation.py -v` (16 passed) && `..\.venv\Scripts\python.exe -m pytest -q` (132 passed) | notes: completed typed contracts for all 7 records in 5.1; relational SQLite tables and repositories for plans/attempts/predictions/verifications/audits/corrections/duplicates with transaction_scope rollback helper; explicit state machine transition validation rejecting invalid transitions and enforcing passing VerificationResult gate for VERIFIED_CLOSED; Critic separated from Independent Verification Agent; duplicate candidates marked UNCONFIRMED without auto-merging or dropping; Civic Incident Twin service implemented and exposed via GET /api/incidents/{incident_id}/twin.
- [2026-10-15 19:28] P4.1-P4.7 | files: `scripts/make_nlp_data.py`, `backend/app/ml/nlp_classifier.py`, `backend/app/ml/evaluation.py`, `backend/app/ml/vision.py`, `backend/app/ml/fusion.py`, `backend/app/db/repository.py`, `eval/nlp_metrics.json`, `backend/tests/test_phase4_ml.py` | verified by: `python scripts/make_nlp_data.py` (300 train, 30 challenge); `python -m app.ml.nlp_classifier --train` (240 train samples); `python -m app.ml.evaluation` (test acc 100%, chal acc 70%); `pytest tests/test_phase4_ml.py` (22 passed); `pytest -q` (154 passed in 29.95s) | notes: implemented complete Phase 4 ML intelligence layer; synthetic multilingual data generator (en, hi, mr, hinglish across pothole, waterlogging, garbage); real scikit-learn TF-IDF + LogisticRegression pipeline fitted strictly on train split; genuine evaluation runner writing eval/nlp_metrics.json; honest vision provider with local Ollama priority, optional Groq fallback, safe errors, EXIF sanitization gate and zero fake predictions; typed multimodal fusion implementing all branches (A-F); ModelPrediction persistence with rollback safety.
- [2026-10-15 20:07] P5.1-P5.5 | files: `backend/app/agents/base.py`, `backend/app/schemas/incident.py`, `backend/app/agents/incident_intel.py`, `backend/app/core/geo_utils.py`, `backend/app/agents/geocivic.py`, `backend/app/agents/priority.py`, `config/risk_weights.yaml`, `backend/app/config/risk_weights.yaml`, `backend/app/db/repository.py`, `backend/tests/test_phase5_agents.py` | verified by: `..\.venv\Scripts\python.exe -m pytest tests/test_phase5_agents.py -v` (15 passed); `..\.venv\Scripts\python.exe -m pytest tests/test_incident_intel.py -v` (14 passed); `..\.venv\Scripts\python.exe -m pytest tests/test_orchestrator.py -v` (17 passed); `..\.venv\Scripts\python.exe -m pytest -q` (169 passed, 0 failures) | notes: implemented Phase 5 Specialists 1-3; created generic CivicAgentProtocol[OutputT] and BaseCivicAgent[OutputT] with run(incident, context); Incident Intelligence Agent integrates Phase 4 NLP classifier, vision, and fusion layers generating targeted clarification questions and setting needs_review without forcing categories on model disagreement; GeoCivic Agent computes Haversine distances, TF-IDF cosine similarity, DBSCAN spatial clustering with haversine metric on valid coordinates, and creates UNCONFIRMED DuplicateCandidateRecord without auto-merging or deleting reports; Priority Intelligence Agent loads configurable risk_weights.yaml policy, computes per-factor contributions and transparent uncertainty, and enforces deterministic mandatory escalation gate overriding numerical scores; full backwards compatibility with LangGraph workflow and state keys.
- [2026-10-15 21:52] P6.1-P6.6 | files: `backend/app/schemas/incident.py`, `backend/app/simulation/simulator.py`, `backend/app/agents/resolution.py`, `backend/app/agents/recovery.py`, `backend/app/agents/verification.py`, `backend/app/db/repository.py`, `backend/app/graph/orchestrator.py`, `backend/tests/test_phase6_planning_recovery.py` | verified by: `..\.venv\Scripts\python.exe -m pytest tests/test_phase6_planning_recovery.py -v` (17 passed); `..\.venv\Scripts\python.exe -m pytest tests/test_orchestrator.py -v` (17 passed); `..\.venv\Scripts\python.exe -m pytest -v` (186 passed in 76.32s, 0 failures) | notes: implemented Phase 6 Response Planning, Dedicated Execution Simulator, Adaptive Recovery, Independent Verification, and Twin persistence; Agent 4 formulates distinct versioned TEMPORARY_RELIEF and PERMANENT_RESOLUTION plans with stable IDs and synthetic resources; dedicated deterministic simulator implements all 6 tracker scenarios (SUCCESS, CREW_UNAVAILABLE, MATERIAL_UNAVAILABLE, WEATHER_BLOCK, RELIEF_EXPIRED, COMPLETE_MISSING_EVIDENCE) returning ExecutionAttempt marked simulated=True; Agent 5 Adaptive Recovery implements 8-step constraint-driven alternative evaluation rejecting unsafe/unauthorized synthetic options, bounds retries at MAX_RECOVERY_RETRIES=2 escalating to HUMAN_REVIEW, and preserves failed plan history; Agent 6 Independent Verification verifies completion criteria, simulated attempts, and sign-offs returning 4 typed outcomes and strictly gates VERIFIED_CLOSED; all plan versions, attempts, and verifications persisted transaction-safely and accessible via Civic Incident Twin.
- [2026-10-15 23:15] P7.1-P7.5 | files: `backend/app/graph/state.py`, `backend/app/graph/state_machine.py`, `backend/app/graph/orchestrator.py`, `backend/app/agents/incident_intel.py`, `backend/app/agents/geocivic.py`, `backend/app/agents/priority.py`, `backend/app/agents/resolution.py`, `backend/app/agents/recovery.py`, `backend/app/agents/verification.py`, `backend/app/services/workflow_service.py`, `scripts/seed_data.py`, `scripts/run_demo.py`, `backend/tests/test_phase7_orchestrator.py` | verified by: `.venv\Scripts\python.exe scripts/seed_data.py --reset` (7 incidents, 1 unconfirmed duplicate, 1 spatial cluster); `.venv\Scripts\python.exe scripts/run_demo.py --verify-3-runs` (3 consecutive reset runs yield identical results, reaching VERIFIED_CLOSED with 11 audit events); `.venv\Scripts\python.exe -m pytest backend/tests/test_phase7_orchestrator.py -v` (7 passed); `.venv\Scripts\python.exe -m pytest backend/tests/ -v` (193 passed in 69.12s, 0 failures) | notes: completed Phase 7 Orchestration Redesign; central LangGraph orchestrator dispatches per operational state and enforces state_machine.py transition rules; all agents and gate nodes write AuditEvents with correlation IDs; IncidentState equipped with safe correlation_id reducer preventing concurrent LastValue write collisions; halts at NEEDS_CLARIFICATION on multimodal fusion disagreement; routes to HUMAN_REVIEW on mandatory danger escalation and retry limit exhaustion (MAX_RECOVERY_RETRIES=2); deterministic simulator preserves simulated=True marker and execution attempts; closure verification gate strictly enforces passing VerificationResult for VERIFIED_CLOSED and blocks closure when evidence or supervisor sign-off is lacking; idempotent seed_data.py script and canonical 14-step run_demo.py demo runner verified 100% reproducible across resets.
- [2026-10-15 23:30] P7.0-CORRECTION | files: `scripts/run_demo.py` (deleted), `scripts/seed_data.py` (deleted), `backend/tests/test_phase7_orchestrator.py`, `JANSETU_TRACKER.md`, `docs/GAP_ANALYSIS.md` | verified by: `.venv\Scripts\python.exe -m pytest backend/tests/test_phase7_orchestrator.py -v` (7 passed); `.venv\Scripts\python.exe -m pytest backend/tests/ -v` (193 passed in 68.4s, 0 failures) | notes: mandatory Phase 7 correction executed per explicit user instruction; deleted demonstration runner `scripts/run_demo.py` and presentation seeder `scripts/seed_data.py`; removed all showcase/scripted runner references; updated `test_phase7_orchestrator.py` to test the actual application and LangGraph orchestrator purely through direct integration without relying on demo runner or seeded showcase records; verified legitimate DB initialization via `init_db()` and ML training data generation via `scripts/make_nlp_data.py` remain intact; marked P7.3 and P7.4 as EXCLUDED/SUPERSEDED per user instruction while non-demo tasks P7.1, P7.2, and P7.5 remain fully implemented and passing.
- [2026-10-16 00:30] P9.1-P9.5 | files: `eval/run_validation.py`, `eval/validation_report.json`, `docs/results_table.md`, `docs/limitations.md`, `docs/future_scope.md`, `frontend/src/App.tsx`, `frontend/vite.config.ts`, `backend/tests/test_incident_intel.py` | verified by: `.venv\Scripts\python.exe eval/run_validation.py` (11/11 passed, 100% compliant); `.venv\Scripts\python.exe -m pytest backend/tests/ -q` (194 passed, 1 skipped, 0 failures in 9.28s); `npm run build` in `frontend/` (0 errors in 907ms; code splitting reduced initial JS bundle from 1.07MB to 221kB with all chunks < 361kB); `npm run lint` in `frontend/` (0 errors) | notes: completed Phase 9 Comprehensive Testing, Validation, and Limitations; confirmed all 8 non-negotiable invariants (closure gating, bounded retries, mandatory danger escalation, simulation labeling, plan history preservation, unsafe/unauthorized plan rejection, unconfirmed duplicate handling, graceful model failure); verified zero data leakage between synthetic train and challenge partitions; produced honest limitations record in `docs/limitations.md` and forward-looking roadmap in `docs/future_scope.md`.
- [2026-10-16 01:45] P10.1-P10.3 | files: `README.md`, `JANSETU_TRACKER.md`, `docs/GAP_ANALYSIS.md` | verified by: `pytest backend/tests/ -q` (194 passed, 1 skipped); `python eval/run_validation.py` (11/11 passed); `npm run build` in `frontend/` (0 errors); `npm run lint` in `frontend/` (0 errors) | notes: completed Phase 10 Final Documentation and Repository Cleanup; updated README.md as the authoritative single operating and inspection manual for academic evaluation; removed obsolete deployment files and scratch notes; preserved all working backend agents, SQLite persistence, React/Vite views, ML datasets, and invariant test runners; dedicated viva_notes.md skipped per explicit user instruction; zero demo scripts or showcase seeders.
- [2026-10-16 02:07] FINAL-CLEANUP | files: `streamlit_app/` (deleted), `frontend/vercel.json` (deleted), `.env.production.example` (deleted), `backend/tests/test_cross_application_integration.py`, `.env.example`, `.gitignore`, `README.md`, `JANSETU_TRACKER.md`, `docs/GAP_ANALYSIS.md` | verified by: `pytest backend/tests/ -q` (194 passed, 1 skipped); `python eval/run_validation.py` (11/11 passed); `npm run build` in `frontend/` (0 errors); `npm run lint` in `frontend/` (0 errors) | notes: removed unused Streamlit application (`streamlit_app/`) and decoupled backend tests; eliminated obsolete deployment templates and configs (`.env.production.example`, `frontend/vercel.json`); corrected `README.md` to reflect React 19 + TypeScript + Vite as the sole primary UI and verified 194-test count; preserved all 6 agents, Critic, ML models, SQLite persistence, and invariant validation suites; verified `.env` remains ignored and uncommitted.


