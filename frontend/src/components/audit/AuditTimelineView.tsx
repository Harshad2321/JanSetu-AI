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
      return { tag: 'Multimodal Vision / Groq', color: 'border-teal-500/40 text-teal-300 bg-teal-500/10' };
    }
    if (agentName.includes('GeoCivic')) {
      return { tag: 'Haversine Engine', color: 'border-sky-500/40 text-sky-300 bg-sky-500/10' };
    }
    if (agentName.includes('Critic')) {
      return { tag: 'Safety Validation Rules', color: 'border-amber-500/40 text-amber-300 bg-amber-500/10' };
    }
    if (agentName.includes('Simulation') || agentName.includes('Closure')) {
      return { tag: 'Deterministic Simulation Gate', color: 'border-emerald-500/40 text-emerald-300 bg-emerald-500/10' };
    }
    if (agentName.includes('Recovery')) {
      return { tag: 'Adaptive Recovery Loop', color: 'border-amber-500/40 text-amber-300 bg-amber-500/10' };
    }
    return { tag: 'Intake Rule Evaluator', color: 'border-slate-700 text-slate-400 bg-slate-800' };
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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            Chronological Audit & Evaluation Trail
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Immutable, privacy-compliant event trail detailing each agent decision, gate evaluation, and recovery action.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
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
          {incidentId && (
            <button
              onClick={() => loadAuditHistory(incidentId)}
              className="p-1.5 rounded-lg border border-slate-700 bg-slate-900 text-slate-400 hover:text-white"
              title="Refresh audit"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          )}

          {activeEvents.length > 0 && (
            <div className="flex items-center gap-1.5 pl-2 border-l border-slate-800">
              <button
                onClick={handleExportJSON}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-mono rounded-lg border border-slate-700 bg-slate-900 hover:bg-slate-800 text-slate-300 transition-colors"
                title="Download JSON audit log"
              >
                <Download className="w-3 h-3 text-teal-400" />
                JSON
              </button>
              <button
                onClick={handleExportCSV}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-mono rounded-lg border border-slate-700 bg-slate-900 hover:bg-slate-800 text-slate-300 transition-colors"
                title="Download CSV audit log"
              >
                <Download className="w-3 h-3 text-emerald-400" />
                CSV
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Filters row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-xl border border-slate-800 bg-slate-900/60 text-xs">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search audit action or result..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-slate-700 bg-slate-950 text-white placeholder-slate-500 focus:outline-none focus:border-teal-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-500" />
          <select
            value={agentFilter}
            onChange={(e) => setAgentFilter(e.target.value)}
            className="px-2.5 py-1.5 rounded-lg border border-slate-700 bg-slate-950 text-slate-300 focus:outline-none"
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
        <div className="p-12 text-center rounded-xl border border-dashed border-slate-800 bg-slate-900/20 text-slate-500 text-xs">
          No audit events found for this incident record.
        </div>
      ) : (
        <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-800">
          {filteredEvents.map((ev, index) => {
            const prov = getAgentProvenance(ev.agent);
            return (
              <div key={index} className="relative group">
                {/* Timeline Dot */}
                <div className="absolute -left-6 top-1.5 w-3 h-3 rounded-full border-2 border-slate-950 bg-teal-400 shadow-sm shadow-teal-400/50" />

                <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 hover:border-slate-700 transition-colors space-y-2">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 border-b border-slate-800/80 pb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-200 text-xs">{ev.agent}</span>
                      <span className="text-slate-500">•</span>
                      <span className="font-semibold text-teal-300 text-xs">{ev.action}</span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${prov.color}`}>
                        {prov.tag}
                      </span>
                      <span className="text-[11px] font-mono text-slate-500">
                        {new Date(ev.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed font-mono">
                    {ev.result}
                  </p>

                  {ev.correlation_id && (
                    <div className="pt-1 flex items-center gap-1.5 text-[10px] font-mono text-slate-500">
                      <span>Trace Correlation ID:</span>
                      <code className="px-1.5 py-0.5 rounded bg-slate-950 text-teal-400 border border-slate-800">
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

