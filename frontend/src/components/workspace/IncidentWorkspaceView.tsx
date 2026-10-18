import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  FileText,
  MapPin,
  Play,
  RefreshCw,
  ShieldCheck,
  Wrench,
  XCircle,
} from 'lucide-react';
import type { Incident, SupportedScenario, WorkflowRunResponse, CivicIncidentTwin } from '../../types/api';
import { api } from '../../services/api';
import { OperationalStatusBadge, EvidenceStatusBadge } from '../common/StatusBadge';

interface IncidentWorkspaceViewProps {
  incidentId: string | null;
  onSelectIncident: (id: string) => void;
  onOpenCommandCenter: (id: string) => void;
}

export const IncidentWorkspaceView: React.FC<IncidentWorkspaceViewProps> = ({
  incidentId,
  onSelectIncident,
  onOpenCommandCenter,
}) => {
  const [incident, setIncident] = useState<Incident | null>(null);
  const [twin, setTwin] = useState<CivicIncidentTwin | null>(null);
  const [allIncidents, setAllIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [executing, setExecuting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<SupportedScenario>('normal');
  const [scenarioNotice, setScenarioNotice] = useState<string | null>(null);

  const loadIncidentList = async () => {
    try {
      const res = await api.getIncidents({ limit: 50 });
      setAllIncidents(res.items);
      if (!incidentId && res.items.length > 0) {
        onSelectIncident(res.items[0].incident_id);
      }
    } catch {
      // Ignore
    }
  };

  const loadIncident = async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const [data, twinData] = await Promise.all([
        api.getIncident(id),
        api.getIncidentTwin(id).catch(() => null),
      ]);
      setIncident(data);
      setTwin(twinData);
    } catch (err: any) {
      setError(err.message || 'Failed to load incident detail.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIncidentList();
  }, []);

  useEffect(() => {
    if (incidentId) {
      loadIncident(incidentId);
    }
  }, [incidentId]);

  // Background auto-refresh polling every 3.5s
  useEffect(() => {
    if (!incidentId) return;
    const interval = setInterval(() => {
      Promise.all([
        api.getIncident(incidentId),
        api.getIncidentTwin(incidentId).catch(() => null),
      ])
        .then(([data, twinData]) => {
          setIncident(data);
          if (twinData) setTwin(twinData);
        })
        .catch(() => {});
    }, 3500);
    return () => clearInterval(interval);
  }, [incidentId]);

  const handleRunWorkflow = async () => {
    if (!incident) return;
    setExecuting(true);
    setError(null);
    setScenarioNotice(null);
    try {
      const res: WorkflowRunResponse = await api.runWorkflow(incident.incident_id);
      setScenarioNotice(`Workflow executed. Status updated to ${res.operational_status}.`);
      await loadIncident(incident.incident_id);
    } catch (err: any) {
      setError(`Workflow run failed: ${err.message}`);
    } finally {
      setExecuting(false);
    }
  };

  const handleRunScenario = async () => {
    if (!incident) return;
    setExecuting(true);
    setError(null);
    setScenarioNotice(null);
    try {
      const res: WorkflowRunResponse = await api.simulateScenario(incident.incident_id, selectedScenario);
      setScenarioNotice(`Simulation scenario '${selectedScenario}' executed. Operational Status: ${res.operational_status}.`);
      await loadIncident(incident.incident_id);
    } catch (err: any) {
      setError(`Scenario execution failed: ${err.message}`);
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Autonomous Orchestration Notice */}
      <div className="p-3.5 rounded-xl border border-teal-200 bg-teal-50 text-teal-900 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-2xs">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-[#0F766E] shrink-0" />
          <span>
            <strong className="text-[#0F766E]">Autonomous Multi-Agent Pipeline Active:</strong> Citizen reports automatically trigger Incident Intelligence, GeoCivic duplicate checks, Priority scoring, Response planning, Critic gate, Deterministic simulation, and Closure verification.
          </span>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-teal-100 text-[#0F766E] border border-teal-200 font-semibold shrink-0">
          Zero-Click Automation
        </span>
      </div>

      {/* Top Selector & Controls Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-xl border border-[#E2E8F0] bg-white shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-xs font-semibold text-[#64748B]">Active Case Record:</label>
          <select
            value={incidentId || ''}
            onChange={(e) => onSelectIncident(e.target.value)}
            className="px-3 py-1.5 text-xs font-mono font-bold rounded-lg border border-[#E2E8F0] bg-white text-[#0F766E] focus:outline-none focus:border-[#0F766E] shadow-2xs cursor-pointer"
          >
            {allIncidents.map((inc) => (
              <option key={inc.incident_id} value={inc.incident_id}>
                {inc.incident_id} — {inc.category.toUpperCase()} ({inc.operational_status})
              </option>
            ))}
          </select>
          {incident && (
            <button
              onClick={() => loadIncident(incident.incident_id)}
              className="p-1.5 rounded-lg border border-[#E2E8F0] bg-white text-[#64748B] hover:text-[#172033] hover:bg-slate-50 transition-colors shadow-2xs cursor-pointer"
              title="Refresh case"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-[#0F766E]' : ''}`} />
            </button>
          )}
        </div>

        {incident && (
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => onOpenCommandCenter(incident.incident_id)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-[#E2E8F0] bg-white hover:bg-slate-50 text-[#172033] shadow-2xs transition-colors cursor-pointer"
            >
              <Cpu className="w-3.5 h-3.5 text-[#0F766E]" />
              View Agent Telemetry
            </button>

            {/* Diagnostics re-run button */}
            <button
              onClick={handleRunWorkflow}
              disabled={executing}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-[#E2E8F0] bg-white hover:bg-slate-50 text-[#172033] shadow-2xs transition-all disabled:opacity-50 cursor-pointer"
              title="Re-run pipeline for diagnostic testing"
            >
              <Play className={`w-3.5 h-3.5 fill-current ${executing ? 'animate-spin text-[#0F766E]' : ''}`} />
              {executing ? 'Executing...' : 'Re-run (Diagnostics)'}
            </button>

            {/* Scenario Quick Selector (Simulation Lab Testing) */}
            <div className="flex items-center gap-1 border border-[#E2E8F0] rounded-lg bg-[#F8FAFC] p-0.5 shadow-2xs" title="Simulation Lab Scenario Injector">
              <span className="text-[10px] font-mono text-amber-700 font-semibold pl-1.5 hidden sm:inline">Lab:</span>
              <select
                value={selectedScenario}
                onChange={(e) => setSelectedScenario(e.target.value as SupportedScenario)}
                className="bg-transparent text-[11px] font-mono text-[#172033] px-2 py-1 focus:outline-none cursor-pointer"
              >
                <option value="normal">Normal (Pass)</option>
                <option value="crew_unavailable">Crew Shortage</option>
                <option value="materials_unavailable">Material Deficit</option>
                <option value="critic_rejection">Critic Rejection</option>
                <option value="insufficient_closure_evidence">Closure Block</option>
                <option value="retry_exhaustion">Exhaust Retries</option>
              </select>
              <button
                onClick={handleRunScenario}
                disabled={executing}
                className="px-2.5 py-1 text-[11px] font-bold rounded bg-amber-600 hover:bg-amber-700 text-white disabled:opacity-50 shadow-2xs cursor-pointer"
              >
                Simulate
              </button>
            </div>
          </div>
        )}
      </div>

      {scenarioNotice && (
        <div className="p-3 rounded-lg border border-teal-200 bg-teal-50 text-teal-900 text-xs font-medium flex items-center justify-between shadow-2xs">
          <span>{scenarioNotice}</span>
          <button onClick={() => setScenarioNotice(null)} className="text-[#0F766E] font-bold cursor-pointer">×</button>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl border border-rose-200 bg-rose-50 text-rose-800 text-xs flex items-center gap-2 shadow-2xs">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span className="font-medium">{error}</span>
        </div>
      )}

      {!incident ? (
        <div className="p-16 text-center rounded-xl border border-dashed border-[#E2E8F0] bg-white text-[#94A3B8] text-xs shadow-2xs">
          Select an incident from the registry above to view its active case file.
        </div>
      ) : (
        <div className="space-y-6">
          {/* Header Summary Card with Dual Badges */}
          <div className="p-5 rounded-xl border border-[#E2E8F0] bg-white shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E2E8F0] pb-4">
              <div>
                <div className="flex items-center gap-2.5">
                  <span className="text-lg font-bold font-mono text-[#0F766E]">{incident.incident_id}</span>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-[#172033] capitalize border border-[#E2E8F0]">
                    {incident.category.replace('_', ' ')}
                  </span>
                  {incident.retry_count > 0 && (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200 font-semibold">
                      Retry {incident.retry_count}/2
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-[#64748B] mt-1 font-mono">
                  Recorded: {new Date(incident.created_at).toLocaleString()} • Last Synchronized: {new Date(incident.updated_at).toLocaleString()}
                </div>
              </div>

              {/* Explicit Dual-Status Presentation */}
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <div className="text-[10px] uppercase tracking-wider text-[#64748B] font-mono font-medium">Operational Lifecycle</div>
                  <OperationalStatusBadge status={incident.operational_status} size="md" />
                </div>
                <div className="h-8 w-px bg-[#E2E8F0]" />
                <div className="text-right">
                  <div className="text-[10px] uppercase tracking-wider text-[#64748B] font-mono font-medium">Evidence Outcome</div>
                  <EvidenceStatusBadge outcome={incident.evidence_status} size="md" />
                </div>
              </div>
            </div>

            {/* Complaint Text */}
            <div className="space-y-1">
              <span className="text-[11px] uppercase tracking-wider font-semibold text-[#64748B] font-mono">
                Citizen Complaint Statement
              </span>
              <p className="text-xs text-[#172033] leading-relaxed bg-[#F8FAFC] p-3.5 rounded-lg border border-[#E2E8F0]">
                {incident.complaint}
              </p>
            </div>

            {/* Location Metadata Bar */}
            <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-[#64748B] pt-1">
              <div className="flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-[#0F766E]" />
                <span className="text-[#172033]">
                  {incident.location?.latitude
                    ? `${incident.location.latitude.toFixed(5)}° N, ${incident.location.longitude?.toFixed(5)}° E`
                    : 'Coordinates not provided'}
                </span>
              </div>
              {incident.location?.accuracy_meters !== null && incident.location?.accuracy_meters !== undefined && (
                <span>Accuracy: ±{Math.round(incident.location.accuracy_meters)}m</span>
              )}
              <span className="px-2 py-0.5 rounded-full bg-slate-100 text-[10px] text-[#64748B] border border-[#E2E8F0]">
                Source: {incident.location?.source || 'MANUAL'}
              </span>
              {incident.location?.is_user_confirmed && (
                <span className="text-[#0F766E] text-[11px] flex items-center gap-1 font-semibold">
                  ✓ Citizen Confirmed Pin
                </span>
              )}
            </div>
          </div>

          {/* Grid: 2 Columns of Specialist Outputs */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 1. Incident Intelligence Extraction */}
            <div className="p-5 rounded-xl border border-[#E2E8F0] bg-white shadow-sm space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-[#0F766E] font-mono flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Incident Intelligence Extraction
              </h3>

              {incident.extracted_facts ? (
                <div className="space-y-3 text-xs">
                  <div>
                    <span className="text-[#64748B] font-mono">Primary Defect:</span>
                    <p className="text-[#172033] font-semibold mt-0.5">{incident.extracted_facts.primary_defect}</p>
                  </div>
                  <div>
                    <span className="text-[#64748B] font-mono">Severity Indicators:</span>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {(incident.extracted_facts.severity_indicators || []).map((s, idx) => (
                        <span key={idx} className="px-2 py-0.5 rounded-full bg-rose-50 text-rose-800 border border-rose-200 text-[11px] font-medium">
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <span className="text-[#64748B] font-mono">Public Exposure:</span>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {(incident.extracted_facts.public_exposure_clues || []).map((c, idx) => (
                        <span key={idx} className="px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200 text-[11px] font-medium">
                          {c}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="text-[11px] text-[#64748B] pt-1 font-mono">
                    Extraction Confidence: {((incident.extracted_facts.confidence_score ?? 0.8) * 100).toFixed(0)}%
                  </div>
                </div>
              ) : (
                <p className="text-xs text-[#94A3B8] italic">No structured facts extracted yet. Run the workflow.</p>
              )}
            </div>

            {/* 2. GeoCivic Spatial Duplicate Radar */}
            <div className="p-5 rounded-xl border border-[#E2E8F0] bg-white shadow-sm space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-[#0F766E] font-mono flex items-center gap-2">
                <MapPin className="w-4 h-4" />
                GeoCivic Spatial Duplicate Detection
              </h3>

              {incident.geo_context ? (
                <div className="space-y-3 text-xs">
                  <div className="flex justify-between items-center">
                    <span className="text-[#64748B] font-mono">Duplicate Status:</span>
                    <span className={`font-semibold ${incident.geo_context.is_duplicate ? 'text-purple-700' : 'text-[#172033]'}`}>
                      {incident.geo_context.is_duplicate ? 'Potential Duplicate Flagged' : 'Unique Civic Incident'}
                    </span>
                  </div>

                  {incident.geo_context.distance_to_nearest_meters !== null && incident.geo_context.distance_to_nearest_meters !== undefined && (
                    <div className="flex justify-between items-center">
                      <span className="text-[#64748B] font-mono">Distance to Nearest Incident:</span>
                      <span className="font-mono text-[#172033] font-semibold">
                        {incident.geo_context.distance_to_nearest_meters.toFixed(1)} meters
                      </span>
                    </div>
                  )}

                  {incident.geo_context.duplicate_candidates && incident.geo_context.duplicate_candidates.length > 0 && (
                    <div className="space-y-2 pt-1">
                      <span className="text-[#64748B] font-mono text-[11px]">Nearby Synthetic Incident Matches:</span>
                      {incident.geo_context.duplicate_candidates.map((cand, idx) => (
                        <div key={idx} className="p-2.5 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] space-y-1">
                          <div className="flex justify-between items-center font-mono">
                            <span className="font-bold text-[#0F766E]">{cand.incident_id}</span>
                            <span className="text-amber-700 font-semibold">{cand.distance_meters.toFixed(1)}m away</span>
                          </div>
                          <p className="text-[11px] text-[#64748B]">{cand.rationale}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {incident.geo_context.spatial_uncertainty_explanation && (
                    <p className="text-[11px] text-[#64748B] italic">
                      {incident.geo_context.spatial_uncertainty_explanation}
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-xs text-[#94A3B8] italic">No geospatial analysis computed yet.</p>
              )}
            </div>

            {/* 3. Priority Intelligence Assessment */}
            <div className="p-5 rounded-xl border border-[#E2E8F0] bg-white shadow-sm space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-[#0F766E] font-mono flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                Priority Intelligence Assessment
              </h3>

              {incident.priority ? (
                <div className="space-y-3 text-xs">
                  <div className="flex justify-between items-center">
                    <span className="text-[#64748B] font-mono">Triage Score:</span>
                    <span className="text-xl font-bold font-mono text-[#EA580C]">
                      {incident.priority.priority_score} / 100
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[#64748B] font-mono">Assigned Band:</span>
                    <span className="font-semibold text-[#172033]">
                      {incident.priority.priority_band}
                    </span>
                  </div>
                  <div>
                    <span className="text-[#64748B] font-mono">Triage Explanation:</span>
                    <p className="text-[#172033] mt-1 leading-relaxed">{incident.priority.explanation}</p>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-[#94A3B8] italic">Priority assessment pending workflow triage.</p>
              )}
            </div>

            {/* 4. Critic & Verification Gate */}
            <div className="p-5 rounded-xl border border-[#E2E8F0] bg-white shadow-sm space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-[#0F766E] font-mono flex items-center gap-2">
                <ShieldCheck className="w-4 h-4" />
                Critic & Safety Verification Gate
              </h3>

              {incident.validation ? (
                <div className="space-y-3 text-xs">
                  <div className="flex justify-between items-center">
                    <span className="text-[#64748B] font-mono">Gate Verdict:</span>
                    <span
                      className={`font-bold px-2 py-0.5 rounded-full text-[11px] ${
                        incident.validation.status === 'APPROVE'
                          ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                          : incident.validation.status === 'REJECT'
                          ? 'bg-amber-50 text-amber-800 border border-amber-200'
                          : 'bg-rose-50 text-rose-800 border border-rose-200'
                      }`}
                    >
                      {incident.validation.status}
                    </span>
                  </div>
                  <div>
                    <span className="text-[#64748B] font-mono">Critic Feedback:</span>
                    <p className="text-[#172033] mt-1 leading-relaxed">{incident.validation.feedback}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
                    <div className="flex items-center gap-1.5">
                      {incident.validation.safety_check_passed ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <XCircle className="w-3.5 h-3.5 text-rose-600" />
                      )}
                      <span className="text-[#64748B]">Safety Criteria</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      {incident.validation.resource_check_passed ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <XCircle className="w-3.5 h-3.5 text-rose-600" />
                      )}
                      <span className="text-[#64748B]">Resource Feasibility</span>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-[#94A3B8] italic">Critic verification will run after plan formulation.</p>
              )}
            </div>
          </div>

          {/* Full-width Resolution Plan Card */}
          <div className="p-5 rounded-xl border border-[#E2E8F0] bg-white shadow-sm space-y-4">
            <div className="flex justify-between items-center border-b border-[#E2E8F0] pb-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-[#0F766E] font-mono flex items-center gap-2">
                <Wrench className="w-4 h-4" />
                Actionable Remediation Plan
              </h3>
              {incident.current_plan?.is_revised && (
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
                  Adaptive Recovery Plan Revision
                </span>
              )}
            </div>

            {incident.current_plan ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
                {/* Left: Mitigation & Permanent Repair */}
                <div className="space-y-3">
                  <div>
                    <span className="text-[#64748B] font-semibold font-mono text-[11px]">
                      {((incident.current_plan as any).actions?.length > 0) ? "Planned Actions:" : "Immediate Mitigation Steps:"}
                    </span>
                    <ul className="list-disc list-inside mt-1.5 space-y-1 text-[#172033]">
                      {(((incident.current_plan as any).actions) || (incident.current_plan as any).mitigation_steps || []).map((m: string, idx: number) => (
                        <li key={idx}>{m}</li>
                      ))}
                    </ul>
                  </div>
                  {((incident.current_plan as any).permanent_repair_steps?.length > 0) && (
                    <div>
                      <span className="text-[#64748B] font-semibold font-mono text-[11px]">Permanent Remediation:</span>
                      <ul className="list-disc list-inside mt-1.5 space-y-1 text-[#172033]">
                        {((incident.current_plan as any).permanent_repair_steps || []).map((r: string, idx: number) => (
                          <li key={idx}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {/* Right: Resources, Roles & Measurable Closure Criteria */}
                <div className="space-y-3">
                  <div>
                    <span className="text-[#64748B] font-semibold font-mono text-[11px]">Allocated Resources:</span>
                    <div className="flex flex-wrap gap-1.5 mt-1.5">
                      {(((incident.current_plan as any).required_resources) || ((incident.current_plan as any).resource_requirements) || ((incident.current_plan as any).allocated_resources) || ((incident.current_plan as any).resources) || []).map((res: string, idx: number) => (
                        <span key={idx} className="px-2 py-0.5 rounded-full bg-slate-100 text-[#172033] text-[11px] border border-[#E2E8F0]">
                          {res}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <span className="text-[#64748B] font-semibold font-mono text-[11px]">Deterministic Closure Criteria:</span>
                    <ul className="list-disc list-inside mt-1.5 space-y-1 text-[#172033]">
                      {((incident.current_plan as any).closure_criteria || []).map((c: string, idx: number) => (
                        <li key={idx}>{c}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-xs text-[#94A3B8] italic">No remediation plan formulated yet.</p>
            )}
          </div>

          {/* Closure Evidence Gate Card */}
          <div className="p-5 rounded-xl border border-[#E2E8F0] bg-white shadow-sm space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[#0F766E] font-mono flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              Closure Evidence Verification Status
            </h3>

            {incident.closure_evidence ? (
              <div className="space-y-3 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-[#64748B] font-mono">Closure Authorization:</span>
                  <span
                    className={`font-bold px-2 py-0.5 rounded-full text-[11px] ${
                      incident.closure_evidence.is_ready_for_closure
                        ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                        : 'bg-rose-50 text-rose-800 border border-rose-200'
                    }`}
                  >
                    {incident.closure_evidence.is_ready_for_closure ? 'READY FOR CLOSURE' : 'CLOSURE BARRED'}
                  </span>
                </div>
                <div>
                  <span className="text-[#64748B] font-mono text-[11px]">Criteria Verified Fulfilled:</span>
                  <ul className="list-disc list-inside mt-1 space-y-0.5 text-emerald-700 font-medium">
                    {(incident.closure_evidence.closure_criteria_met || []).map((met, idx) => (
                      <li key={idx}>{met}</li>
                    ))}
                  </ul>
                </div>
                {(incident.closure_evidence.outstanding_criteria || []).length > 0 && (
                  <div>
                    <span className="text-[#64748B] font-mono text-[11px]">Outstanding Criteria:</span>
                    <ul className="list-disc list-inside mt-1 space-y-0.5 text-rose-700 font-medium">
                      {(incident.closure_evidence.outstanding_criteria || []).map((unmet, idx) => (
                        <li key={idx}>{unmet}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {incident.closure_evidence.inspector_notes && (
                  <p className="text-[11px] text-[#64748B] italic">
                    Inspector Telemetry: {incident.closure_evidence.inspector_notes}
                  </p>
                )}
              </div>
            ) : (
              <p className="text-xs text-[#94A3B8] italic">
                Closure verification pending simulated field execution and completion evidence.
              </p>
            )}
          </div>

          {/* Civic Incident Twin Historical Records */}
          {twin && (
            <div className="p-5 rounded-xl border border-teal-200 bg-white shadow-sm space-y-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#E2E8F0] pb-3">
                <div className="flex items-center gap-2">
                  <Cpu className="w-5 h-5 text-[#0F766E]" />
                  <h3 className="text-sm font-bold text-[#172033] tracking-tight">
                    Civic Incident Twin — Historical Digital Record
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-teal-50 text-[#0F766E] border border-teal-200 font-bold">
                    SYNTHETIC ACADEMIC POC
                  </span>
                </div>
              </div>

              {/* Version-Preserved Response Plans */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold uppercase text-[#172033]">
                    Preserved Response Plans ({twin.plans?.length || 0} versions)
                  </span>
                  <span className="text-[11px] font-mono text-[#64748B]">Dual-Track: Permanent & Relief</span>
                </div>

                {twin.plans && twin.plans.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {twin.plans.map((p, idx) => (
                      <div key={idx} className="p-3.5 rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] space-y-2 text-xs shadow-2xs">
                        <div className="flex items-center justify-between font-mono">
                          <span className="font-bold text-[#0F766E]">{p.plan_id}</span>
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-white text-[#64748B] border border-[#E2E8F0]">
                            Version {p.version} • {p.plan_type}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] font-mono text-[#64748B] block font-semibold">Actions:</span>
                          <ul className="list-disc list-inside space-y-0.5 text-[#172033] text-[11px] mt-0.5">
                            {(p.actions || []).map((act, aIdx) => (
                              <li key={aIdx}>{act}</li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <span className="text-[10px] font-mono text-[#64748B] block font-semibold">Closure Criteria:</span>
                          <ul className="list-disc list-inside space-y-0.5 text-[#64748B] text-[10px] mt-0.5">
                            {(p.closure_criteria || []).map((crit, cIdx) => (
                              <li key={cIdx}>{crit}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-[#94A3B8] italic">No historical plans recorded yet.</p>
                )}
              </div>

              {/* Simulated Execution Attempts (Invariant 2) */}
              <div className="space-y-3 pt-3 border-t border-[#E2E8F0]">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold uppercase text-[#172033]">
                    Simulated Execution Log ({twin.execution_attempts?.length || 0} attempts)
                  </span>
                  <span className="text-[10px] font-mono text-amber-700 font-semibold">simulated=True (Invariant 2)</span>
                </div>

                {twin.execution_attempts && twin.execution_attempts.length > 0 ? (
                  <div className="space-y-2">
                    {(twin.execution_attempts || []).map((att, idx) => (
                      <div key={idx} className="p-3 rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-2xs">
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-2 font-mono">
                            <span className="font-bold text-[#172033]">{att.attempt_id}</span>
                            <span className={`text-[10px] font-bold px-2 py-0.2 rounded-full ${
                              att.outcome === 'SUCCESS' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-rose-50 text-rose-800 border border-rose-200'
                            }`}>
                              {att.outcome}
                            </span>
                          </div>
                          {att.failure_reason && (
                            <p className="text-[11px] text-rose-700 font-mono">Reason: {att.failure_reason}</p>
                          )}
                        </div>
                        <span className="text-[10px] font-mono text-[#64748B]">
                          {new Date((att as any).attempted_at || att.timestamp || Date.now()).toLocaleTimeString()}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-[#94A3B8] italic">No execution attempts simulated yet.</p>
                )}
              </div>

              {/* Independent Verification Outcomes (Invariant 1) */}
              <div className="space-y-3 pt-3 border-t border-[#E2E8F0]">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold uppercase text-[#172033]">
                    Independent Verification Records ({twin.verification_results?.length || 0} audits)
                  </span>
                  <span className="text-[10px] font-mono text-emerald-700 font-semibold">Invariant 1 Gate</span>
                </div>

                {twin.verification_results && twin.verification_results.length > 0 ? (
                  <div className="space-y-2">
                    {(twin.verification_results || []).map((v, idx) => (
                      <div key={idx} className="p-3 rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] text-xs space-y-1.5 shadow-2xs">
                        <div className="flex items-center justify-between font-mono">
                          <span className="font-bold text-[#0F766E]">{v.verification_id}</span>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                            v.passed ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-rose-50 text-rose-800 border border-rose-200'
                          }`}>
                            {v.passed ? 'VERIFICATION PASSED' : 'VERIFICATION FAILED'}
                          </span>
                        </div>
                        <div className="text-[11px] text-[#64748B]">
                          Criteria Satisfied: {v.criteria_met?.length || 0} • Unmet: {v.unmet_criteria?.length || 0}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-[#94A3B8] italic">No independent verification records present.</p>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
