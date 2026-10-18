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
            <div className="text-[10px] font-mono text-teal-700 font-bold uppercase tracking-wider">Gateway</div>
            <div className="text-xs font-bold text-[#172033] mt-0.5">1. Incident Intel</div>
            <div className="text-[10px] text-slate-500 mt-1">Vision, Sanitization & NLP</div>
            <div className="mt-2.5 flex items-center gap-1.5 pt-2 border-t border-slate-100">
              <span
                className={`w-2 h-2 rounded-full ${
                  hasIntel ? 'bg-emerald-500' : isEscalated ? 'bg-rose-500' : 'bg-slate-300'
                }`}
              />
              <span className="text-[10px] font-mono font-medium text-slate-600">
                {hasIntel ? 'Completed' : isEscalated ? 'Escalated' : 'Ready'}
              </span>
            </div>
          </div>
        ),
      },
      style: {
        background: '#FFFFFF',
        borderColor: hasIntel ? '#0F766E' : isEscalated ? '#DC2626' : '#E2E8F0',
        borderRadius: '10px',
        borderWidth: hasIntel ? '2px' : '1px',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.06)',
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
            <div className="text-[10px] font-mono text-teal-700 font-bold uppercase tracking-wider">Branch A (Parallel)</div>
            <div className="text-xs font-bold text--[#172033] mt-0.5">2. Geo-Spatial Intel</div>
            <div className="text-[10px] text-slate-500 mt-1">Haversine & Dup Radar</div>
            <div className="mt-2.5 flex items-center gap-1.5 pt-2 border-t border-slate-100">
              <span
                className={`w-2 h-2 rounded-full ${
                  hasGeo
                    ? 'bg-emerald-500'
                    : isEscalated
                    ? 'bg-slate-400'
                    : 'bg-slate-300'
                }`}
              />
              <span className="text-[10px] font-mono font-medium text-slate-600">
                {hasGeo ? 'Completed' : isEscalated ? 'Bypassed' : 'Waiting'}
              </span>
            </div>
          </div>
        ),
      },
      style: {
        background: '#FFFFFF',
        borderColor: hasGeo ? '#0F766E' : '#E2E8F0',
        borderRadius: '10px',
        borderWidth: hasGeo ? '2px' : '1px',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.06)',
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
            <div className="text-[10px] font-mono text-teal-700 font-bold uppercase tracking-wider">Branch B (Parallel)</div>
            <div className="text-xs font-bold text-[#172033] mt-0.5">3. Risk & Priority</div>
            <div className="text-[10px] text-slate-500 mt-1">Explainable 0-100 Score</div>
            <div className="mt-2.5 flex items-center gap-1.5 pt-2 border-t border-slate-100">
              <span
                className={`w-2 h-2 rounded-full ${
                  hasPriority
                    ? 'bg-emerald-500'
                    : isEscalated
                    ? 'bg-rose-500'
                    : 'bg-slate-300'
                }`}
              />
              <span className="text-[10px] font-mono font-medium text-slate-600">
                {hasPriority ? `${activeIncident?.priority?.priority_score}/100` : isEscalated ? 'Escalated' : 'Waiting'}
              </span>
            </div>
          </div>
        ),
      },
      style: {
        background: '#FFFFFF',
        borderColor: hasPriority ? '#0F766E' : isEscalated ? '#DC2626' : '#E2E8F0',
        borderRadius: '10px',
        borderWidth: hasPriority ? '2px' : '1px',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.06)',
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
            <div className="text-[10px] font-mono text-teal-700 font-bold uppercase tracking-wider">Branch Join</div>
            <div className="text-xs font-bold text-[#172033] mt-0.5">4. Response Planning</div>
            <div className="text-[10px] text-slate-500 mt-1">Dual Stage Remediation</div>
            <div className="mt-2.5 flex items-center gap-1.5 pt-2 border-t border-slate-100">
              <span
                className={`w-2 h-2 rounded-full ${
                  hasPlan
                    ? 'bg-emerald-500'
                    : isEscalated
                    ? 'bg-rose-500'
                    : 'bg-slate-300'
                }`}
              />
              <span className="text-[10px] font-mono font-medium text-slate-600">
                {hasPlan ? 'Plan Ready' : isEscalated ? 'Bypassed' : 'Waiting'}
              </span>
            </div>
          </div>
        ),
      },
      style: {
        background: '#FFFFFF',
        borderColor: hasPlan ? '#0F766E' : '#E2E8F0',
        borderRadius: '10px',
        borderWidth: hasPlan ? '2px' : '1px',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.06)',
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
            <div className="text-[10px] font-mono text-amber-700 font-bold uppercase tracking-wider">Safety Gate</div>
            <div className="text-xs font-bold text-[#172033] mt-0.5">5. Critic Validator</div>
            <div className="text-[10px] text-slate-500 mt-1">Safety & Feasibility</div>
            <div className="mt-2.5 flex items-center gap-1.5 pt-2 border-t border-slate-100">
              <span
                className={`w-2 h-2 rounded-full ${
                  hasCritic
                    ? activeIncident?.validation?.status === 'APPROVE'
                      ? 'bg-emerald-500'
                      : 'bg-amber-500'
                    : 'bg-slate-300'
                }`}
              />
              <span className="text-[10px] font-mono font-medium text-slate-600">
                {activeIncident?.validation?.status || 'Waiting'}
              </span>
            </div>
          </div>
        ),
      },
      style: {
        background: '#FFFFFF',
        borderColor: hasCritic ? '#D97706' : '#E2E8F0',
        borderRadius: '10px',
        borderWidth: hasCritic ? '2px' : '1px',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.06)',
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
            <div className="text-[10px] font-mono text-indigo-700 font-bold uppercase tracking-wider">Sandbox Engine</div>
            <div className="text-xs font-bold text-[#172033] mt-0.5">Execution Simulator</div>
            <div className="text-[10px] text-slate-500 mt-1">simulated=True Run</div>
            <div className="mt-2.5 flex items-center gap-1.5 pt-2 border-t border-slate-100">
              <span
                className={`w-2 h-2 rounded-full ${
                  isSimDone
                    ? 'bg-emerald-500'
                    : isRecovering
                    ? 'bg-amber-500'
                    : 'bg-slate-300'
                }`}
              />
              <span className="text-[10px] font-mono font-medium text-slate-600">
                {isSimDone ? 'Simulated' : isRecovering ? 'Obstacle' : 'Waiting'}
              </span>
            </div>
          </div>
        ),
      },
      style: {
        background: '#FFFFFF',
        borderColor: isSimDone ? '#4F46E5' : isRecovering ? '#D97706' : '#E2E8F0',
        borderRadius: '10px',
        borderWidth: isSimDone || isRecovering ? '2px' : '1px',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.06)',
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
            <div className="text-[10px] font-mono text-amber-700 font-bold uppercase tracking-wider">Adaptive Loop</div>
            <div className="text-xs font-bold text-[#172033] mt-0.5">6. Adaptive Recovery</div>
            <div className="text-[10px] text-slate-500 mt-1">Crew/Material Replanning</div>
            <div className="mt-2.5 flex items-center gap-1.5 pt-2 border-t border-slate-100">
              <span
                className={`w-2 h-2 rounded-full ${
                  isRecovering ? 'bg-amber-500 animate-pulse' : 'bg-slate-300'
                }`}
              />
              <span className="text-[10px] font-mono font-medium text-slate-600">
                {isRecovering ? `Retry ${activeIncident?.retry_count || 1}/2` : 'Idle'}
              </span>
            </div>
          </div>
        ),
      },
      style: {
        background: '#FFFFFF',
        borderColor: isRecovering ? '#D97706' : '#E2E8F0',
        borderRadius: '10px',
        borderWidth: isRecovering ? '2px' : '1px',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.06)',
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
            <div className="text-[10px] font-mono text-emerald-800 font-bold uppercase tracking-wider">Invariant 1 Gate</div>
            <div className="text-xs font-bold text-[#172033] mt-0.5">7. Verification Agent</div>
            <div className="text-[10px] text-slate-500 mt-1">Evidence & Closure Gate</div>
            <div className="mt-2.5 flex items-center gap-1.5 pt-2 border-t border-slate-100">
              <span
                className={`w-2 h-2 rounded-full ${
                  activeIncident?.operational_status === 'SIMULATED_RESOLVED'
                    ? 'bg-emerald-500'
                    : isClosureBlocked
                    ? 'bg-rose-500'
                    : isEscalated
                    ? 'bg-rose-500'
                    : 'bg-slate-300'
                }`}
              />
              <span className="text-[10px] font-mono font-medium text-slate-600">
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
        background: '#FFFFFF',
        borderColor:
          activeIncident?.operational_status === 'SIMULATED_RESOLVED'
            ? '#0F766E'
            : isClosureBlocked
            ? '#DC2626'
            : isEscalated
            ? '#DC2626'
            : '#E2E8F0',
        borderRadius: '10px',
        borderWidth:
          activeIncident?.operational_status === 'SIMULATED_RESOLVED' || isClosureBlocked || isEscalated
            ? '2px'
            : '1px',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.06)',
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
      style: { stroke: hasGeo ? '#0F766E' : '#CBD5E1', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: hasGeo ? '#0F766E' : '#CBD5E1' },
    },
    {
      id: 'e-intake-prio',
      source: 'intake',
      target: 'priority',
      animated: hasPriority,
      style: { stroke: hasPriority ? '#0F766E' : '#CBD5E1', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: hasPriority ? '#0F766E' : '#CBD5E1' },
    },
    {
      id: 'e-geo-plan',
      source: 'geocivic',
      target: 'planning',
      animated: hasPlan,
      style: { stroke: hasPlan ? '#0F766E' : '#CBD5E1', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: hasPlan ? '#0F766E' : '#CBD5E1' },
    },
    {
      id: 'e-prio-plan',
      source: 'priority',
      target: 'planning',
      animated: hasPlan,
      style: { stroke: hasPlan ? '#0F766E' : '#CBD5E1', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: hasPlan ? '#0F766E' : '#CBD5E1' },
    },
    {
      id: 'e-plan-critic',
      source: 'planning',
      target: 'critic',
      animated: hasCritic,
      style: { stroke: hasCritic ? '#D97706' : '#CBD5E1', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: hasCritic ? '#D97706' : '#CBD5E1' },
    },
    {
      id: 'e-critic-sim',
      source: 'critic',
      target: 'simulator',
      animated: isSimDone,
      style: { stroke: isSimDone ? '#4F46E5' : '#CBD5E1', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: isSimDone ? '#4F46E5' : '#CBD5E1' },
    },
    {
      id: 'e-sim-closure',
      source: 'simulator',
      target: 'closure',
      animated: activeIncident?.operational_status === 'SIMULATED_RESOLVED',
      style: {
        stroke: activeIncident?.operational_status === 'SIMULATED_RESOLVED' ? '#0F766E' : '#CBD5E1',
        strokeWidth: 2,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: activeIncident?.operational_status === 'SIMULATED_RESOLVED' ? '#0F766E' : '#CBD5E1',
      },
    },
    {
      id: 'e-critic-recovery',
      source: 'critic',
      target: 'recovery',
      animated: isRecovering,
      style: { stroke: isRecovering ? '#D97706' : '#CBD5E1', strokeDasharray: '4', strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: isRecovering ? '#D97706' : '#CBD5E1' },
    },
    {
      id: 'e-sim-recovery',
      source: 'simulator',
      target: 'recovery',
      animated: isRecovering,
      style: { stroke: isRecovering ? '#D97706' : '#CBD5E1', strokeDasharray: '4', strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: isRecovering ? '#D97706' : '#CBD5E1' },
    },
    {
      id: 'e-recovery-planning',
      source: 'recovery',
      target: 'planning',
      animated: isRecovering,
      style: { stroke: isRecovering ? '#D97706' : '#CBD5E1', strokeDasharray: '4', strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: isRecovering ? '#D97706' : '#CBD5E1' },
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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E2E8F0] pb-5">
        <div>
          <h2 className="text-2xl font-bold text-[#172033] tracking-tight flex items-center gap-2">
            Multi-Agent Orchestration Mesh
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Real-time execution telemetry of all 6 specialist agents, Critic safety gate, and deterministic simulator. Click any node to inspect telemetry.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Live Polling Toggle */}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono font-medium rounded-lg border transition-all ${
              autoRefresh
                ? 'border-emerald-300 bg-emerald-50 text-emerald-800'
                : 'border-[#E2E8F0] bg-white text-slate-600 hover:bg-slate-50'
            }`}
            title="Auto-refresh telemetry every 3 seconds"
          >
            <Radio className={`w-3.5 h-3.5 ${autoRefresh ? 'animate-pulse text-emerald-600' : 'text-slate-400'}`} />
            {autoRefresh ? 'Live Polling Active' : 'Polling Paused'}
          </button>

          <select
            value={incidentId || ''}
            onChange={(e) => onSelectIncident(e.target.value)}
            disabled={loading}
            className="px-3 py-1.5 text-xs font-mono font-semibold rounded-lg border border-[#E2E8F0] bg-white text-slate-800 shadow-xs focus:outline-none focus:ring-1 focus:ring-teal-600 disabled:opacity-50"
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
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-white hover:bg-slate-50 border border-[#E2E8F0] text-slate-700 shadow-xs transition-all disabled:opacity-50"
              title="Manual re-dispatch (Routine incidents execute automatically on submission)"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${executing ? 'animate-spin text-teal-600' : 'text-slate-500'}`} />
              {executing ? 'Running Mesh...' : 'Re-Dispatch'}
            </button>
          )}
        </div>
      </div>

      {/* Case Status Pill */}
      {activeIncident && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-xl border border-[#E2E8F0] bg-white shadow-xs font-mono text-xs gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <span className="font-bold text-teal-800 text-sm">{activeIncident.incident_id}</span>
            <span className="text-slate-500">Status:</span>
            <OperationalStatusBadge status={activeIncident.operational_status} size="sm" />
            {activeIncident.retry_count > 0 && (
              <span className="text-[10px] px-2 py-0.5 rounded-md bg-amber-50 text-amber-800 border border-amber-200 font-semibold">
                Replanning Iteration: {activeIncident.retry_count}/2
              </span>
            )}
            {activeIncident.operational_status === 'AWAITING_HUMAN_REVIEW' && (
              <span className="text-[10px] px-2 py-0.5 rounded-md bg-rose-50 text-rose-800 border border-rose-200 flex items-center gap-1 font-semibold">
                <ShieldAlert className="w-3 h-3 text-rose-600" />
                Human Review Escalated
              </span>
            )}
          </div>
          <div className="text-[11px] text-slate-500">
            Workflows execute autonomously upon citizen submission. Click any node below to inspect live telemetry.
          </div>
        </div>
      )}

      {/* React Flow Container */}
      <div className="w-full h-[560px] rounded-2xl border border-[#E2E8F0] bg-[#F8FAFC] overflow-hidden relative shadow-sm">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodeClick={handleNodeClick}
          fitView
          attributionPosition="bottom-left"
          className="bg-[#F8FAFC]"
        >
          <Background color="#E2E8F0" gap={16} size={1} />
          <Controls className="bg-white border border-[#E2E8F0] shadow-sm rounded-lg overflow-hidden [&>button]:border-b [&>button]:border-[#E2E8F0] [&>button]:bg-white hover:[&>button]:bg-slate-50" />
        </ReactFlow>

        {/* Legend */}
        <div className="absolute top-4 left-4 p-3 rounded-xl bg-white/95 border border-[#E2E8F0] shadow-sm backdrop-blur text-[10px] space-y-1.5 font-mono text-slate-600 pointer-events-none">
          <div className="font-bold text-slate-800 border-b border-[#E2E8F0] pb-1">Orchestration Legend</div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>Completed Execution</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            <span>Critic Rejection / Recovery</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-rose-500" />
            <span>Human Review / Escalated</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-slate-300" />
            <span>Awaiting Upstream Stage</span>
          </div>
        </div>
      </div>

      {/* Telemetry Inspection Drawer Modal */}
      {selectedAgent && (
        <div className="fixed inset-0 z-50 bg-slate-900/30 backdrop-blur-xs flex justify-end">
          <div className="w-full max-w-lg h-full bg-white border-l border-[#E2E8F0] p-6 space-y-6 overflow-y-auto shadow-2xl animate-in slide-in-from-right duration-200">
            <div className="flex justify-between items-start border-b border-[#E2E8F0] pb-4">
              <div>
                <h3 className="text-base font-bold text-[#172033] tracking-tight">{selectedAgent.name}</h3>
                <p className="text-xs text-slate-500 mt-0.5">{selectedAgent.role}</p>
                {selectedAgent.startTime && (
                  <div className="flex items-center gap-2 mt-2 text-[10px] font-mono text-slate-500">
                    <Clock className="w-3 h-3 text-teal-600" />
                    <span>
                      {new Date(selectedAgent.startTime).toLocaleTimeString()} → {selectedAgent.endTime ? new Date(selectedAgent.endTime).toLocaleTimeString() : 'In Progress'}
                    </span>
                  </div>
                )}
              </div>
              <button
                onClick={() => setSelectedAgent(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider font-semibold">Execution Decision</span>
                <p className="text-teal-900 font-semibold mt-1 p-2.5 rounded-lg bg-teal-50 border border-teal-200 font-mono text-xs">
                  {selectedAgent.decision}
                </p>
              </div>

              <div>
                <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider font-semibold">Structured Agent Inputs</span>
                <pre className="mt-1 p-3 rounded-lg bg-slate-50 border border-[#E2E8F0] text-[11px] font-mono text-slate-700 overflow-x-auto max-h-48">
                  {JSON.stringify(selectedAgent.inputs, null, 2)}
                </pre>
              </div>

              <div>
                <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider font-semibold">Structured Agent Outputs</span>
                <pre className="mt-1 p-3 rounded-lg bg-slate-50 border border-[#E2E8F0] text-[11px] font-mono text-slate-700 overflow-x-auto max-h-56">
                  {JSON.stringify(selectedAgent.outputs, null, 2)}
                </pre>
              </div>

              {selectedAgent.events.length > 0 && (
                <div>
                  <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider font-semibold">Chronological Audit Events</span>
                  <div className="mt-2 space-y-2">
                    {selectedAgent.events.map((ev, idx) => (
                      <div key={idx} className="p-2.5 rounded-lg bg-slate-50 border border-[#E2E8F0] space-y-1">
                        <div className="flex justify-between items-center text-[10px] font-mono text-slate-500">
                          <span className="font-semibold text-slate-700">{ev.action}</span>
                          <span>{new Date(ev.timestamp).toLocaleTimeString()}</span>
                        </div>
                        <p className="text-slate-700 text-[11px]">{ev.result}</p>
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
