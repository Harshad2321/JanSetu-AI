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
  CartesianGrid,
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

  // Prepare chart data with semantic colors
  const priorityChartData = [
    { name: 'Critical', count: summary?.priority_bands?.['Critical'] || 0, color: '#DC2626' },
    { name: 'High', count: summary?.priority_bands?.['High'] || 0, color: '#EA580C' },
    { name: 'Medium', count: summary?.priority_bands?.['Medium'] || 0, color: '#D97706' },
    { name: 'Low', count: summary?.priority_bands?.['Low'] || 0, color: '#16A34A' },
  ];

  const categoryChartData = [
    { name: 'Pothole', count: summary?.categories?.['pothole'] || 0, color: '#0284C7' },
    { name: 'Waterlogging', count: summary?.categories?.['waterlogging'] || 0, color: '#2563EB' },
    { name: 'Garbage', count: summary?.categories?.['garbage'] || 0, color: '#059669' },
    { name: 'Other', count: summary?.categories?.['uncertain_other'] || 0, color: '#64748B' },
  ];

  if (loading && !summary) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[480px] space-y-3 text-[#64748B]">
        <RefreshCw className="w-8 h-8 animate-spin text-[#0F766E]" />
        <p className="text-sm font-medium text-[#172033]">Connecting to JanSetu Command Center...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Top Banner / Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E2E8F0] pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#172033] flex items-center gap-2">
            Operations Command Overview
          </h1>
          <p className="text-xs text-[#64748B] mt-1 font-normal">
            Real-time municipal telemetry, multimodal intake queue, and agent dispatch pipeline.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={loadData}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium rounded-lg border border-[#E2E8F0] bg-white text-[#172033] hover:bg-slate-50 transition-colors shadow-2xs cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-[#0F766E]' : 'text-[#64748B]'}`} />
            Refresh
          </button>
          <button
            onClick={onNavigateToIntake}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-[#0F766E] hover:bg-[#115E59] text-white shadow-xs transition-all cursor-pointer"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            New Report
          </button>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl border border-rose-200 bg-rose-50 text-rose-800 text-xs flex items-center justify-between shadow-2xs">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
            <span className="font-medium">{error}</span>
          </div>
          <button
            onClick={loadData}
            className="px-3 py-1 text-xs rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-medium shadow-xs"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* KPI Cards Row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {/* Card 1: Total Logged */}
        <div className="p-4 rounded-xl border border-[#E2E8F0] bg-white shadow-sm space-y-1.5 transition-all hover:shadow-md">
          <div className="flex items-center justify-between text-[#64748B] text-xs">
            <span className="font-medium">Total Logged</span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-[#64748B]">POW-ALL</span>
          </div>
          <div className="text-2xl font-bold text-[#172033] font-mono tracking-tight">{totalCount}</div>
          <p className="text-[11px] text-[#64748B]">Municipal incident records</p>
        </div>

        {/* Card 2: Active Triage */}
        <div className="p-4 rounded-xl border border-[#E2E8F0] bg-white shadow-sm space-y-1.5 transition-all hover:shadow-md">
          <div className="flex items-center justify-between text-[#64748B] text-xs">
            <span className="font-medium">Active Triage</span>
            <Clock className="w-3.5 h-3.5 text-[#0F766E]" />
          </div>
          <div className="text-2xl font-bold text-[#0F766E] font-mono tracking-tight">{pendingCount}</div>
          <p className="text-[11px] text-[#64748B]">Under specialist assessment</p>
        </div>

        {/* Card 3: Critical / High */}
        <div className="p-4 rounded-xl border border-[#E2E8F0] bg-white shadow-sm space-y-1.5 transition-all hover:shadow-md">
          <div className="flex items-center justify-between text-[#64748B] text-xs">
            <span className="font-medium">Critical / High</span>
            <AlertTriangle className="w-3.5 h-3.5 text-[#EA580C]" />
          </div>
          <div className="text-2xl font-bold text-[#EA580C] font-mono tracking-tight">{highPriorityCount}</div>
          <p className="text-[11px] text-[#64748B]">Arterial / hazardous defects</p>
        </div>

        {/* Card 4: Citizen Action */}
        <div className="p-4 rounded-xl border border-[#E2E8F0] bg-white shadow-sm space-y-1.5 transition-all hover:shadow-md">
          <div className="flex items-center justify-between text-[#64748B] text-xs">
            <span className="font-medium">Citizen Action</span>
            <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
          </div>
          <div className="text-2xl font-bold text-[#172033] font-mono tracking-tight">{awaitingCitizenCount}</div>
          <p className="text-[11px] text-[#64748B]">Clarification / retake requested</p>
        </div>

        {/* Card 5: Simulated Done */}
        <div className="p-4 rounded-xl border border-[#E2E8F0] bg-white shadow-sm space-y-1.5 col-span-2 md:col-span-1 transition-all hover:shadow-md">
          <div className="flex items-center justify-between text-[#64748B] text-xs">
            <span className="font-medium">Simulated Done</span>
            <CheckCircle2 className="w-3.5 h-3.5 text-[#0F766E]" />
          </div>
          <div className="text-2xl font-bold text-[#0F766E] font-mono tracking-tight">{simulatedResolvedCount}</div>
          <p className="text-[11px] text-[#0F766E] font-medium">[Demo Simulation Only]</p>
        </div>
      </div>

      {/* Visual Analytics Row: Priority & Category Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Priority Breakdown */}
        <div className="p-5 rounded-xl border border-[#E2E8F0] bg-white shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-3">
            <h3 className="text-sm font-semibold text-[#172033]">Hazard Priority Distribution</h3>
            <span className="text-[11px] text-[#64748B] font-mono">Triage Bands</span>
          </div>
          <div className="h-48 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={priorityChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E9EEF5" />
                <XAxis dataKey="name" stroke="#64748B" fontSize={11} tickLine={false} axisLine={{ stroke: '#E2E8F0' }} />
                <YAxis stroke="#64748B" fontSize={11} allowDecimals={false} tickLine={false} axisLine={{ stroke: '#E2E8F0' }} />
                <Tooltip
                  cursor={{ fill: 'rgba(241, 245, 249, 0.6)' }}
                  contentStyle={{
                    backgroundColor: '#FFFFFF',
                    borderColor: '#E2E8F0',
                    borderRadius: '8px',
                    boxShadow: '0 4px 12px rgba(15, 23, 42, 0.08)',
                    fontSize: '12px',
                    color: '#172033',
                  }}
                  itemStyle={{ color: '#172033', fontWeight: 600 }}
                  labelStyle={{ color: '#64748B', fontWeight: 500 }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={48}>
                  {priorityChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Category Breakdown */}
        <div className="p-5 rounded-xl border border-[#E2E8F0] bg-white shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-3">
            <h3 className="text-sm font-semibold text-[#172033]">Incident Category Distribution</h3>
            <span className="text-[11px] text-[#64748B] font-mono">Multi-class Triage</span>
          </div>
          <div className="h-48 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={categoryChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E9EEF5" />
                <XAxis dataKey="name" stroke="#64748B" fontSize={11} tickLine={false} axisLine={{ stroke: '#E2E8F0' }} />
                <YAxis stroke="#64748B" fontSize={11} allowDecimals={false} tickLine={false} axisLine={{ stroke: '#E2E8F0' }} />
                <Tooltip
                  cursor={{ fill: 'rgba(241, 245, 249, 0.6)' }}
                  contentStyle={{
                    backgroundColor: '#FFFFFF',
                    borderColor: '#E2E8F0',
                    borderRadius: '8px',
                    boxShadow: '0 4px 12px rgba(15, 23, 42, 0.08)',
                    fontSize: '12px',
                    color: '#172033',
                  }}
                  itemStyle={{ color: '#172033', fontWeight: 600 }}
                  labelStyle={{ color: '#64748B', fontWeight: 500 }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={48}>
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
      <div className="p-5 rounded-xl border border-[#E2E8F0] bg-white shadow-sm space-y-3">
        <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-3">
          <div>
            <h3 className="text-sm font-semibold text-[#172033]">Geospatial Incident Clustering</h3>
            <p className="text-xs text-[#64748B] mt-0.5">OpenStreetMap pins color-coded by priority tier.</p>
          </div>
          <span className="text-xs font-mono text-[#64748B]">Haversine Distance Radar</span>
        </div>
        <IncidentMap incidents={incidents} onSelectIncident={onSelectIncident} />
      </div>

      {/* Filterable Incident Registry Table */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <h3 className="text-sm font-semibold text-[#172033] flex items-center gap-2">
            <span>Incident Registry</span>
            <span className="text-xs font-normal text-[#64748B]">({filteredIncidents.length} matching)</span>
          </h3>

          {/* Search and Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
              <input
                type="text"
                placeholder="Search incident ID, keyword..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8 pr-3 py-1.5 text-xs rounded-lg border border-[#E2E8F0] bg-white text-[#172033] placeholder-[#94A3B8] focus:outline-none focus:border-[#0F766E] focus:ring-1 focus:ring-[#0F766E] w-56 shadow-2xs"
              />
            </div>

            <div className="flex items-center gap-1.5 border border-[#E2E8F0] rounded-lg bg-white px-2.5 py-1 text-xs shadow-2xs">
              <Filter className="w-3 h-3 text-[#64748B]" />
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="bg-transparent text-[#172033] text-xs focus:outline-none cursor-pointer"
              >
                <option value="all">All Categories</option>
                <option value="pothole">Pothole</option>
                <option value="waterlogging">Waterlogging</option>
                <option value="garbage">Garbage</option>
                <option value="uncertain_other">Uncertain / Other</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5 border border-[#E2E8F0] rounded-lg bg-white px-2.5 py-1 text-xs shadow-2xs">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-transparent text-[#172033] text-xs focus:outline-none cursor-pointer"
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
          <div className="p-12 text-center rounded-xl border border-dashed border-[#E2E8F0] bg-white shadow-2xs space-y-3">
            <p className="text-[#64748B] text-sm">
              {incidents.length === 0
                ? 'No civic incidents recorded in the database yet. The system is ready to receive citizen reports.'
                : 'No incidents match the active filters or search query.'}
            </p>
            {incidents.length === 0 && (
              <div className="pt-2">
                <button
                  onClick={onNavigateToIntake}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-[#0F766E] hover:bg-[#115E59] text-white shadow-xs transition-all cursor-pointer"
                >
                  + Report New Incident
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="rounded-xl border border-[#E2E8F0] bg-white overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#F8FAFC] text-[#64748B] border-b border-[#E2E8F0] uppercase font-mono text-[10px] tracking-wider font-semibold">
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
                <tbody className="divide-y divide-[#E2E8F0]">
                  {filteredIncidents.map((inc) => (
                    <tr
                      key={inc.incident_id}
                      onClick={() => onSelectIncident(inc.incident_id)}
                      className="hover:bg-slate-50/80 transition-colors cursor-pointer group"
                    >
                      <td className="py-3.5 px-4 font-mono font-bold text-[#0F766E] group-hover:underline">
                        {inc.incident_id}
                      </td>
                      <td className="py-3.5 px-4 capitalize text-[#172033] font-medium">
                        {inc.category.replace('_', ' ')}
                      </td>
                      <td className="py-3.5 px-4 text-[#64748B] max-w-xs truncate" title={inc.complaint}>
                        {inc.complaint}
                      </td>
                      <td className="py-3.5 px-4">
                        <OperationalStatusBadge status={inc.operational_status} size="sm" />
                      </td>
                      <td className="py-3.5 px-4">
                        <EvidenceStatusBadge outcome={inc.evidence_status} size="sm" />
                      </td>
                      <td className="py-3.5 px-4">
                        {inc.priority ? (
                          <div className="flex items-center gap-1.5">
                            <span
                              className={`w-2 h-2 rounded-full ${
                                inc.priority.priority_band === 'Critical'
                                  ? 'bg-[#DC2626]'
                                  : inc.priority.priority_band === 'High'
                                  ? 'bg-[#EA580C]'
                                  : 'bg-[#0F766E]'
                              }`}
                            />
                            <span className="font-mono text-[#172033] font-semibold">
                              {inc.priority.priority_score}
                            </span>
                            <span className="text-[10px] text-[#64748B]">
                              ({inc.priority.priority_band})
                            </span>
                          </div>
                        ) : (
                          <span className="text-[#94A3B8] text-[11px]">Unscored</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <span className="text-[#0F766E] hover:text-[#115E59] font-semibold group-hover:underline">
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
