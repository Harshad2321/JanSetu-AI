import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Filter,
  PlusCircle,
  RefreshCw,
  Search,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import type { DashboardSummary, Incident } from '../../types/api';
import { api } from '../../services/api';
import { OperationalStatusBadge, EvidenceStatusBadge } from '../common/StatusBadge';
import { IncidentMap } from './IncidentMap';

interface DashboardViewProps {
  onSelectIncident: (id: string) => void;
  onNavigateToIntake: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  onSelectIncident,
  onNavigateToIntake,
}) => {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [seeding, setSeeding] = useState<boolean>(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumData, incList] = await Promise.all([
        api.getDashboardSummary(),
        api.getIncidents({ limit: 50 }),
      ]);
      setSummary(sumData);
      setIncidents(incList.items);
    } catch (err: any) {
      setError(err.message || 'Failed to connect to JanSetu backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSeed = async () => {
    setSeeding(true);
    try {
      await api.seedDemonstrationData();
      await loadData();
    } catch (err: any) {
      setError(`Seeding failed: ${err.message}`);
    } finally {
      setSeeding(false);
    }
  };

  // Filtered incidents
  const filteredIncidents = incidents.filter((inc) => {
    const matchesSearch =
      searchTerm === '' ||
      inc.incident_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inc.complaint.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesCategory = categoryFilter === 'all' || inc.category === categoryFilter;
    const matchesStatus = statusFilter === 'all' || inc.operational_status === statusFilter;

    return matchesSearch && matchesCategory && matchesStatus;
  });

  // Calculate KPIs
  const totalCount = summary?.total_incidents || incidents.length;
  const pendingCount = incidents.filter((i) =>
    ['NEW', 'RECORDED_PENDING_REVIEW', 'TRIAGED', 'PLANNING', 'VALIDATING', 'SIMULATING'].includes(
      i.operational_status
    )
  ).length;
  const highPriorityCount = incidents.filter(
    (i) => i.priority?.priority_band === 'Critical' || i.priority?.priority_band === 'High'
  ).length;
  const awaitingCitizenCount = incidents.filter((i) =>
    ['AWAITING_CLARIFICATION', 'AWAITING_EVIDENCE_RETAKE'].includes(i.operational_status)
  ).length;
  const simulatedResolvedCount = incidents.filter(
    (i) => i.operational_status === 'SIMULATED_RESOLVED'
  ).length;

  // Prepare chart data
  const priorityChartData = [
    { name: 'Critical', count: summary?.priority_bands?.['Critical'] || 0, color: '#ef4444' },
    { name: 'High', count: summary?.priority_bands?.['High'] || 0, color: '#f59e0b' },
    { name: 'Medium', count: summary?.priority_bands?.['Medium'] || 0, color: '#2dd4bf' },
    { name: 'Low', count: summary?.priority_bands?.['Low'] || 0, color: '#94a3b8' },
  ];

  const categoryChartData = [
    { name: 'Pothole', count: summary?.categories?.['pothole'] || 0, color: '#38bdf8' },
    { name: 'Waterlogging', count: summary?.categories?.['waterlogging'] || 0, color: '#0ea5e9' },
    { name: 'Garbage', count: summary?.categories?.['garbage'] || 0, color: '#10b981' },
    { name: 'Other', count: summary?.categories?.['uncertain_other'] || 0, color: '#64748b' },
  ];

  if (loading && !summary) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] space-y-4 text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin text-teal-400" />
        <p className="text-sm font-medium">Connecting to JanSetu Command Center...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Top Banner / Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Operations Command Overview
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time municipal telemetry, multimodal intake queue, and agent dispatch pipeline.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadData}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={onNavigateToIntake}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-teal-600 hover:bg-teal-500 text-white shadow-sm shadow-teal-500/20 transition-all"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            New Report
          </button>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl border border-rose-500/40 bg-rose-500/10 text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
          <button
            onClick={loadData}
            className="px-2.5 py-1 text-xs rounded bg-rose-900/50 hover:bg-rose-900 text-white font-medium"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* KPI Cards Row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Total Logged</span>
            <span className="text-[10px] font-mono text-slate-500">POW-ALL</span>
          </div>
          <div className="text-2xl font-bold text-white font-mono">{totalCount}</div>
          <p className="text-[11px] text-slate-500">Municipal incident records</p>
        </div>

        <div className="p-4 rounded-xl border border-teal-500/20 bg-teal-500/5 backdrop-blur-sm space-y-1">
          <div className="flex items-center justify-between text-teal-400 text-xs">
            <span>Active Triage</span>
            <Clock className="w-3.5 h-3.5 text-teal-400" />
          </div>
          <div className="text-2xl font-bold text-teal-300 font-mono">{pendingCount}</div>
          <p className="text-[11px] text-slate-500">Under specialist assessment</p>
        </div>

        <div className="p-4 rounded-xl border border-amber-500/20 bg-amber-500/5 backdrop-blur-sm space-y-1">
          <div className="flex items-center justify-between text-amber-400 text-xs">
            <span>Critical / High</span>
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-300 font-mono">{highPriorityCount}</div>
          <p className="text-[11px] text-slate-500">Arterial / hazardous defects</p>
        </div>

        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Citizen Action</span>
            <AlertCircle className="w-3.5 h-3.5 text-amber-500" />
          </div>
          <div className="text-2xl font-bold text-slate-200 font-mono">{awaitingCitizenCount}</div>
          <p className="text-[11px] text-slate-500">Clarification / retake requested</p>
        </div>

        <div className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 backdrop-blur-sm space-y-1 col-span-2 md:col-span-1">
          <div className="flex items-center justify-between text-emerald-400 text-xs">
            <span>Simulated Done</span>
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-300 font-mono">{simulatedResolvedCount}</div>
          <p className="text-[11px] text-emerald-600 font-medium">[Demo Simulation Only]</p>
        </div>
      </div>

      {/* Visual Analytics Row: Priority & Category Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Priority Breakdown */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-200">Hazard Priority Distribution</h3>
            <span className="text-[11px] text-slate-500 font-mono">Triage Bands</span>
          </div>
          <div className="h-44 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={priorityChartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} allowDecimals={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {priorityChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Category Breakdown */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-200">Incident Category Distribution</h3>
            <span className="text-[11px] text-slate-500 font-mono">Multi-class Triage</span>
          </div>
          <div className="h-44 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={categoryChartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} allowDecimals={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {categoryChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Geospatial Map Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-200">Geospatial Incident Clustering</h3>
            <p className="text-xs text-slate-400">OpenStreetMap pins color-coded by priority tier.</p>
          </div>
          <span className="text-xs font-mono text-slate-500">Haversine Distance Radar</span>
        </div>
        <IncidentMap incidents={incidents} onSelectIncident={onSelectIncident} />
      </div>

      {/* Filterable Incident Registry Table */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <span>Incident Registry</span>
            <span className="text-xs font-normal text-slate-400">({filteredIncidents.length} matching)</span>
          </h3>

          {/* Search and Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                placeholder="Search incident ID, keyword..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8 pr-3 py-1.5 text-xs rounded-lg border border-slate-700 bg-slate-900/90 text-white placeholder-slate-500 focus:outline-none focus:border-teal-500 w-52"
              />
            </div>

            <div className="flex items-center gap-1.5 border border-slate-700 rounded-lg bg-slate-900 px-2 py-1 text-xs">
              <Filter className="w-3 h-3 text-slate-400" />
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="bg-transparent text-slate-300 text-xs focus:outline-none"
              >
                <option value="all">All Categories</option>
                <option value="pothole">Pothole</option>
                <option value="waterlogging">Waterlogging</option>
                <option value="garbage">Garbage</option>
                <option value="uncertain_other">Uncertain / Other</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5 border border-slate-700 rounded-lg bg-slate-900 px-2 py-1 text-xs">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-transparent text-slate-300 text-xs focus:outline-none"
              >
                <option value="all">All Statuses</option>
                <option value="NEW">New</option>
                <option value="RECORDED_PENDING_REVIEW">Pending Review</option>
                <option value="TRIAGED">Triaged</option>
                <option value="AWAITING_CLARIFICATION">Awaiting Clarification</option>
                <option value="SIMULATED_RESOLVED">Simulated Resolved</option>
                <option value="CLOSURE_BLOCKED">Closure Blocked</option>
                <option value="ESCALATED">Escalated</option>
              </select>
            </div>
          </div>
        </div>

        {/* Table / Empty State */}
        {filteredIncidents.length === 0 ? (
          <div className="p-12 text-center rounded-xl border border-dashed border-slate-800 bg-slate-900/30 space-y-3">
            <p className="text-slate-400 text-sm">No incidents match the active filters or query.</p>
            {incidents.length === 0 && (
              <div className="pt-2">
                <button
                  onClick={handleSeed}
                  disabled={seeding}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-teal-600 hover:bg-teal-500 text-white shadow-md shadow-teal-600/20 transition-all disabled:opacity-50"
                >
                  {seeding ? 'Seeding Demonstration Records...' : 'Seed Sample Demonstration Incidents'}
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden shadow-lg">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 uppercase font-mono text-[10px] tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Case ID</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4">Complaint Description</th>
                    <th className="py-3 px-4">Operational Status</th>
                    <th className="py-3 px-4">Photo Evidence</th>
                    <th className="py-3 px-4">Priority</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredIncidents.map((inc) => (
                    <tr
                      key={inc.incident_id}
                      onClick={() => onSelectIncident(inc.incident_id)}
                      className="hover:bg-slate-800/40 transition-colors cursor-pointer group"
                    >
                      <td className="py-3 px-4 font-mono font-bold text-teal-400 group-hover:text-teal-300">
                        {inc.incident_id}
                      </td>
                      <td className="py-3 px-4 capitalize text-slate-300 font-medium">
                        {inc.category.replace('_', ' ')}
                      </td>
                      <td className="py-3 px-4 text-slate-300 max-w-xs truncate" title={inc.complaint}>
                        {inc.complaint}
                      </td>
                      <td className="py-3 px-4">
                        <OperationalStatusBadge status={inc.operational_status} size="sm" />
                      </td>
                      <td className="py-3 px-4">
                        <EvidenceStatusBadge outcome={inc.evidence_status} size="sm" />
                      </td>
                      <td className="py-3 px-4">
                        {inc.priority ? (
                          <div className="flex items-center gap-1.5">
                            <span
                              className={`w-2 h-2 rounded-full ${
                                inc.priority.priority_band === 'Critical'
                                  ? 'bg-rose-500'
                                  : inc.priority.priority_band === 'High'
                                  ? 'bg-amber-500'
                                  : 'bg-teal-400'
                              }`}
                            />
                            <span className="font-mono text-slate-200">
                              {inc.priority.priority_score}
                            </span>
                            <span className="text-[10px] text-slate-500">
                              ({inc.priority.priority_band})
                            </span>
                          </div>
                        ) : (
                          <span className="text-slate-500 text-[11px]">Unscored</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <span className="text-teal-400 hover:text-teal-300 font-semibold group-hover:underline">
                          Open →
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
