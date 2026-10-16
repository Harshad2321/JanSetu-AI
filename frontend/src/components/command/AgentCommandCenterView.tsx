import React, { useState, useEffect } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  type Node,
  type Edge,
  Position,
  MarkerType,
} from '@xyflow/react';
import { X, RefreshCw, Radio, Clock, ShieldAlert } from 'lucide-react';
import type { Incident, AuditEvent } from '../../types/api';
import { api } from '../../services/api';
import { OperationalStatusBadge } from '../common/StatusBadge';

interface AgentCommandCenterViewProps {
  incidentId: string | null;
  onSelectIncident: (id: string) => void;
}

interface AgentTelemetryModal {
  name: string;
  role: string;
  status: 'COMPLETED' | 'RUNNING' | 'FAILED' | 'REJECTED' | 'WAITING' | 'SKIPPED' | 'ESCALATED' | 'BLOCKED' | 'NOT_EXECUTED' | 'HUMAN_REVIEW';
  startTime?: string;
  endTime?: string;
  durationMs?: number;
  correlationId?: string;
  inputs: Record<string, any>;
  outputs: Record<string, any>;
  decision: string;
  events: AuditEvent[];
}

export const AgentCommandCenterView: React.FC<AgentCommandCenterViewProps> = ({
  incidentId,
  onSelectIncident,
}) => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [activeIncident, setActiveIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [executing, setExecuting] = useState<boolean>(false);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [selectedAgent, setSelectedAgent] = useState<AgentTelemetryModal | null>(null);

  const loadIncidents = async () => {
    try {
      const res = await api.getIncidents({ limit: 50 });
      setIncidents(res.items);
      if (!incidentId && res.items.length > 0) {
        onSelectIncident(res.items[0].incident_id);
      }
    } catch {
      // Ignore
    }
  };

  const loadActiveIncident = async (id: string, background = false) => {
    if (!background) setLoading(true);
    try {
      const data = await api.getIncident(id);
      setActiveIncident(data);
    } catch {
      // Ignore
    } finally {
      if (!background) setLoading(false);
    }
  };

  useEffect(() => {
    loadIncidents();
  }, []);

  useEffect(() => {
    if (incidentId) {
      loadActiveIncident(incidentId);
    }
  }, [incidentId]);

  // Live Auto-Refresh polling
  useEffect(() => {
    if (!autoRefresh || !incidentId) return;
    const interval = setInterval(() => {
      loadActiveIncident(incidentId, true);
    }, 3000);
    return () => clearInterval(interval);
  }, [autoRefresh, incidentId]);

  const handleExecuteWorkflow = async () => {
    if (!activeIncident) return;
    setExecuting(true);
    try {
      await api.runWorkflow(activeIncident.incident_id);
      await loadActiveIncident(activeIncident.incident_id);
      await loadIncidents();
    } catch {
      // Ignore
    } finally {
      setExecuting(false);
    }
  };

  // Helper to query agent traces
  const findTrace = (pattern: string) =>
    activeIncident?.agent_traces?.find((t) =>
      t.agent_name.toLowerCase().includes(pattern.toLowerCase())
    );

  const intelTrace = findTrace('incident');
  const geoTrace = findTrace('geo');
  const prioTrace = findTrace('priority');
  const planTrace = findTrace('plan');
  const criticTrace = findTrace('critic');
  const simTrace = findTrace('simulat');
  const recTrace = findTrace('recovery');
  const verifTrace = findTrace('verif') || findTrace('closure');

  const isEscalated =
    activeIncident?.operational_status === 'ESCALATED' ||
    activeIncident?.operational_status === 'AWAITING_HUMAN_REVIEW';
  const hasIntel = Boolean(activeIncident?.extracted_facts || activeIncident?.evidence_analysis);
  const hasGeo = Boolean(activeIncident?.geo_context);
  const hasPriority = Boolean(activeIncident?.priority);
  const hasPlan = Boolean(activeIncident?.current_plan);
  const hasCritic = Boolean(activeIncident?.validation);
  const isRecovering =
    activeIncident?.operational_status === 'RECOVERING' || (activeIncident?.retry_count || 0) > 0;
  const isSimDone =
    activeIncident?.operational_status === 'SIMULATED_RESOLVED' ||
    Boolean(activeIncident?.simulation_result) ||
    simTrace?.status === 'COMPLETED';
  const isClosureBlocked = activeIncident?.operational_status === 'CLOSURE_BLOCKED';

  // React Flow Nodes
  const nodes: Node[] = [
    // 1. Incident Intelligence
    {
      id: 'intake',
      position: { x: 40, y: 150 },
      data: {
        label: (
          <div className="p-3 text-left">
            <div className="text-[10px] font-mono text-teal-400 font-bold uppercase">Multimodal Gateway</div>
            <div className="text-xs font-bold text-white">1. Incident Intelligence</div>
            <div className="text-[10px] text-slate-400 mt-1">Sanitization, Vision & NLP</div>
            <div className="mt-2 flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  hasIntel ? 'bg-emerald-400' : isEscalated ? 'bg-rose-500' : 'bg-slate-500'
                }`}
              />
              <span className="text-[10px] font-mono text-slate-300">
                {hasIntel ? 'Completed' : isEscalated ? 'Escalated' : 'Ready'}
              </span>
            </div>
          </div>
        ),
      },
      style: {
        background: '#090d16',
        borderColor: hasIntel ? '#2dd4bf' : isEscalated ? '#f43f5e' : '#334155',
        borderRadius: '12px',
        borderWidth: '1.5px',
        width: 190,
      },
      sourcePosition: Position.Right,
    },
    // 2. Branch A: GeoCivic
    {
      id: 'geocivic',
      position: { x: 280, y: 60 },
      data: {
        label: (
          <div className="p-3 text-left">
            <div className="text-[10px] font-mono text-teal-400 font-bold uppercase">Branch A (Parallel)</div>
            <div className="text-xs font-bold text-white">2. Geo-Spatial Intel</div>
            <div className="text-[10px] text-slate-400 mt-1">Haversine & Dup Radar</div>
            <div className="mt-2 flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  hasGeo
                    ? 'bg-emerald-400'
                    : isEscalated
                    ? 'bg-slate-600'
                    : 'bg-slate-500'
                }`}
              />
              <span className="text-[10px] font-mono text-slate-300">
                {hasGeo ? 'Completed' : isEscalated ? 'Bypassed' : 'Waiting'}
              </span>
            </div>
          </div>
        ),
      },
      style: {
        background: '#090d16',
        borderColor: hasGeo ? '#2dd4bf' : '#334155',
        borderRadius: '12px',
        borderWidth: '1.5px',
        width: 185,
      },
      targetPosition: Position.Left,
      sourcePosition: Position.Right,
    },
    // 3. Branch B: Priority Intelligence
    {
      id: 'priority',
      position: { x: 280, y: 240 },
      data: {
        label: (
          <div className="p-3 text-left">
            <div className="text-[10px] font-mono text-teal-400 font-bold uppercase">Branch B (Parallel)</div>
            <div className="text-xs font-bold text-white">3. Risk & Priority</div>
            <div className="text-[10px] text-slate-400 mt-1">Explainable 0-100 Score</div>
            <div className="mt-2 flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  hasPriority
                    ? 'bg-emerald-400'
                    : isEscalated
                    ? 'bg-rose-500'
                    : 'bg-slate-500'
                }`}
              />
              <span className="text-[10px] font-mono text-slate-300">
                {hasPriority ? `${activeIncident?.priority?.priority_score}/100` : isEscalated ? 'Escalated' : 'Waiting'}
              </span>
            </div>
          </div>
        ),
      },
      style: {
        background: '#090d16',
        borderColor: hasPriority ? '#2dd4bf' : isEscalated ? '#f43f5e' : '#334155',
        borderRadius: '12px',
        borderWidth: '1.5px',
        width: 185,
      },
      targetPosition: Position.Left,
      sourcePosition: Position.Right,
    },
    // 4. Branch Join: Response Planning
    {
      id: 'planning',
      position: { x: 515, y: 150 },
      data: {
        label: (
          <div className="p-3 text-left">
            <div className="text-[10px] font-mono text-teal-400 font-bold uppercase">Branch Join</div>
            <div className="text-xs font-bold text-white">4. Response Planning</div>
            <div className="text-[10px] text-slate-400 mt-1">Relief & Permanent Plans</div>
            <div className="mt-2 flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  hasPlan
                    ? 'bg-emerald-400'
                    : isEscalated
                    ? 'bg-rose-500'
                    : 'bg-slate-500'
                }`}
              />
              <span className="text-[10px] font-mono text-slate-300">
                {hasPlan ? 'Plan Formulated' : isEscalated ? 'Bypassed' : 'Waiting'}
              </span>
            </div>
          </div>
        ),
      },
      style: {
        background: '#090d16',
        borderColor: hasPlan ? '#2dd4bf' : '#334155',
        borderRadius: '12px',
        borderWidth: '1.5px',
        width: 195,
      },
      targetPosition: Position.Left,
      sourcePosition: Position.Right,
    },
    // 5. Critic & Validation Gate
    {
      id: 'critic',
      position: { x: 760, y: 150 },
      data: {
        label: (
          <div className="p-3 text-left">
            <div className="text-[10px] font-mono text-amber-400 font-bold uppercase">Safety Pre-Check</div>
            <div className="text-xs font-bold text-white">5. Critic Validator</div>
            <div className="text-[10px] text-slate-400 mt-1">Safety & Feasibility</div>
            <div className="mt-2 flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  hasCritic
                    ? activeIncident?.validation?.status === 'APPROVE'
                      ? 'bg-emerald-400'
                      : 'bg-amber-400'
                    : 'bg-slate-500'
                }`}
              />
              <span className="text-[10px] font-mono text-slate-300">
                {activeIncident?.validation?.status || 'Waiting'}
              </span>
            </div>
          </div>
        ),
      },
      style: {
        background: '#090d16',
        borderColor: hasCritic ? '#f59e0b' : '#334155',
        borderRadius: '12px',
        borderWidth: '1.5px',
        width: 185,
      },
      targetPosition: Position.Left,
      sourcePosition: Position.Right,
    },
    // 6. Deterministic Simulator
    {
      id: 'simulator',
      position: { x: 995, y: 150 },
      data: {
        label: (
          <div className="p-3 text-left">
            <div className="text-[10px] font-mono text-indigo-400 font-bold uppercase">Deterministic Sandbox</div>
            <div className="text-xs font-bold text-white">Execution Simulator</div>
            <div className="text-[10px] text-slate-400 mt-1">simulated=True Intervention</div>
            <div className="mt-2 flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  isSimDone
                    ? 'bg-emerald-400'
                    : isRecovering
                    ? 'bg-amber-400'
                    : 'bg-slate-500'
                }`}
              />
              <span className="text-[10px] font-mono text-slate-300">
                {isSimDone ? 'Simulated' : isRecovering ? 'Obstacle Detected' : 'Waiting'}
              </span>
            </div>
          </div>
        ),
      },
      style: {
        background: '#090d16',
        borderColor: isSimDone ? '#818cf8' : isRecovering ? '#f59e0b' : '#334155',
        borderRadius: '12px',
        borderWidth: '1.5px',
        width: 190,
      },
      targetPosition: Position.Left,
      sourcePosition: Position.Right,
    },
    // 7. Adaptive Recovery Agent
    {
      id: 'recovery',
      position: { x: 880, y: 310 },
      data: {
        label: (
          <div className="p-3 text-left">
            <div className="text-[10px] font-mono text-amber-400 font-bold uppercase">Adaptive Loop</div>
            <div className="text-xs font-bold text-white">6. Adaptive Recovery</div>
            <div className="text-[10px] text-slate-400 mt-1">Crew/Material Replanning</div>
            <div className="mt-2 flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  isRecovering ? 'bg-amber-400 animate-pulse' : 'bg-slate-500'
                }`}
              />
              <span className="text-[10px] font-mono text-slate-300">
                {isRecovering ? `Retry ${activeIncident?.retry_count || 1}/2` : 'Idle'}
              </span>
            </div>
          </div>
        ),
      },
      style: {
        background: '#090d16',
        borderColor: isRecovering ? '#f59e0b' : '#334155',
        borderRadius: '12px',
        borderWidth: '1.5px',
        width: 195,
      },
      targetPosition: Position.Top,
      sourcePosition: Position.Left,
    },
    // 8. Independent Verification Agent (Closure Gate)
    {
      id: 'closure',
      position: { x: 1235, y: 150 },
      data: {
        label: (
          <div className="p-3 text-left">
            <div className="text-[10px] font-mono text-emerald-400 font-bold uppercase">Invariant 1 Gate</div>
            <div className="text-xs font-bold text-white">7. Verification Agent</div>
            <div className="text-[10px] text-slate-400 mt-1">Evidence & Closure Gate</div>
            <div className="mt-2 flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  activeIncident?.operational_status === 'SIMULATED_RESOLVED'
                    ? 'bg-emerald-400'
                    : isClosureBlocked
                    ? 'bg-rose-500'
                    : isEscalated
                    ? 'bg-rose-500'
                    : 'bg-slate-500'
                }`}
              />
              <span className="text-[10px] font-mono text-slate-300">
                {activeIncident?.operational_status === 'SIMULATED_RESOLVED'
                  ? 'Simulated Resolved'
                  : isClosureBlocked
                  ? 'Closure Blocked'
                  : isEscalated
                  ? 'Human Review'
                  : 'Waiting'}
              </span>
            </div>
          </div>
        ),
      },
      style: {
        background: '#090d16',
        borderColor:
          activeIncident?.operational_status === 'SIMULATED_RESOLVED'
            ? '#10b981'
            : isClosureBlocked
            ? '#f43f5e'
            : isEscalated
            ? '#f43f5e'
            : '#334155',
        borderRadius: '12px',
        borderWidth: '1.5px',
        width: 190,
      },
      targetPosition: Position.Left,
    },
  ];

  // React Flow Edges
  const edges: Edge[] = [
    {
      id: 'e-intake-geo',
      source: 'intake',
      target: 'geocivic',
      animated: hasGeo,
      style: { stroke: hasGeo ? '#2dd4bf' : '#475569', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: hasGeo ? '#2dd4bf' : '#475569' },
    },
    {
      id: 'e-intake-prio',
      source: 'intake',
      target: 'priority',
      animated: hasPriority,
      style: { stroke: hasPriority ? '#2dd4bf' : '#475569', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: hasPriority ? '#2dd4bf' : '#475569' },
    },
    {
      id: 'e-geo-plan',
      source: 'geocivic',
      target: 'planning',
      animated: hasPlan,
      style: { stroke: hasPlan ? '#2dd4bf' : '#475569', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: hasPlan ? '#2dd4bf' : '#475569' },
    },
    {
      id: 'e-prio-plan',
      source: 'priority',
      target: 'planning',
      animated: hasPlan,
      style: { stroke: hasPlan ? '#2dd4bf' : '#475569', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: hasPlan ? '#2dd4bf' : '#475569' },
    },
    {
      id: 'e-plan-critic',
      source: 'planning',
      target: 'critic',
      animated: hasCritic,
      style: { stroke: hasCritic ? '#f59e0b' : '#475569', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: hasCritic ? '#f59e0b' : '#475569' },
    },
    {
      id: 'e-critic-sim',
      source: 'critic',
      target: 'simulator',
      animated: isSimDone,
      style: { stroke: isSimDone ? '#818cf8' : '#475569', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: isSimDone ? '#818cf8' : '#475569' },
    },
    {
      id: 'e-sim-closure',
      source: 'simulator',
      target: 'closure',
      animated: activeIncident?.operational_status === 'SIMULATED_RESOLVED',
      style: {
        stroke: activeIncident?.operational_status === 'SIMULATED_RESOLVED' ? '#10b981' : '#475569',
        strokeWidth: 2,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: activeIncident?.operational_status === 'SIMULATED_RESOLVED' ? '#10b981' : '#475569',
      },
    },
    {
      id: 'e-critic-recovery',
      source: 'critic',
      target: 'recovery',
      animated: isRecovering,
      style: { stroke: isRecovering ? '#f59e0b' : '#334155', strokeDasharray: '4', strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: isRecovering ? '#f59e0b' : '#334155' },
    },
    {
      id: 'e-sim-recovery',
      source: 'simulator',
      target: 'recovery',
      animated: isRecovering,
      style: { stroke: isRecovering ? '#f59e0b' : '#334155', strokeDasharray: '4', strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: isRecovering ? '#f59e0b' : '#334155' },
    },
    {
      id: 'e-recovery-planning',
      source: 'recovery',
      target: 'planning',
      animated: isRecovering,
      style: { stroke: isRecovering ? '#f59e0b' : '#334155', strokeDasharray: '4', strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: isRecovering ? '#f59e0b' : '#334155' },
    },
  ];

  // Inspect agent click handler
  const handleNodeClick = (_: React.MouseEvent, node: Node) => {
    if (!activeIncident) return;

    if (node.id === 'intake') {
      setSelectedAgent({
        name: 'Incident Intelligence Agent',
        role: 'Multimodal vision and complaint fact extraction with EXIF sanitization.',
        status: hasIntel ? 'COMPLETED' : isEscalated ? 'HUMAN_REVIEW' : 'WAITING',
        startTime: intelTrace?.start_time,
        endTime: intelTrace?.end_time,
        inputs: {
          complaint: activeIncident.complaint,
          category: activeIncident.category,
          has_photograph: activeIncident.has_photograph,
        },
        outputs: {
          extracted_facts: activeIncident.extracted_facts,
          evidence_analysis: activeIncident.evidence_analysis,
          evidence_status: activeIncident.evidence_status,
        },
        decision: `Photographic evidence outcome: ${activeIncident.evidence_status}`,
        events: activeIncident.audit_timeline.filter((e) => e.agent.includes('Incident') || e.agent.includes('Intake')),
      });
    } else if (node.id === 'geocivic') {
      setSelectedAgent({
        name: 'Geo-Spatial Intelligence Agent',
        role: 'Geospatial duplicate detection using Haversine formula against municipal registry.',
        status: hasGeo ? 'COMPLETED' : isEscalated ? 'BLOCKED' : 'WAITING',
        startTime: geoTrace?.start_time,
        endTime: geoTrace?.end_time,
        inputs: { location: activeIncident.location },
        outputs: { geo_context: activeIncident.geo_context },
        decision: activeIncident.geo_context?.is_duplicate ? 'Potential Duplicate Flagged (UNCONFIRMED)' : 'Unique Civic Incident Confirmed',
        events: activeIncident.audit_timeline.filter((e) => e.agent.includes('GeoCivic')),
      });
    } else if (node.id === 'priority') {
      setSelectedAgent({
        name: 'Risk & Priority Intelligence Agent',
        role: 'Explainable hazard severity, public exposure, and mandatory escalation evaluation.',
        status: hasPriority ? 'COMPLETED' : isEscalated ? 'ESCALATED' : 'WAITING',
        startTime: prioTrace?.start_time,
        endTime: prioTrace?.end_time,
        inputs: {
          category: activeIncident.category,
          severity_indicators: activeIncident.extracted_facts?.severity_indicators,
        },
        outputs: { priority: activeIncident.priority },
        decision: `Assigned Priority: ${activeIncident.priority?.priority_score} (${activeIncident.priority?.priority_band})`,
        events: activeIncident.audit_timeline.filter((e) => e.agent.includes('Priority')),
      });
    } else if (node.id === 'planning') {
      setSelectedAgent({
        name: 'Response Planning Agent',
        role: 'Formulates dual temporary-relief and permanent-resolution plans with closure criteria.',
        status: hasPlan ? 'COMPLETED' : isEscalated ? 'BLOCKED' : 'WAITING',
        startTime: planTrace?.start_time,
        endTime: planTrace?.end_time,
        inputs: {
          geo_context: activeIncident.geo_context,
          priority: activeIncident.priority,
        },
        outputs: { current_plan: activeIncident.current_plan },
        decision: activeIncident.current_plan?.is_revised ? 'Adaptive Plan Revision Applied' : 'Standard Dual Remediation Plan Formulated',
        events: activeIncident.audit_timeline.filter((e) => e.agent.includes('Resolution') || e.agent.includes('Planning')),
      });
    } else if (node.id === 'critic') {
      setSelectedAgent({
        name: 'Critic Validation Agent',
        role: 'Validates safety constraints, resource limits, and authorization before execution.',
        status: activeIncident.validation?.status === 'APPROVE' ? 'COMPLETED' : activeIncident.validation ? 'REJECTED' : isEscalated ? 'BLOCKED' : 'WAITING',
        startTime: criticTrace?.start_time,
        endTime: criticTrace?.end_time,
        inputs: { plan: activeIncident.current_plan, retry_count: activeIncident.retry_count },
        outputs: { validation: activeIncident.validation },
        decision: `Critic Verdict: ${activeIncident.validation?.status || 'Pending'} — ${activeIncident.validation?.feedback || ''}`,
        events: activeIncident.audit_timeline.filter((e) => e.agent.includes('Critic')),
      });
    } else if (node.id === 'simulator') {
      setSelectedAgent({
        name: 'Deterministic Execution Simulator',
        role: 'Simulates municipal intervention deterministically (simulated=True).',
        status: isSimDone ? 'COMPLETED' : isRecovering ? 'FAILED' : isEscalated ? 'BLOCKED' : 'WAITING',
        startTime: simTrace?.start_time,
        endTime: simTrace?.end_time,
        inputs: {
          plan: activeIncident.current_plan,
          scenario: 'Deterministic Execution Engine',
        },
        outputs: {
          simulation_result: activeIncident.simulation_result,
          failure_reason: activeIncident.failure_reason,
        },
        decision: activeIncident.simulation_result ? `Simulation Result: ${activeIncident.simulation_result}` : 'Awaiting Simulation',
        events: activeIncident.audit_timeline.filter((e) => e.agent.includes('Simulator') || e.action.includes('Simulation')),
      });
    } else if (node.id === 'recovery') {
      setSelectedAgent({
        name: 'Adaptive Recovery Agent',
        role: 'Bounded replanning (max 2 retries) upon obstacle detection (crew/materials shortage).',
        status: isRecovering ? 'COMPLETED' : 'WAITING',
        startTime: recTrace?.start_time,
        endTime: recTrace?.end_time,
        inputs: {
          failure_reason: activeIncident.failure_reason,
          retry_count: activeIncident.retry_count,
        },
        outputs: { current_plan: activeIncident.current_plan },
        decision: activeIncident.failure_reason ? `Handled Obstacle: ${activeIncident.failure_reason} (Attempt ${activeIncident.retry_count}/2)` : 'No recovery required.',
        events: activeIncident.audit_timeline.filter((e) => e.agent.includes('Recovery') || e.action.includes('Recovery')),
      });
    } else if (node.id === 'closure') {
      setSelectedAgent({
        name: 'Independent Verification Agent',
        role: 'Invariant 1 Gate: Evaluates completion criteria and synthetic evidence before verified closure.',
        status: activeIncident.operational_status === 'SIMULATED_RESOLVED' ? 'COMPLETED' : isClosureBlocked ? 'FAILED' : isEscalated ? 'HUMAN_REVIEW' : 'WAITING',
        startTime: verifTrace?.start_time,
        endTime: verifTrace?.end_time,
        inputs: {
          closure_evidence: activeIncident.closure_evidence,
          simulation_result: activeIncident.simulation_result,
        },
        outputs: {
          closure_evidence: activeIncident.closure_evidence,
          operational_status: activeIncident.operational_status,
        },
        decision:
          activeIncident.operational_status === 'SIMULATED_RESOLVED'
            ? 'SIMULATED_RESOLVED: All measurable closure criteria verified.'
            : isClosureBlocked
            ? 'CLOSURE_BLOCKED: Evidence missing or criteria unmet.'
            : isEscalated
            ? 'HUMAN_REVIEW: Mandatory escalation routed to municipal supervisor.'
            : 'Awaiting Gate Execution',
        events: activeIncident.audit_timeline.filter((e) => e.agent.includes('Closure') || e.agent.includes('Verification')),
      });
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            Multi-Agent Orchestration Mesh
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time execution telemetry of all 6 specialist agents, Critic safety gate, and deterministic simulator. Click any node to inspect telemetry.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Live Polling Toggle */}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono font-medium rounded-lg border transition-all ${
              autoRefresh
                ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                : 'border-slate-700 bg-slate-900 text-slate-400'
            }`}
            title="Auto-refresh telemetry every 3 seconds"
          >
            <Radio className={`w-3.5 h-3.5 ${autoRefresh ? 'animate-pulse text-emerald-400' : 'text-slate-500'}`} />
            {autoRefresh ? 'Live Polling Active' : 'Polling Paused'}
          </button>

          <select
            value={incidentId || ''}
            onChange={(e) => onSelectIncident(e.target.value)}
            disabled={loading}
            className="px-3 py-1.5 text-xs font-mono font-bold rounded-lg border border-slate-700 bg-slate-900 text-teal-400 focus:outline-none disabled:opacity-50"
          >
            {incidents.map((inc) => (
              <option key={inc.incident_id} value={inc.incident_id}>
                {inc.incident_id} ({inc.operational_status})
              </option>
            ))}
          </select>

          {activeIncident && (
            <button
              onClick={handleExecuteWorkflow}
              disabled={executing}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 shadow-sm transition-all disabled:opacity-50"
              title="Manual re-dispatch (Routine incidents execute automatically on submission)"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${executing ? 'animate-spin text-teal-400' : ''}`} />
              {executing ? 'Running Mesh...' : 'Re-Dispatch (Diagnostics)'}
            </button>
          )}
        </div>
      </div>

      {/* Case Status Pill */}
      {activeIncident && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 font-mono text-xs gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <span className="font-bold text-teal-400">{activeIncident.incident_id}</span>
            <span className="text-slate-500">Status:</span>
            <OperationalStatusBadge status={activeIncident.operational_status} size="sm" />
            {activeIncident.retry_count > 0 && (
              <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
                Replanning Iteration: {activeIncident.retry_count}/2
              </span>
            )}
            {activeIncident.operational_status === 'AWAITING_HUMAN_REVIEW' && (
              <span className="text-[10px] px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/40 flex items-center gap-1">
                <ShieldAlert className="w-3 h-3" />
                Human Review Escalated
              </span>
            )}
          </div>
          <div className="text-[11px] text-slate-400">
            Workflows execute autonomously upon citizen submission. Click any node below to inspect live trace.
          </div>
        </div>
      )}

      {/* React Flow Container */}
      <div className="w-full h-[560px] rounded-2xl border border-slate-800 bg-slate-950 overflow-hidden relative shadow-2xl">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodeClick={handleNodeClick}
          fitView
          attributionPosition="bottom-left"
          className="bg-slate-950"
        >
          <Background color="#1e293b" gap={16} size={1} />
          <Controls className="bg-slate-900 border border-slate-800 fill-slate-300 text-slate-300" />
        </ReactFlow>

        {/* Legend */}
        <div className="absolute top-4 left-4 p-3 rounded-xl bg-slate-900/90 border border-slate-800 backdrop-blur text-[10px] space-y-1.5 font-mono text-slate-300 pointer-events-none">
          <div className="font-bold text-slate-400 border-b border-slate-800 pb-1">Orchestration Legend</div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>Completed Execution</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-amber-400" />
            <span>Critic Rejection / Recovery</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-rose-500" />
            <span>Human Review / Escalated</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-slate-500" />
            <span>Awaiting Upstream Stage</span>
          </div>
        </div>
      </div>

      {/* Telemetry Inspection Drawer Modal */}
      {selectedAgent && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex justify-end">
          <div className="w-full max-w-lg h-full bg-slate-900 border-l border-slate-800 p-6 space-y-6 overflow-y-auto animate-in slide-in-from-right duration-200">
            <div className="flex justify-between items-start border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-base font-bold text-white tracking-tight">{selectedAgent.name}</h3>
                <p className="text-xs text-slate-400 mt-0.5">{selectedAgent.role}</p>
                {selectedAgent.startTime && (
                  <div className="flex items-center gap-2 mt-2 text-[10px] font-mono text-slate-500">
                    <Clock className="w-3 h-3 text-teal-400" />
                    <span>
                      {new Date(selectedAgent.startTime).toLocaleTimeString()} → {selectedAgent.endTime ? new Date(selectedAgent.endTime).toLocaleTimeString() : 'In Progress'}
                    </span>
                  </div>
                )}
              </div>
              <button
                onClick={() => setSelectedAgent(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">Execution Decision</span>
                <p className="text-teal-300 font-semibold mt-1 p-2.5 rounded-lg bg-slate-950 border border-slate-800 font-mono text-xs">
                  {selectedAgent.decision}
                </p>
              </div>

              <div>
                <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">Structured Agent Inputs</span>
                <pre className="mt-1 p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-300 overflow-x-auto max-h-48">
                  {JSON.stringify(selectedAgent.inputs, null, 2)}
                </pre>
              </div>

              <div>
                <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">Structured Agent Outputs</span>
                <pre className="mt-1 p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-300 overflow-x-auto max-h-56">
                  {JSON.stringify(selectedAgent.outputs, null, 2)}
                </pre>
              </div>

              {selectedAgent.events.length > 0 && (
                <div>
                  <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">Chronological Audit Events</span>
                  <div className="mt-2 space-y-2">
                    {selectedAgent.events.map((ev, idx) => (
                      <div key={idx} className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                        <div className="flex justify-between items-center text-[10px] font-mono text-slate-500">
                          <span>{ev.action}</span>
                          <span>{new Date(ev.timestamp).toLocaleTimeString()}</span>
                        </div>
                        <p className="text-slate-300 text-[11px]">{ev.result}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
