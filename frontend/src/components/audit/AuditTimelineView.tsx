import React, { useState, useEffect } from 'react';
import { Download, Filter, RefreshCw, Search } from 'lucide-react';
import type { Incident, AuditEvent } from '../../types/api';
import { api } from '../../services/api';

interface AuditTimelineViewProps {
  incidentId: string | null;
  onSelectIncident: (id: string) => void;
}

export const AuditTimelineView: React.FC<AuditTimelineViewProps> = ({
  incidentId,
  onSelectIncident,
}) => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [activeEvents, setActiveEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [agentFilter, setAgentFilter] = useState<string>('all');

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

  const loadAuditHistory = async (id: string) => {
    setLoading(true);
    try {
      const events = await api.getAudit(id);
      setActiveEvents(events);
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
      loadAuditHistory(incidentId);
    }
  }, [incidentId]);

  // Filter events
  const filteredEvents = activeEvents.filter((ev) => {
    const matchesSearch =
      searchTerm === '' ||
      ev.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
      ev.result.toLowerCase().includes(searchTerm.toLowerCase()) ||
      ev.agent.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesAgent = agentFilter === 'all' || ev.agent.toLowerCase().includes(agentFilter.toLowerCase());

    return matchesSearch && matchesAgent;
  });

  function getAgentProvenance(agentName: string) {
    if (agentName.includes('Groq') || agentName.includes('Incident Intelligence')) {
      return { tag: 'Multimodal Vision / Groq', color: 'border-teal-200 text-teal-800 bg-teal-50' };
    }
    if (agentName.includes('GeoCivic')) {
      return { tag: 'Haversine Engine', color: 'border-sky-200 text-sky-800 bg-sky-50' };
    }
    if (agentName.includes('Critic')) {
      return { tag: 'Safety Validation Rules', color: 'border-amber-200 text-amber-800 bg-amber-50' };
    }
    if (agentName.includes('Simulation') || agentName.includes('Closure')) {
      return { tag: 'Deterministic Simulation Gate', color: 'border-emerald-200 text-emerald-800 bg-emerald-50' };
    }
    if (agentName.includes('Recovery')) {
      return { tag: 'Adaptive Recovery Loop', color: 'border-amber-200 text-amber-800 bg-amber-50' };
    }
    return { tag: 'Intake Rule Evaluator', color: 'border-slate-200 text-slate-600 bg-slate-100' };
  }

  const handleExportJSON = () => {
    if (!incidentId || activeEvents.length === 0) return;
    const blob = new Blob([JSON.stringify(activeEvents, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit_${incidentId}_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportCSV = () => {
    if (!incidentId || activeEvents.length === 0) return;
    const headers = ['timestamp', 'agent', 'action', 'result', 'correlation_id'];
    const rows = activeEvents.map((e) => [
      `"${e.timestamp}"`,
      `"${e.agent.replace(/"/g, '""')}"`,
      `"${e.action.replace(/"/g, '""')}"`,
      `"${e.result.replace(/"/g, '""')}"`,
      `"${(e.correlation_id || '').replace(/"/g, '""')}"`,
    ]);
    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit_${incidentId}_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E2E8F0] pb-5">
        <div>
          <h2 className="text-2xl font-bold text-[#172033] tracking-tight flex items-center gap-2">
            Chronological Audit & Evaluation Trail
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Immutable, privacy-compliant event trail detailing each agent decision, gate evaluation, and recovery action.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
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
          {incidentId && (
            <button
              onClick={() => loadAuditHistory(incidentId)}
              className="p-1.5 rounded-lg border border-[#E2E8F0] bg-white text-slate-500 hover:text-slate-800 hover:bg-slate-50 shadow-xs transition-colors"
              title="Refresh audit"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-teal-600' : ''}`} />
            </button>
          )}

          {activeEvents.length > 0 && (
            <div className="flex items-center gap-1.5 pl-2 border-l border-[#E2E8F0]">
              <button
                onClick={handleExportJSON}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-mono font-medium rounded-lg border border-[#E2E8F0] bg-white hover:bg-slate-50 text-slate-700 shadow-xs transition-colors"
                title="Download JSON audit log"
              >
                <Download className="w-3 h-3 text-teal-700" />
                JSON
              </button>
              <button
                onClick={handleExportCSV}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-mono font-medium rounded-lg border border-[#E2E8F0] bg-white hover:bg-slate-50 text-slate-700 shadow-xs transition-colors"
                title="Download CSV audit log"
              >
                <Download className="w-3 h-3 text-emerald-700" />
                CSV
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Filters row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-xl border border-[#E2E8F0] bg-white shadow-xs text-xs">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search audit action or result..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-[#E2E8F0] bg-slate-50/50 text-[#172033] placeholder-slate-400 focus:outline-none focus:bg-white focus:border-teal-600 focus:ring-1 focus:ring-teal-600 transition-all"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <select
            value={agentFilter}
            onChange={(e) => setAgentFilter(e.target.value)}
            className="px-2.5 py-1.5 rounded-lg border border-[#E2E8F0] bg-white text-slate-700 shadow-xs focus:outline-none focus:ring-1 focus:ring-teal-600"
          >
            <option value="all">All Agents & Gates</option>
            <option value="Intake">Intake Portal</option>
            <option value="Incident">Incident Intelligence</option>
            <option value="GeoCivic">GeoCivic</option>
            <option value="Priority">Priority Intelligence</option>
            <option value="Resolution">Resolution Planning</option>
            <option value="Critic">Critic Gate</option>
            <option value="Simulation">Simulation Lab</option>
            <option value="Closure">Closure Verification</option>
            <option value="Recovery">Adaptive Recovery</option>
          </select>
        </div>
      </div>

      {/* Timeline List */}
      {filteredEvents.length === 0 ? (
        <div className="p-12 text-center rounded-xl border border-dashed border-[#E2E8F0] bg-white text-slate-500 text-xs shadow-xs">
          No audit events found for this incident record.
        </div>
      ) : (
        <div className="relative pl-6 space-y-5 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-200">
          {filteredEvents.map((ev, index) => {
            const prov = getAgentProvenance(ev.agent);
            return (
              <div key={index} className="relative group">
                {/* Timeline Dot */}
                <div className="absolute -left-6 top-2 w-3 h-3 rounded-full border-2 border-white bg-teal-600 shadow-xs ring-4 ring-teal-50" />

                <div className="p-4 rounded-xl border border-[#E2E8F0] bg-white hover:border-slate-300 shadow-xs transition-colors space-y-2">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 border-b border-[#E2E8F0] pb-2.5">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-[#172033] text-xs">{ev.agent}</span>
                      <span className="text-slate-300">•</span>
                      <span className="font-semibold text-teal-800 text-xs">{ev.action}</span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${prov.color}`}>
                        {prov.tag}
                      </span>
                      <span className="text-[11px] font-mono text-slate-400">
                        {new Date(ev.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>

                  <p className="text-xs text-slate-700 leading-relaxed font-mono">
                    {ev.result}
                  </p>

                  {ev.correlation_id && (
                    <div className="pt-1.5 flex items-center gap-1.5 text-[10px] font-mono text-slate-400">
                      <span>Trace Correlation ID:</span>
                      <code className="px-1.5 py-0.5 rounded bg-slate-100 text-teal-800 border border-slate-200 font-semibold">
                        {ev.correlation_id}
                      </code>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
