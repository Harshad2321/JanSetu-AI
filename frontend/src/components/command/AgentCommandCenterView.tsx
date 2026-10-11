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
import { Play, X } from 'lucide-react';
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
  status: 'COMPLETED' | 'RUNNING' | 'FAILED' | 'REJECTED' | 'WAITING' | 'SKIPPED' | 'ESCALATED';
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

  const loadActiveIncident = async (id: string) => {
    setLoading(true);
    try {
      const data = await api.getIncident(id);
      setActiveIncident(data);
    } catch {
      // Ignore
    } finally {
      setLoading(false);
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

  const handleExecuteWorkflow = async () => {
    if (!activeIncident) return;
    setExecuting(true);
    try {
      await api.runWorkflow(activeIncident.incident_id);
      await loadActiveIncident(activeIncident.incident_id);
    } catch {
      // Ignore
    } finally {
      setExecuting(false);
    }
  };

  // Determine node states based on actual incident outputs
  const hasIntel = Boolean(activeIncident?.extracted_facts || activeIncident?.evidence_analysis);
  const hasGeo = Boolean(activeIncident?.geo_context);
  const hasPriority = Boolean(activeIncident?.priority);
  const hasPlan = Boolean(activeIncident?.current_plan);
  const hasCritic = Boolean(activeIncident?.validation);
  const isRecovering = activeIncident?.operational_status === 'RECOVERING' || (activeIncident?.retry_count || 0) > 0;
  const isSimDone = activeIncident?.operational_status === 'SIMULATED_RESOLVED';
  const isClosureBlocked = activeIncident?.operational_status === 'CLOSURE_BLOCKED';
  const isEscalated = activeIncident?.operational_status === 'ESCALATED';

  // React Flow Nodes
  const nodes: Node[] = [
    {
      id: 'intake',
      position: { x: 50, y: 150 },
      data: {
        label: (
          <div className="p-3 text-left">
            <div className="text-[10px] font-mono text-teal-400 font-bold uppercase">Multimodal Gateway</div>
            <div className="text-xs font-bold text-white">1. Incident Intelligence</div>
            <div className="text-[10px] text-slate-400 mt-1">Photo Sanitizer & Groq Vision</div>
            <div className="mt-2 flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${hasIntel ? 'bg-emerald-400' : 'bg-slate-500'}`} />
              <span className="text-[10px] font-mono text-slate-300">
                {hasIntel ? 'Completed' : 'Ready'}
              </span>
            </div>
          </div>
        ),
      },
      style: {
        background: '#090d16',
        borderColor: hasIntel ? '#2dd4bf' : '#334155',
        borderRadius: '12px',
        borderWidth: '1.5px',
        width: 200,
      },
      sourcePosition: Position.Right,
    },
    // Branch A: GeoCivic
    {
      id: 'geocivic',
      position: { x: 310, y: 70 },
      data: {
        label: (
          <div className="p-3 text-left">
            <div className="text-[10px] font-mono text-teal-400 font-bold uppercase">Branch A (Parallel)</div>
            <div className="text-xs font-bold text-white">2. GeoCivic Agent</div>
            <div className="text-[10px] text-slate-400 mt-1">Haversine Distance & Dup Radar</div>
            <div className="mt-2 flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${hasGeo ? 'bg-emerald-400' : 'bg-slate-500'}`} />
              <span className="text-[10px] font-mono text-slate-300">
                {hasGeo ? 'Completed' : 'Waiting'}
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
        width: 190,
      },
      targetPosition: Position.Left,
      sourcePosition: Position.Right,
    },
    // Branch B: Priority Intelligence
    {
      id: 'priority',
      position: { x: 310, y: 230 },
      data: {
        label: (
          <div className="p-3 text-left">
            <div className="text-[10px] font-mono text-teal-400 font-bold uppercase">Branch B (Parallel)</div>
            <div className="text-xs font-bold text-white">3. Priority Intelligence</div>
            <div className="text-[10px] text-slate-400 mt-1">Hazard & Exposure Scoring</div>
            <div className="mt-2 flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${hasPriority ? 'bg-emerald-400' : 'bg-slate-500'}`} />
              <span className="text-[10px] font-mono text-slate-300">
                {hasPriority ? 'Completed' : 'Waiting'}
              </span>
            </div>
          </div>
        ),
      },
      style: {
        background: '#090d16',
        borderColor: hasPriority ? '#2dd4bf' : '#334155',
        borderRadius: '12px',
        borderWidth: '1.5px',
        width: 190,
      },
      targetPosition: Position.Left,
      sourcePosition: Position.Right,
    },
    // Join: Resolution Planning
    {
      id: 'planning',
      position: { x: 560, y: 150 },
      data: {
        label: (
          <div className="p-3 text-left">
            <div className="text-[10px] font-mono text-teal-400 font-bold uppercase">Branch Join</div>
            <div className="text-xs font-bold text-white">4. Resolution Planning</div>
            <div className="text-[10px] text-slate-400 mt-1">Mitigation & Resource Allocation</div>
            <div className="mt-2 flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${hasPlan ? 'bg-emerald-400' : 'bg-slate-500'}`} />
              <span className="text-[10px] font-mono text-slate-300">
                {hasPlan ? 'Plan Formulated' : 'Waiting'}
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
        width: 200,
      },
      targetPosition: Position.Left,
      sourcePosition: Position.Right,
    },
    // Critic & Verification Gate
    {
      id: 'critic',
      position: { x: 810, y: 150 },
      data: {
        label: (
          <div className="p-3 text-left">
            <div className="text-[10px] font-mono text-amber-400 font-bold uppercase">Safety & Feasibility Gate</div>
            <div className="text-xs font-bold text-white">5. Critic & Verification</div>
            <div className="text-[10px] text-slate-400 mt-1">Safety Constraints (Max 2 Retries)</div>
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
        width: 200,
      },
      targetPosition: Position.Left,
      sourcePosition: Position.Right,
    },
    // Adaptive Recovery Agent
    {
      id: 'recovery',
      position: { x: 810, y: 310 },
      data: {
        label: (
          <div className="p-3 text-left">
            <div className="text-[10px] font-mono text-amber-400 font-bold uppercase">Failure Recovery Loop</div>
            <div className="text-xs font-bold text-white">6. Adaptive Recovery</div>
            <div className="text-[10px] text-slate-400 mt-1">Resource / Crew Substitution</div>
            <div className="mt-2 flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  isRecovering ? 'bg-amber-400 animate-pulse' : 'bg-slate-500'
                }`}
              />
              <span className="text-[10px] font-mono text-slate-300">
                {isRecovering ? 'Plan Revised' : 'Idle'}
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
        width: 200,
      },
      targetPosition: Position.Top,
      sourcePosition: Position.Left,
    },
    // Closure Verification Gate
    {
      id: 'closure',
      position: { x: 1060, y: 150 },
      data: {
        label: (
          <div className="p-3 text-left">
            <div className="text-[10px] font-mono text-emerald-400 font-bold uppercase">Deterministic Gate</div>
            <div className="text-xs font-bold text-white">Closure Verification</div>
            <div className="text-[10px] text-slate-400 mt-1">Requires Synthetic Proof</div>
            <div className="mt-2 flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  isSimDone
                    ? 'bg-emerald-400'
                    : isClosureBlocked
                    ? 'bg-rose-500'
                    : isEscalated
                    ? 'bg-rose-500'
                    : 'bg-slate-500'
                }`}
              />
              <span className="text-[10px] font-mono text-slate-300">
                {isSimDone ? 'Simulated Resolved' : isClosureBlocked ? 'Closure Blocked' : 'Waiting'}
              </span>
            </div>
          </div>
        ),
      },
      style: {
        background: '#090d16',
        borderColor: isSimDone ? '#10b981' : isClosureBlocked ? '#f43f5e' : '#334155',
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
      id: 'e-critic-closure',
      source: 'critic',
      target: 'closure',
      animated: isSimDone,
      style: { stroke: isSimDone ? '#10b981' : '#475569', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: isSimDone ? '#10b981' : '#475569' },
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
        role: 'Multimodal vision and complaint fact extraction with EXIF sanitation.',
        status: hasIntel ? 'COMPLETED' : 'WAITING',
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
        name: 'GeoCivic Agent',
        role: 'Geospatial duplicate detection using Haversine formula against municipal registry.',
        status: hasGeo ? 'COMPLETED' : 'WAITING',
        inputs: { location: activeIncident.location },
        outputs: { geo_context: activeIncident.geo_context },
        decision: activeIncident.geo_context?.is_duplicate ? 'Potential Duplicate Flagged' : 'Unique Incident Confirmed',
        events: activeIncident.audit_timeline.filter((e) => e.agent.includes('GeoCivic')),
      });
    } else if (node.id === 'priority') {
      setSelectedAgent({
        name: 'Priority Intelligence Agent',
        role: 'Hazard severity and public exposure evaluation (0-100 score).',
        status: hasPriority ? 'COMPLETED' : 'WAITING',
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
        name: 'Resolution Planning Agent',
        role: 'Formulates domain remediation plan, resource allocation, and closure criteria.',
        status: hasPlan ? 'COMPLETED' : 'WAITING',
        inputs: {
          geo_context: activeIncident.geo_context,
          priority: activeIncident.priority,
        },
        outputs: { current_plan: activeIncident.current_plan },
        decision: activeIncident.current_plan?.is_revised ? 'Adaptive Plan Revision Applied' : 'Standard Remediation Plan Formulated',
        events: activeIncident.audit_timeline.filter((e) => e.agent.includes('Resolution') || e.agent.includes('Planning')),
      });
    } else if (node.id === 'critic') {
      setSelectedAgent({
        name: 'Critic and Verification Agent',
        role: 'Validates safety constraints and resource availability with bounded retries.',
        status: activeIncident.validation?.status === 'APPROVE' ? 'COMPLETED' : activeIncident.validation ? 'REJECTED' : 'WAITING',
        inputs: { plan: activeIncident.current_plan, retry_count: activeIncident.retry_count },
        outputs: { validation: activeIncident.validation },
        decision: `Critic Verdict: ${activeIncident.validation?.status || 'Pending'} — ${activeIncident.validation?.feedback || ''}`,
        events: activeIncident.audit_timeline.filter((e) => e.agent.includes('Critic')),
      });
    } else if (node.id === 'recovery') {
      setSelectedAgent({
        name: 'Adaptive Recovery Agent',
        role: 'Revises remediation plans when simulated obstacles (crew/materials shortage) occur.',
        status: isRecovering ? 'COMPLETED' : 'WAITING',
        inputs: {
          failure_reason: activeIncident.failure_reason,
          retry_count: activeIncident.retry_count,
        },
        outputs: { current_plan: activeIncident.current_plan },
        decision: activeIncident.failure_reason ? `Handled Obstacle: ${activeIncident.failure_reason}` : 'No recovery required.',
        events: activeIncident.audit_timeline.filter((e) => e.agent.includes('Recovery') || e.action.includes('Recovery')),
      });
    } else if (node.id === 'closure') {
      setSelectedAgent({
        name: 'Deterministic Closure Verification Gate',
        role: 'Ensures no incident is marked resolved without explicit synthetic completion evidence.',
        status: isSimDone ? 'COMPLETED' : isClosureBlocked ? 'FAILED' : 'WAITING',
        inputs: {
          closure_evidence: activeIncident.closure_evidence,
          simulation_result: activeIncident.simulation_result,
        },
        outputs: {
          closure_evidence: activeIncident.closure_evidence,
          operational_status: activeIncident.operational_status,
        },
        decision: isSimDone ? 'SIMULATED_RESOLVED [Explicit Simulation Marker]' : isClosureBlocked ? 'CLOSURE_BLOCKED: Evidence Incomplete' : 'Awaiting Gate Execution',
        events: activeIncident.audit_timeline.filter((e) => e.agent.includes('Closure')),
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
            Real-time execution telemetry of the 6 specialist agents and deterministic workflow gates. Click any node to inspect telemetry.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
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
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg bg-teal-600 hover:bg-teal-500 text-white shadow-sm transition-all disabled:opacity-50"
            >
              <Play className={`w-3.5 h-3.5 fill-current ${executing ? 'animate-spin' : ''}`} />
              {executing ? 'Running Mesh...' : 'Dispatch Mesh'}
            </button>
          )}
        </div>
      </div>

      {/* Case Status Pill */}
      {activeIncident && (
        <div className="flex items-center justify-between p-3 rounded-xl border border-slate-800 bg-slate-900/60 font-mono text-xs">
          <div className="flex items-center gap-3">
            <span className="font-bold text-teal-400">{activeIncident.incident_id}</span>
            <span className="text-slate-400">Status:</span>
            <OperationalStatusBadge status={activeIncident.operational_status} size="sm" />
          </div>
          <div className="text-[11px] text-slate-500">
            Click on any agent node below to inspect real input and output state.
          </div>
        </div>
      )}

      {/* React Flow Container */}
      <div className="w-full h-[540px] rounded-2xl border border-slate-800 bg-slate-950 overflow-hidden relative shadow-2xl">
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
            <span className="w-2 h-2 rounded-full bg-slate-500" />
            <span>Awaiting Upstream Branch</span>
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
                <p className="text-teal-300 font-semibold mt-1 p-2.5 rounded-lg bg-slate-950 border border-slate-800">
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
