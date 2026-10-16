import React, { useState } from 'react';
import {
  Cpu,
  Database,
  FileCode,
  Layers,
  RotateCcw,
  Shield,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react';

interface ComponentDetail {
  id: string;
  title: string;
  category: 'frontend' | 'gateway' | 'orchestration' | 'specialist-agent' | 'validator' | 'simulation' | 'gate' | 'persistence';
  file: string;
  role: string;
  inputs: string[];
  outputs: string[];
  invariants: string[];
  description: string;
}

export const SystemArchitectureView: React.FC = () => {
  const [selectedComponentId, setSelectedComponentId] = useState<string>('orchestrator');

  const components: ComponentDetail[] = [
    {
      id: 'react-frontend',
      title: 'React + TypeScript Frontend',
      category: 'frontend',
      file: 'frontend/src/',
      role: 'Citizen Complaint Intake & Operator Command Center',
      inputs: ['Citizen text complaints', 'Device GPS coordinates', 'Camera image uploads', 'Supervisor sign-offs'],
      outputs: ['Multipart/form-data HTTP submissions', 'Real-time telemetry queries', 'Simulation trigger requests'],
      invariants: ['Zero leaked API secrets in client bundle', 'Clearly labels all simulation results with simulated=True'],
      description: 'Single-page web application providing citizen reporting, real-time agent telemetry, Civic Incident Twin inspection, ML Model Lab, and audit trail analytics without predetermined demonstration scripts.',
    },
    {
      id: 'fastapi-gateway',
      title: 'FastAPI REST Application Gateway',
      category: 'gateway',
      file: 'backend/app/main.py',
      role: 'Secure Ingestion, Validation & Storage Routing',
      inputs: ['HTTP requests from React client or API clients'],
      outputs: ['Validated Pydantic models', 'Sanitized file uploads', 'JSON responses with proper HTTP status codes'],
      invariants: ['Strict CORS policy', 'Masked generic internal exception handling (no stack leaks)', 'Image sanitization & EXIF stripping'],
      description: 'Serves REST endpoints for incident intake, lifecycle execution, Civic Incident Twin queries, and ML evaluation metrics with automatic schema validation and transaction safety.',
    },
    {
      id: 'langgraph-orchestrator',
      title: 'LangGraph State Orchestrator',
      category: 'orchestration',
      file: 'backend/app/graph/orchestrator.py',
      role: 'Central Operational State Machine & Lifecycle Coordinator',
      inputs: ['IncidentState (correlation_id, raw_input, location_data, image_bytes)'],
      outputs: ['Updated IncidentState with verified status and chronological audit timeline'],
      invariants: ['All state transitions enforced by state_machine.py', 'Correlation ID preserved across every audit event', 'No state writes overwrite concurrent values'],
      description: 'Coordinates six specialist agents, plan validation, execution simulation, adaptive recovery loops, and closure verification using a deterministic StateGraph architecture.',
    },
    {
      id: 'agent-1-intel',
      title: 'Agent 1: Incident Intelligence',
      category: 'specialist-agent',
      file: 'backend/app/agents/incident_intel.py',
      role: 'Complaint Parsing, NLP Classification & Vision Fusion',
      inputs: ['Citizen text complaint', 'Sanitized photo bytes (optional)'],
      outputs: ['IncidentExtraction facts', 'PhotoEvidenceAnalysis', 'Multimodal fusion verdict'],
      invariants: ['Multimodal fusion disagreement halts automated workflow at NEEDS_CLARIFICATION', 'Missing photo operates in safe degraded mode'],
      description: 'Fuses multilingual text classifications (TF-IDF + Logistic Regression) with Groq Vision LLM evidence analysis. Flags discrepancies between complaint text and uploaded photographs.',
    },
    {
      id: 'agent-2-geo',
      title: 'Agent 2: GeoCivic Intelligence',
      category: 'specialist-agent',
      file: 'backend/app/agents/geocivic.py',
      role: 'Duplicate Detection & Spatial Hotspot Clustering',
      inputs: ['IncidentLocation coordinates', 'Existing active incident registry'],
      outputs: ['Duplicate candidate list', 'DBSCAN cluster IDs', 'Distance and text similarity scores'],
      invariants: ['Invariant 7: Candidate duplicates remain UNCONFIRMED (no automated destructive merge)'],
      description: 'Computes spatial Haversine distances (≤50m threshold) and complaint text semantic similarity. Performs DBSCAN spatial density clustering to detect municipal infrastructure hotspot clusters.',
    },
    {
      id: 'agent-3-priority',
      title: 'Agent 3: Risk & Priority Intelligence',
      category: 'specialist-agent',
      file: 'backend/app/agents/priority.py',
      role: 'Multi-Factor Triage & Emergency Corridor Escalation',
      inputs: ['Extracted defect facts', 'Location tags (school, hospital, highway)'],
      outputs: ['Priority score (0–100)', 'Priority band (Low, Medium, High, Critical)', 'Escalation flag'],
      invariants: ['Mandatory danger detection routes immediately to HUMAN_REVIEW bypassing automated planning'],
      description: 'Calculates composite risk scores based on severity (0.35), exposure (0.30), duration (0.20), and recurrence (0.15). Detects emergency corridors and life-safety hazards.',
    },
    {
      id: 'agent-4-planning',
      title: 'Agent 4: Response Planning',
      category: 'specialist-agent',
      file: 'backend/app/agents/resolution.py',
      role: 'Dual-Track Plan Generation (Relief & Permanent Resolution)',
      inputs: ['Triaged incident facts', 'Priority assessment', 'Available resource catalog'],
      outputs: ['PERMANENT_RESOLUTION plan v1', 'TEMPORARY_RELIEF containment plan'],
      invariants: ['Both plan types generated with distinct IDs and explicit closure criteria'],
      description: 'Generates structured municipal action steps, equipment allocation, estimated completion times, and verifiable physical closure criteria required for independent inspection.',
    },
    {
      id: 'critic-validator',
      title: 'Critic Validator (Separate Safety Gate)',
      category: 'validator',
      file: 'backend/app/agents/critic.py',
      role: 'Pre-Execution Plan Safety & Feasibility Audit',
      inputs: ['Generated ResponsePlan', 'Incident constraints'],
      outputs: ['ValidationDecision (APPROVE, REJECT, ESCALATE)', 'Constraint violation list'],
      invariants: ['Separated from Independent Verification Agent (does not inspect completed physical work)'],
      description: 'Audits plans before field deployment for municipal safety violations, budget overages, and missing permits. If rejected, triggers targeted replanning with constructive feedback.',
    },
    {
      id: 'simulator-engine',
      title: 'Execution Simulator Engine',
      category: 'simulation',
      file: 'backend/app/simulation/simulator.py',
      role: 'Deterministic Field Action Simulation',
      inputs: ['Approved ResponsePlan', 'Simulation scenario configuration'],
      outputs: ['ExecutionAttempt record', 'Outcome (SUCCESS, FAILED)', 'simulated=True flag'],
      invariants: ['Invariant 2: All synthetic actions carry simulated=True marker and unique attempt_id'],
      description: 'Simulates municipal crew deployment, material logistics, and field repairs with reproducible deterministic outcomes (crew shortage, material deficit, weather blocks) for testability.',
    },
    {
      id: 'agent-5-recovery',
      title: 'Agent 5: Adaptive Recovery',
      category: 'specialist-agent',
      file: 'backend/app/agents/recovery.py',
      role: 'Dynamic Re-Planning & Feasible Alternative Selection',
      inputs: ['ExecutionAttempt failure reason', 'Previous plan version', 'Retry count'],
      outputs: ['Revised ResponsePlan v2', 'Incremented retry_count', 'Escalation decision'],
      invariants: ['Invariant 4: Bounded retries (MAX_RECOVERY_RETRIES=2); exhausts to HUMAN_REVIEW'],
      description: 'Analyzes field impediments (e.g., municipal crew shortage) and automatically selects feasible alternatives (e.g., standby contractor team, cold-mix polymer) preserving plan version history.',
    },
    {
      id: 'agent-6-verification',
      title: 'Agent 6: Independent Verification',
      category: 'specialist-agent',
      file: 'backend/app/agents/verification.py',
      role: 'Post-Execution Evidence & Criteria Verification',
      inputs: ['Simulated repair evidence', 'Original plan closure criteria', 'Post-repair photo'],
      outputs: ['VerificationResult (passed=True/False, outcome, criteria_met, unmet_criteria)'],
      invariants: ['Cannot verify plans (pre-execution); only verifies completed physical repair evidence'],
      description: 'Independently inspects field evidence against original closure criteria. Distinct from the Critic. Requires full criteria satisfaction before authorization.',
    },
    {
      id: 'closure-gate',
      title: 'Closure Verification & Supervisor Sign-off Gate',
      category: 'gate',
      file: 'backend/app/graph/state_machine.py',
      role: 'Strict Transition Guard to VERIFIED_CLOSED',
      inputs: ['Current operational status', 'VerificationResult', 'Supervisor sign-off flag'],
      outputs: ['Transition to VERIFIED_CLOSED or route to CLOSURE_BLOCKED / HUMAN_REVIEW'],
      invariants: ['Invariant 1: No transition to VERIFIED_CLOSED without passing VerificationResult'],
      description: 'Enforces hard cryptographic state boundaries: an incident cannot be marked VERIFIED_CLOSED simply because a photo was matched or repair was simulated without passing independent verification.',
    },
    {
      id: 'sqlite-twin-persistence',
      title: 'SQLite Database & Civic Incident Twin',
      category: 'persistence',
      file: 'backend/app/db/ & backend/app/twin/',
      role: 'Immutable Historical Digital Twin Persistence',
      inputs: ['Incidents, Plans, Attempts, VerificationResults, AuditEvents'],
      outputs: ['Normalized Civic Incident Twin records', 'Audit history trail', 'Dashboard aggregates'],
      invariants: ['Never overwrites historical plan versions or execution attempts', 'Transaction rollback safety on failure'],
      description: 'Stores version-preserved plans, all simulated execution attempts, candidate duplicate relationships, model prediction provenance, and full audit logs on disk.',
    },
  ];

  const active = components.find((c) => c.id === selectedComponentId) || components[2];

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="border-b border-slate-800 pb-4">
        <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
          <Layers className="w-6 h-6 text-teal-400" />
          System Architecture & Data Flow
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Inspectable system map representing the real code components, specialist agents, verification gates, and safety invariants.
        </p>
      </div>

      {/* Main Architecture Map & Detail Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Interactive Architecture Flow Diagram */}
        <div className="lg:col-span-2 space-y-4">
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40 text-xs text-slate-400">
            Click any component block below to inspect its genuine source code file, input/output contracts, and architectural invariants.
          </div>

          {/* Layer 1: Client & Gateway */}
          <div className="space-y-2">
            <span className="text-[10px] font-mono uppercase text-slate-500 tracking-wider">1. Intake & REST API Layer</span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                onClick={() => setSelectedComponentId('react-frontend')}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  selectedComponentId === 'react-frontend'
                    ? 'border-teal-500 bg-teal-950/30 ring-1 ring-teal-500/50'
                    : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-teal-400" />
                  <span className="font-bold text-xs text-white">React + Vite Web App</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">Multi-view operator console & citizen intake</p>
                <span className="text-[10px] font-mono text-teal-400/80 mt-1 block">frontend/src/</span>
              </button>

              <button
                onClick={() => setSelectedComponentId('fastapi-gateway')}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  selectedComponentId === 'fastapi-gateway'
                    ? 'border-teal-500 bg-teal-950/30 ring-1 ring-teal-500/50'
                    : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-400" />
                  <span className="font-bold text-xs text-white">FastAPI Application Gateway</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">Pydantic validation, CORS & secure routing</p>
                <span className="text-[10px] font-mono text-emerald-400/80 mt-1 block">backend/app/main.py</span>
              </button>
            </div>
          </div>

          {/* Central Orchestrator */}
          <div className="space-y-2">
            <span className="text-[10px] font-mono uppercase text-slate-500 tracking-wider">2. Central Workflow Orchestration</span>
            <button
              onClick={() => setSelectedComponentId('langgraph-orchestrator')}
              className={`w-full p-4 rounded-xl border text-left transition-all ${
                selectedComponentId === 'langgraph-orchestrator'
                  ? 'border-teal-500 bg-teal-950/40 ring-2 ring-teal-500/50'
                  : 'border-slate-700 bg-slate-900/80 hover:border-teal-600'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-teal-400" />
                  <span className="font-bold text-sm text-white">LangGraph State Orchestrator</span>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-teal-500/20 text-teal-300 border border-teal-500/30">
                  StateGraph Engine
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-1">
                Dispatches per operational state, coordinates parallel triage, enforces transitions, and logs audit events with correlation_id.
              </p>
              <span className="text-[11px] font-mono text-teal-400 mt-2 block">
                backend/app/graph/orchestrator.py • backend/app/graph/state_machine.py
              </span>
            </button>
          </div>

          {/* Specialist Agents (3 Parallel Triage) */}
          <div className="space-y-2">
            <span className="text-[10px] font-mono uppercase text-slate-500 tracking-wider">3. Parallel Intelligence & Triage Agents</span>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <button
                onClick={() => setSelectedComponentId('agent-1-intel')}
                className={`p-3 rounded-xl border text-left transition-all ${
                  selectedComponentId === 'agent-1-intel'
                    ? 'border-teal-500 bg-teal-950/30 ring-1 ring-teal-500/50'
                    : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                }`}
              >
                <div className="font-bold text-xs text-white">Agent 1: Incident Intel</div>
                <p className="text-[11px] text-slate-400 mt-1">NLP + Vision Multimodal Fusion</p>
                <span className="text-[10px] font-mono text-teal-400/80 mt-1 block truncate">incident_intel.py</span>
              </button>

              <button
                onClick={() => setSelectedComponentId('agent-2-geo')}
                className={`p-3 rounded-xl border text-left transition-all ${
                  selectedComponentId === 'agent-2-geo'
                    ? 'border-teal-500 bg-teal-950/30 ring-1 ring-teal-500/50'
                    : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                }`}
              >
                <div className="font-bold text-xs text-white">Agent 2: GeoCivic</div>
                <p className="text-[11px] text-slate-400 mt-1">Duplicates & DBSCAN Clusters</p>
                <span className="text-[10px] font-mono text-teal-400/80 mt-1 block truncate">geocivic.py</span>
              </button>

              <button
                onClick={() => setSelectedComponentId('agent-3-priority')}
                className={`p-3 rounded-xl border text-left transition-all ${
                  selectedComponentId === 'agent-3-priority'
                    ? 'border-teal-500 bg-teal-950/30 ring-1 ring-teal-500/50'
                    : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                }`}
              >
                <div className="font-bold text-xs text-white">Agent 3: Risk & Priority</div>
                <p className="text-[11px] text-slate-400 mt-1">Risk Factors & Corridor Gate</p>
                <span className="text-[10px] font-mono text-teal-400/80 mt-1 block truncate">priority.py</span>
              </button>
            </div>
          </div>

          {/* Planning & Validation Gate */}
          <div className="space-y-2">
            <span className="text-[10px] font-mono uppercase text-slate-500 tracking-wider">4. Response Planning & Safety Gate</span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                onClick={() => setSelectedComponentId('agent-4-planning')}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  selectedComponentId === 'agent-4-planning'
                    ? 'border-teal-500 bg-teal-950/30 ring-1 ring-teal-500/50'
                    : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                }`}
              >
                <div className="font-bold text-xs text-white">Agent 4: Response Planning</div>
                <p className="text-[11px] text-slate-400 mt-1">Permanent Resolution + Temporary Relief plans</p>
                <span className="text-[10px] font-mono text-teal-400/80 mt-1 block">resolution.py</span>
              </button>

              <button
                onClick={() => setSelectedComponentId('critic-validator')}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  selectedComponentId === 'critic-validator'
                    ? 'border-amber-500 bg-amber-950/30 ring-1 ring-amber-500/50'
                    : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
                  <span className="font-bold text-xs text-white">Separate Critic Validator</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">Audits plan safety, resource constraints & budget</p>
                <span className="text-[10px] font-mono text-amber-400/80 mt-1 block">critic.py</span>
              </button>
            </div>
          </div>

          {/* Simulation & Adaptive Recovery Loop */}
          <div className="space-y-2">
            <span className="text-[10px] font-mono uppercase text-slate-500 tracking-wider">5. Execution Simulation & Bounded Recovery Loop</span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                onClick={() => setSelectedComponentId('simulator-engine')}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  selectedComponentId === 'simulator-engine'
                    ? 'border-teal-500 bg-teal-950/30 ring-1 ring-teal-500/50'
                    : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                }`}
              >
                <div className="font-bold text-xs text-white">Field Action Simulator</div>
                <p className="text-[11px] text-slate-400 mt-1">Deterministic simulation (simulated=True)</p>
                <span className="text-[10px] font-mono text-teal-400/80 mt-1 block">simulator.py</span>
              </button>

              <button
                onClick={() => setSelectedComponentId('agent-5-recovery')}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  selectedComponentId === 'agent-5-recovery'
                    ? 'border-teal-500 bg-teal-950/30 ring-1 ring-teal-500/50'
                    : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <RotateCcw className="w-3.5 h-3.5 text-teal-400" />
                  <span className="font-bold text-xs text-white">Agent 5: Adaptive Recovery</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">Selects feasible alternatives (max 2 retries)</p>
                <span className="text-[10px] font-mono text-teal-400/80 mt-1 block">recovery.py</span>
              </button>
            </div>
          </div>

          {/* Verification & Closure Gates */}
          <div className="space-y-2">
            <span className="text-[10px] font-mono uppercase text-slate-500 tracking-wider">6. Independent Verification & Closure Authorization</span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                onClick={() => setSelectedComponentId('agent-6-verification')}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  selectedComponentId === 'agent-6-verification'
                    ? 'border-teal-500 bg-teal-950/30 ring-1 ring-teal-500/50'
                    : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                }`}
              >
                <div className="font-bold text-xs text-white">Agent 6: Independent Verification</div>
                <p className="text-[11px] text-slate-400 mt-1">Physical criterion audit (distinct from Critic)</p>
                <span className="text-[10px] font-mono text-teal-400/80 mt-1 block">verification.py</span>
              </button>

              <button
                onClick={() => setSelectedComponentId('closure-gate')}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  selectedComponentId === 'closure-gate'
                    ? 'border-emerald-500 bg-emerald-950/30 ring-1 ring-emerald-500/50'
                    : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="font-bold text-xs text-white">Closure Gate (Invariant 1)</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">Strict passing verification needed for VERIFIED_CLOSED</p>
                <span className="text-[10px] font-mono text-emerald-400/80 mt-1 block">state_machine.py</span>
              </button>
            </div>
          </div>

          {/* Persistence Layer */}
          <div className="space-y-2">
            <span className="text-[10px] font-mono uppercase text-slate-500 tracking-wider">7. Digital Twin & Persistence</span>
            <button
              onClick={() => setSelectedComponentId('sqlite-twin-persistence')}
              className={`w-full p-3.5 rounded-xl border text-left transition-all ${
                selectedComponentId === 'sqlite-twin-persistence'
                  ? 'border-teal-500 bg-teal-950/30 ring-1 ring-teal-500/50'
                  : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-teal-400" />
                <span className="font-bold text-xs text-white">SQLite Persistence & Civic Incident Twin</span>
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                Version-preserving plans, execution logs, verification records, unconfirmed duplicates, and audit history.
              </p>
              <span className="text-[10px] font-mono text-teal-400/80 mt-1 block">backend/app/db/ • backend/app/twin/</span>
            </button>
          </div>
        </div>

        {/* Inspector Sidebar Panel */}
        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/70 backdrop-blur-md space-y-5 h-fit sticky top-24">
          <div className="border-b border-slate-800 pb-3">
            <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-teal-500/10 text-teal-300 border border-teal-500/30">
              {active.category.toUpperCase()}
            </span>
            <h3 className="text-lg font-bold text-white mt-2 tracking-tight">
              {active.title}
            </h3>
            <div className="flex items-center gap-1.5 mt-1 text-[11px] font-mono text-teal-400">
              <FileCode className="w-3.5 h-3.5" />
              <span>{active.file}</span>
            </div>
          </div>

          {/* Role & Description */}
          <div className="space-y-1.5 text-xs">
            <span className="font-mono text-slate-400 uppercase text-[10px]">Architectural Role:</span>
            <p className="text-slate-200 leading-relaxed">{active.role}</p>
            <p className="text-slate-400 text-[11px] leading-relaxed pt-1">{active.description}</p>
          </div>

          {/* Inputs & Outputs */}
          <div className="space-y-3 pt-2 border-t border-slate-800/80">
            <div>
              <span className="font-mono text-slate-400 uppercase text-[10px] block mb-1">Inputs:</span>
              <ul className="space-y-1">
                {active.inputs.map((inp, idx) => (
                  <li key={idx} className="text-[11px] text-slate-300 flex items-start gap-1.5 font-mono">
                    <span className="text-teal-400 shrink-0">→</span>
                    <span>{inp}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <span className="font-mono text-slate-400 uppercase text-[10px] block mb-1">Outputs / Emits:</span>
              <ul className="space-y-1">
                {active.outputs.map((out, idx) => (
                  <li key={idx} className="text-[11px] text-slate-300 flex items-start gap-1.5 font-mono">
                    <span className="text-emerald-400 shrink-0">←</span>
                    <span>{out}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Enforced Invariants */}
          <div className="pt-2 border-t border-slate-800/80 space-y-1.5">
            <span className="font-mono text-slate-400 uppercase text-[10px] flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5 text-teal-400" />
              System Invariants Enforced:
            </span>
            <div className="space-y-1">
              {active.invariants.map((inv, idx) => (
                <div key={idx} className="p-2 rounded-lg border border-teal-500/30 bg-teal-950/20 text-[11px] text-teal-200 font-mono">
                  {inv}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
