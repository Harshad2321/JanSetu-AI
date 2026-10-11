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
  color: string;
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
      color: 'border-emerald-500/40 text-emerald-400',
    },
    {
      id: 'crew_unavailable',
      title: '2. Crew Shortage (Adaptive Recovery)',
      description: 'Primary municipal repair crew is unavailable due to emergency arterial waterlogging dispatch.',
      injectedObstacle: 'crew_unavailable obstacle injected into simulation engine',
      expectedBehavior: 'Simulator fails; Adaptive Recovery activates, assigns standby private contractor crew, passes revised plan back through Critic.',
      badge: 'Crew Shortage',
      color: 'border-amber-500/40 text-amber-400',
    },
    {
      id: 'materials_unavailable',
      title: '3. Material Deficit (Plan Mutation)',
      description: 'Hot-mix asphalt batching plant is offline; supplies unavailable for permanent asphalt repair.',
      injectedObstacle: 'materials_unavailable obstacle injected',
      expectedBehavior: 'Adaptive Recovery substitutes cold-patch asphalt and heavy steel road plates; submits revised mitigation through Critic gate.',
      badge: 'Material Shortage',
      color: 'border-amber-500/40 text-amber-400',
    },
    {
      id: 'critic_rejection',
      title: '4. Critic Safety Rejection & Replan',
      description: 'Resolution plan contains uncertified sealant additive violating municipal safety protocol.',
      injectedObstacle: 'Critic gate rejects plan (REJECT verdict)',
      expectedBehavior: 'Resolution Planning receives exact feedback, amends materials, increments retry counter, and re-submits to Critic.',
      badge: 'Safety Rejection',
      color: 'border-amber-500/40 text-amber-400',
    },
    {
      id: 'insufficient_closure_evidence',
      title: '5. Insufficient Closure Evidence',
      description: 'Physical simulation reports success, but post-intervention compaction density telemetry is missing.',
      injectedObstacle: 'Missing synthetic closure evidence (depth/photo criteria missing)',
      expectedBehavior: 'Deterministic Closure Gate blocks resolution; sets status to CLOSURE_BLOCKED and records exact missing requirements.',
      badge: 'Closure Blocked',
      color: 'border-rose-500/40 text-rose-400',
    },
    {
      id: 'retry_exhaustion',
      title: '6. Retry Ceiling Exhaustion (Escalation)',
      description: 'Repeated intervention failures exceed the bounded retry limit (MAX_PLANNING_RETRIES = 2).',
      injectedObstacle: 'Persistent obstacle across retry ceiling',
      expectedBehavior: 'Workflow halts automated looping; transitions status to ESCALATED with supervisor notification.',
      badge: 'Escalation Flow',
      color: 'border-rose-500/40 text-rose-400',
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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            Failure Simulation & Adaptive Recovery Lab
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Test deterministic failure scenarios to verify that Adaptive Recovery alters remediation plans, passes Critic gates, and blocks closure when evidence is absent.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="text-xs font-mono text-slate-400">Target Incident:</label>
          <select
            value={incidentId || ''}
            onChange={(e) => onSelectIncident(e.target.value)}
            className="px-3 py-1.5 text-xs font-mono font-bold rounded-lg border border-slate-700 bg-slate-900 text-teal-400 focus:outline-none"
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
        <div className="p-3.5 rounded-xl border border-rose-500/40 bg-rose-500/10 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
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
              className={`p-4 rounded-xl border transition-all flex flex-col justify-between ${
                isSelected
                  ? 'border-teal-500 bg-slate-900/90 shadow-lg shadow-teal-500/10'
                  : 'border-slate-800 bg-slate-900/40 hover:border-slate-700'
              }`}
            >
              <div className="space-y-2">
                <div className="flex justify-between items-start">
                  <span className={`text-[10px] font-mono uppercase font-bold px-2 py-0.5 rounded border bg-slate-950 ${sc.color}`}>
                    {sc.badge}
                  </span>
                  {isSelected && (
                    <span className="w-2 h-2 rounded-full bg-teal-400 animate-ping" />
                  )}
                </div>
                <h4 className="text-sm font-bold text-white tracking-tight">{sc.title}</h4>
                <p className="text-xs text-slate-300 leading-relaxed">{sc.description}</p>
                <div className="text-[11px] font-mono text-slate-400 bg-slate-950/80 p-2 rounded-lg border border-slate-800/80">
                  <span className="text-amber-400">Obstacle:</span> {sc.injectedObstacle}
                </div>
              </div>

              <div className="pt-4 mt-2 border-t border-slate-800/80 flex justify-between items-center">
                <span className="text-[10px] font-mono text-slate-500">FastAPI /simulate</span>
                <button
                  onClick={() => handleExecuteScenario(sc.id)}
                  disabled={running || !activeIncident}
                  className="px-3 py-1.5 text-xs font-bold rounded-lg bg-teal-600 hover:bg-teal-500 text-white shadow-sm flex items-center gap-1.5 transition-all disabled:opacity-50"
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
        <div className="p-6 rounded-2xl border border-teal-500/40 bg-slate-900/80 backdrop-blur-md shadow-2xl space-y-6 animate-in zoom-in-95 duration-200">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono uppercase px-2 py-0.5 rounded bg-teal-500/10 text-teal-300 border border-teal-500/30">
                  Simulation Result
                </span>
                <span className="font-mono font-bold text-white text-sm">{lastResult.incident_id}</span>
              </div>
              <p className="text-xs text-slate-400 mt-1">{lastResult.message}</p>
            </div>

            <div className="flex items-center gap-3">
              <OperationalStatusBadge status={lastResult.operational_status} size="lg" />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            {/* 1. Critic Decision */}
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <span className="text-[11px] font-mono text-slate-500 uppercase">Critic Gate Verdict</span>
              <div className="font-bold text-amber-300 text-sm">
                {lastResult.validation?.status || 'NOT APPLIED'}
              </div>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                {lastResult.validation?.feedback || 'Plan satisfied municipal safety protocols.'}
              </p>
            </div>

            {/* 2. Adaptive Plan Revision */}
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <span className="text-[11px] font-mono text-slate-500 uppercase">Adaptive Plan Revision</span>
              <div className="font-semibold text-slate-200">
                {lastResult.current_plan?.is_revised ? (
                  <span className="text-amber-400 flex items-center gap-1">
                    <RotateCcw className="w-3.5 h-3.5" /> Plan Materially Revised
                  </span>
                ) : (
                  <span className="text-slate-400">Initial Strategy Kept</span>
                )}
              </div>
              <p className="text-[11px] text-slate-400">
                {lastResult.current_plan?.allocated_resources?.join(', ') || 'No resources allocated'}
              </p>
            </div>

            {/* 3. Closure Gate Outcome */}
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <span className="text-[11px] font-mono text-slate-500 uppercase">Closure Verification Gate</span>
              <div className="font-bold text-sm">
                {lastResult.is_simulated_resolution ? (
                  <span className="text-emerald-400">SIMULATED_RESOLVED</span>
                ) : lastResult.operational_status === 'CLOSURE_BLOCKED' ? (
                  <span className="text-rose-400">CLOSURE_BLOCKED</span>
                ) : (
                  <span className="text-slate-400">{lastResult.operational_status}</span>
                )}
              </div>
              <p className="text-[11px] text-slate-400">
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
