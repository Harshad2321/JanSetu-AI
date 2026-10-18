import React, { useState, useEffect } from 'react';
import { AlertCircle, Play, RotateCcw } from 'lucide-react';
import type { Incident, SupportedScenario, WorkflowRunResponse } from '../../types/api';
import { api } from '../../services/api';
import { OperationalStatusBadge } from '../common/StatusBadge';

interface SimulationLabViewProps {
  incidentId: string | null;
  onSelectIncident: (id: string) => void;
}

interface ScenarioCard {
  id: SupportedScenario;
  title: string;
  description: string;
  injectedObstacle: string;
  expectedBehavior: string;
  badge: string;
  badgeStyle: string;
}

export const SimulationLabView: React.FC<SimulationLabViewProps> = ({
  incidentId,
  onSelectIncident,
}) => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [activeIncident, setActiveIncident] = useState<Incident | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<SupportedScenario>('crew_unavailable');
  const [running, setRunning] = useState<boolean>(false);
  const [lastResult, setLastResult] = useState<WorkflowRunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const scenarioCards: ScenarioCard[] = [
    {
      id: 'normal',
      title: '1. Normal Simulated Execution',
      description: 'Ideal field intervention with available crews, verified asphalt compaction, and photographic closure evidence.',
      injectedObstacle: 'None (nominal operational flow)',
      expectedBehavior: 'Proceeds through planning and Critic gate; intervention succeeds; passes closure gate -> SIMULATED_RESOLVED.',
      badge: 'Success Flow',
      badgeStyle: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    },
    {
      id: 'crew_unavailable',
      title: '2. Crew Shortage (Adaptive Recovery)',
      description: 'Primary municipal repair crew is unavailable due to emergency arterial waterlogging dispatch.',
      injectedObstacle: 'crew_unavailable obstacle injected into simulation engine',
      expectedBehavior: 'Simulator fails; Adaptive Recovery activates, assigns standby private contractor crew, passes revised plan back through Critic.',
      badge: 'Crew Shortage',
      badgeStyle: 'bg-amber-50 text-amber-800 border-amber-200',
    },
    {
      id: 'materials_unavailable',
      title: '3. Material Deficit (Plan Mutation)',
      description: 'Hot-mix asphalt batching plant is offline; supplies unavailable for permanent asphalt repair.',
      injectedObstacle: 'materials_unavailable obstacle injected',
      expectedBehavior: 'Adaptive Recovery substitutes cold-patch asphalt and heavy steel road plates; submits revised mitigation through Critic gate.',
      badge: 'Material Shortage',
      badgeStyle: 'bg-amber-50 text-amber-800 border-amber-200',
    },
    {
      id: 'critic_rejection',
      title: '4. Critic Safety Rejection & Replan',
      description: 'Resolution plan contains uncertified sealant additive violating municipal safety protocol.',
      injectedObstacle: 'Critic gate rejects plan (REJECT verdict)',
      expectedBehavior: 'Resolution Planning receives exact feedback, amends materials, increments retry counter, and re-submits to Critic.',
      badge: 'Safety Rejection',
      badgeStyle: 'bg-amber-50 text-amber-800 border-amber-200',
    },
    {
      id: 'insufficient_closure_evidence',
      title: '5. Insufficient Closure Evidence',
      description: 'Physical simulation reports success, but post-intervention compaction density telemetry is missing.',
      injectedObstacle: 'Missing synthetic closure evidence (depth/photo criteria missing)',
      expectedBehavior: 'Deterministic Closure Gate blocks resolution; sets status to CLOSURE_BLOCKED and records exact missing requirements.',
      badge: 'Closure Blocked',
      badgeStyle: 'bg-rose-50 text-rose-800 border-rose-200',
    },
    {
      id: 'retry_exhaustion',
      title: '6. Retry Ceiling Exhaustion (Escalation)',
      description: 'Repeated intervention failures exceed the bounded retry limit (MAX_PLANNING_RETRIES = 2).',
      injectedObstacle: 'Persistent obstacle across retry ceiling',
      expectedBehavior: 'Workflow halts automated looping; transitions status to ESCALATED with supervisor notification.',
      badge: 'Escalation Flow',
      badgeStyle: 'bg-rose-50 text-rose-800 border-rose-200',
    },
  ];

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
    try {
      const data = await api.getIncident(id);
      setActiveIncident(data);
    } catch {
      // Ignore
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

  const handleExecuteScenario = async (scenario: SupportedScenario) => {
    if (!activeIncident) return;
    setSelectedScenario(scenario);
    setRunning(true);
    setError(null);
    setLastResult(null);

    try {
      const result = await api.simulateScenario(activeIncident.incident_id, scenario);
      setLastResult(result);
      await loadActiveIncident(activeIncident.incident_id);
    } catch (err: any) {
      setError(err.message || 'Scenario execution failed.');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E2E8F0] pb-5">
        <div>
          <h2 className="text-2xl font-bold text-[#172033] tracking-tight flex items-center gap-2">
            Failure Simulation & Adaptive Recovery Lab
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Test deterministic failure scenarios to verify that Adaptive Recovery alters remediation plans, passes Critic gates, and blocks closure when evidence is absent.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <label className="text-xs font-mono font-medium text-slate-500">Target Incident:</label>
          <select
            value={incidentId || ''}
            onChange={(e) => onSelectIncident(e.target.value)}
            className="px-3 py-1.5 text-xs font-mono font-semibold rounded-lg border border-[#E2E8F0] bg-white text-slate-800 shadow-xs focus:outline-none focus:ring-1 focus:ring-teal-600"
          >
            {incidents.map((inc) => (
              <option key={inc.incident_id} value={inc.incident_id}>
                {inc.incident_id} ({inc.operational_status})
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl border border-rose-200 bg-rose-50 text-rose-800 text-xs flex items-center gap-2 shadow-xs">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Scenarios Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {scenarioCards.map((sc) => {
          const isSelected = selectedScenario === sc.id;
          return (
            <div
              key={sc.id}
              className={`p-5 rounded-xl border transition-all flex flex-col justify-between ${
                isSelected
                  ? 'border-teal-600 bg-teal-50/20 shadow-md ring-1 ring-teal-600/30'
                  : 'border-[#E2E8F0] bg-white hover:border-slate-300 shadow-xs'
              }`}
            >
              <div className="space-y-2.5">
                <div className="flex justify-between items-start">
                  <span className={`text-[10px] font-mono uppercase font-semibold px-2 py-0.5 rounded border ${sc.badgeStyle}`}>
                    {sc.badge}
                  </span>
                  {isSelected && (
                    <span className="w-2 h-2 rounded-full bg-teal-600 animate-ping" />
                  )}
                </div>
                <h4 className="text-sm font-bold text-[#172033] tracking-tight">{sc.title}</h4>
                <p className="text-xs text-slate-600 leading-relaxed">{sc.description}</p>
                <div className="text-[11px] font-mono text-slate-700 bg-slate-50 p-2.5 rounded-lg border border-[#E2E8F0]">
                  <span className="text-amber-700 font-semibold">Obstacle:</span> {sc.injectedObstacle}
                </div>
              </div>

              <div className="pt-4 mt-3 border-t border-[#E2E8F0] flex justify-between items-center">
                <span className="text-[10px] font-mono text-slate-400">FastAPI /simulate</span>
                <button
                  onClick={() => handleExecuteScenario(sc.id)}
                  disabled={running || !activeIncident}
                  className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-teal-700 hover:bg-teal-800 text-white shadow-xs flex items-center gap-1.5 transition-all disabled:opacity-50"
                >
                  <Play className={`w-3 h-3 fill-current ${running && isSelected ? 'animate-spin' : ''}`} />
                  {running && isSelected ? 'Executing...' : 'Trigger'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Execution Results Inspection Panel */}
      {lastResult && (
        <div className="p-6 rounded-2xl border border-teal-200 bg-white shadow-md space-y-6 animate-in zoom-in-95 duration-200">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E2E8F0] pb-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-semibold uppercase px-2 py-0.5 rounded bg-teal-50 text-teal-800 border border-teal-200">
                  Simulation Result
                </span>
                <span className="font-mono font-bold text-[#172033] text-sm">{lastResult.incident_id}</span>
              </div>
              <p className="text-xs text-slate-500 mt-1">{lastResult.message}</p>
            </div>

            <div className="flex items-center gap-3">
              <OperationalStatusBadge status={lastResult.operational_status} size="lg" />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            {/* 1. Critic Decision */}
            <div className="p-4 rounded-xl bg-slate-50 border border-[#E2E8F0] space-y-2">
              <span className="text-[11px] font-mono text-slate-500 uppercase font-semibold">Critic Gate Verdict</span>
              <div className="font-bold text-amber-800 text-sm">
                {lastResult.validation?.status || 'NOT APPLIED'}
              </div>
              <p className="text-slate-600 text-[11px] leading-relaxed">
                {lastResult.validation?.feedback || 'Plan satisfied municipal safety protocols.'}
              </p>
            </div>

            {/* 2. Adaptive Plan Revision */}
            <div className="p-4 rounded-xl bg-slate-50 border border-[#E2E8F0] space-y-2">
              <span className="text-[11px] font-mono text-slate-500 uppercase font-semibold">Adaptive Plan Revision</span>
              <div className="font-semibold text-slate-800">
                {lastResult.current_plan?.is_revised ? (
                  <span className="text-amber-800 flex items-center gap-1">
                    <RotateCcw className="w-3.5 h-3.5 text-amber-600" /> Plan Materially Revised
                  </span>
                ) : (
                  <span className="text-slate-600">Initial Strategy Kept</span>
                )}
              </div>
              <p className="text-[11px] text-slate-500">
                {lastResult.current_plan?.allocated_resources?.join(', ') || 'No resources allocated'}
              </p>
            </div>

            {/* 3. Closure Gate Outcome */}
            <div className="p-4 rounded-xl bg-slate-50 border border-[#E2E8F0] space-y-2">
              <span className="text-[11px] font-mono text-slate-500 uppercase font-semibold">Closure Verification Gate</span>
              <div className="font-bold text-sm">
                {lastResult.is_simulated_resolution ? (
                  <span className="text-emerald-700">SIMULATED_RESOLVED</span>
                ) : lastResult.operational_status === 'CLOSURE_BLOCKED' ? (
                  <span className="text-rose-700">CLOSURE_BLOCKED</span>
                ) : (
                  <span className="text-slate-700">{lastResult.operational_status}</span>
                )}
              </div>
              <p className="text-[11px] text-slate-600">
                {lastResult.closure_evidence?.is_ready_for_closure
                  ? 'All synthetic closure criteria verified fulfilled.'
                  : 'Closure barred: required completion evidence is missing.'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
