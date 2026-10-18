import React, { useState, useEffect } from 'react';
import {
  AlertCircle,
  ExternalLink,
  Eye,
  MapPin,
  RefreshCw,
  Search,
} from 'lucide-react';
import { api } from '../../services/api';
import type { Incident } from '../../types/api';
import { OperationalStatusBadge, EvidenceStatusBadge } from '../common/StatusBadge';

interface IncidentExplorerViewProps {
  onSelectIncident: (id: string) => void;
  onOpenCommandCenter: (id: string) => void;
  onNavigateToIntake: () => void;
}

export const IncidentExplorerView: React.FC<IncidentExplorerViewProps> = ({
  onSelectIncident,
  onOpenCommandCenter,
  onNavigateToIntake,
}) => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [selectedEvidence, setSelectedEvidence] = useState<string>('all');

  const [selectedForPreview, setSelectedForPreview] = useState<Incident | null>(null);

  const loadIncidents = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getIncidents({ limit: 100 });
      setIncidents(res.items);
      if (res.items.length > 0 && !selectedForPreview) {
        setSelectedForPreview(res.items[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load incident records from backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIncidents();
  }, []);

  const filtered = incidents.filter((inc) => {
    const matchesSearch =
      searchTerm === '' ||
      inc.incident_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inc.complaint.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (inc.location?.address_text && inc.location.address_text.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesCat = selectedCategory === 'all' || inc.category === selectedCategory;
    const matchesStat = selectedStatus === 'all' || inc.operational_status === selectedStatus;
    const matchesEv = selectedEvidence === 'all' || inc.evidence_status === selectedEvidence;

    return matchesSearch && matchesCat && matchesStat && matchesEv;
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E2E8F0] pb-5">
        <div>
          <h1 className="text-2xl font-bold text-[#172033] tracking-tight flex items-center gap-2">
            <Search className="w-6 h-6 text-[#0F766E]" />
            Civic Incident Explorer
          </h1>
          <p className="text-xs text-[#64748B] mt-1">
            Search, filter, and inspect registered municipal incidents, unconfirmed duplicate candidates, and geo-spatial coordinates.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={loadIncidents}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium rounded-lg border border-[#E2E8F0] bg-white hover:bg-slate-50 text-[#172033] transition-colors disabled:opacity-50 shadow-2xs cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-[#0F766E]' : 'text-[#64748B]'}`} />
            Refresh Registry
          </button>
          <button
            onClick={onNavigateToIntake}
            className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-[#0F766E] hover:bg-[#115E59] text-white shadow-xs transition-all cursor-pointer"
          >
            + Report Incident
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl border border-rose-200 bg-rose-50 text-rose-800 text-xs flex items-center gap-2 shadow-2xs">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span className="font-medium">{error}</span>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="p-4 rounded-xl border border-[#E2E8F0] bg-white shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
        <div className="relative flex-1 max-w-md">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
          <input
            type="text"
            placeholder="Search incident ID, complaint keywords, address..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-[#E2E8F0] bg-white text-[#172033] placeholder-[#94A3B8] focus:outline-none focus:border-[#0F766E] focus:ring-1 focus:ring-[#0F766E] shadow-2xs"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 border border-[#E2E8F0] rounded-lg bg-white px-2.5 py-1 shadow-2xs">
            <span className="text-[10px] uppercase font-mono text-[#64748B] font-semibold">Category:</span>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="bg-transparent text-[#172033] text-xs focus:outline-none cursor-pointer"
            >
              <option value="all">All</option>
              <option value="pothole">Pothole</option>
              <option value="waterlogging">Waterlogging</option>
              <option value="garbage">Garbage</option>
              <option value="uncertain_other">Uncertain / Other</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 border border-[#E2E8F0] rounded-lg bg-white px-2.5 py-1 shadow-2xs">
            <span className="text-[10px] uppercase font-mono text-[#64748B] font-semibold">Status:</span>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="bg-transparent text-[#172033] text-xs focus:outline-none cursor-pointer"
            >
              <option value="all">All</option>
              <option value="NEW">New</option>
              <option value="RECORDED_PENDING_REVIEW">Pending Review</option>
              <option value="TRIAGED">Triaged</option>
              <option value="AWAITING_CLARIFICATION">Awaiting Clarification</option>
              <option value="SIMULATED_RESOLVED">Simulated Resolved</option>
              <option value="CLOSURE_BLOCKED">Closure Blocked</option>
              <option value="ESCALATED">Escalated</option>
              <option value="VERIFIED_CLOSED">Verified Closed</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 border border-[#E2E8F0] rounded-lg bg-white px-2.5 py-1 shadow-2xs">
            <span className="text-[10px] uppercase font-mono text-[#64748B] font-semibold">Evidence:</span>
            <select
              value={selectedEvidence}
              onChange={(e) => setSelectedEvidence(e.target.value)}
              className="bg-transparent text-[#172033] text-xs focus:outline-none cursor-pointer"
            >
              <option value="all">All</option>
              <option value="MATCHED">Matched</option>
              <option value="MISMATCH">Mismatch</option>
              <option value="INCONCLUSIVE">Inconclusive</option>
              <option value="LOW_QUALITY">Low Quality</option>
              <option value="NOT_PROVIDED">Not Provided</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Grid: Incident Table & Quick Inspection Card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Table Column */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between text-xs text-[#64748B] px-1">
            <span>Showing {filtered.length} of {incidents.length} incidents</span>
            {filtered.length !== incidents.length && (
              <button
                onClick={() => {
                  setSearchTerm('');
                  setSelectedCategory('all');
                  setSelectedStatus('all');
                  setSelectedEvidence('all');
                }}
                className="text-[#0F766E] hover:underline font-medium cursor-pointer"
              >
                Clear all filters
              </button>
            )}
          </div>

          {filtered.length === 0 ? (
            <div className="p-12 text-center rounded-xl border border-dashed border-[#E2E8F0] bg-white shadow-2xs space-y-3">
              <p className="text-[#64748B] text-sm">
                {incidents.length === 0
                  ? 'No incidents recorded in database. The system is ready to receive citizen reports.'
                  : 'No incidents match the active search or filters.'}
              </p>
              {incidents.length === 0 && (
                <button
                  onClick={onNavigateToIntake}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-[#0F766E] hover:bg-[#115E59] text-white shadow-xs cursor-pointer"
                >
                  Submit First Citizen Report
                </button>
              )}
            </div>
          ) : (
            <div className="rounded-xl border border-[#E2E8F0] bg-white overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#F8FAFC] text-[#64748B] border-b border-[#E2E8F0] uppercase font-mono text-[10px] tracking-wider font-semibold">
                    <tr>
                      <th className="py-3 px-3.5">Case ID</th>
                      <th className="py-3 px-3.5">Category</th>
                      <th className="py-3 px-3.5">Complaint</th>
                      <th className="py-3 px-3.5">Status</th>
                      <th className="py-3 px-3.5">Evidence</th>
                      <th className="py-3 px-3.5">Priority</th>
                      <th className="py-3 px-3.5 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E2E8F0]">
                    {filtered.map((inc) => {
                      const isSelected = selectedForPreview?.incident_id === inc.incident_id;
                      return (
                        <tr
                          key={inc.incident_id}
                          onClick={() => setSelectedForPreview(inc)}
                          className={`cursor-pointer transition-colors ${
                            isSelected ? 'bg-teal-50/80 border-l-2 border-l-[#0F766E]' : 'hover:bg-slate-50/80'
                          }`}
                        >
                          <td className="py-3.5 px-3.5 font-mono font-bold text-[#0F766E]">
                            {inc.incident_id}
                          </td>
                          <td className="py-3.5 px-3.5 capitalize text-[#172033] font-medium">
                            {inc.category.replace('_', ' ')}
                          </td>
                          <td className="py-3.5 px-3.5 text-[#64748B] max-w-xs truncate" title={inc.complaint}>
                            {inc.complaint}
                          </td>
                          <td className="py-3.5 px-3.5">
                            <OperationalStatusBadge status={inc.operational_status} size="sm" />
                          </td>
                          <td className="py-3.5 px-3.5">
                            <EvidenceStatusBadge outcome={inc.evidence_status} size="sm" />
                          </td>
                          <td className="py-3.5 px-3.5">
                            {inc.priority ? (
                              <span className="font-mono text-[#172033] font-semibold">
                                {inc.priority.priority_score} <span className="text-[10px] text-[#64748B] font-normal">({inc.priority.priority_band})</span>
                              </span>
                            ) : (
                              <span className="text-[#94A3B8] text-[10px]">Unscored</span>
                            )}
                          </td>
                          <td className="py-3.5 px-3.5 text-right">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                onSelectIncident(inc.incident_id);
                              }}
                              className="text-[#0F766E] hover:text-[#115E59] font-semibold text-[11px] hover:underline cursor-pointer"
                            >
                              Open Twin →
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Selected Incident Quick Inspection Column */}
        <div className="space-y-4">
          {selectedForPreview ? (
            <div className="p-5 rounded-xl border border-[#E2E8F0] bg-white shadow-sm space-y-4 sticky top-24">
              <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-3">
                <div>
                  <span className="text-[10px] font-mono text-[#64748B] uppercase font-semibold">Case Summary</span>
                  <div className="font-mono font-bold text-base text-[#0F766E]">
                    {selectedForPreview.incident_id}
                  </div>
                </div>
                <OperationalStatusBadge status={selectedForPreview.operational_status} size="sm" />
              </div>

              {/* Full Description */}
              <div className="space-y-1">
                <span className="text-[10px] font-mono text-[#64748B] uppercase font-semibold">Original Complaint:</span>
                <p className="text-xs text-[#172033] bg-[#F8FAFC] p-3 rounded-lg border border-[#E2E8F0] leading-relaxed font-sans">
                  "{selectedForPreview.complaint}"
                </p>
              </div>

              {/* Geo Details */}
              <div className="p-3 rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] space-y-2 text-xs">
                <div className="flex items-center gap-1.5 text-[#64748B] text-[10px] font-mono uppercase font-semibold">
                  <MapPin className="w-3.5 h-3.5 text-[#0F766E]" />
                  <span>Geo-Spatial Coordinates</span>
                </div>
                {selectedForPreview.location?.latitude ? (
                  <div className="space-y-1 font-mono text-[11px] text-[#172033]">
                    <div>Lat: {selectedForPreview.location.latitude.toFixed(5)}, Lon: {selectedForPreview.location.longitude?.toFixed(5)}</div>
                    <div className="text-[#64748B] text-[10px] truncate">{selectedForPreview.location.address_text || 'Address recorded'}</div>
                    <div className="text-[#94A3B8] text-[10px]">Source: {selectedForPreview.location.source} • Confirmed: {selectedForPreview.location.is_user_confirmed ? 'Yes' : 'No'}</div>
                  </div>
                ) : (
                  <div className="text-[#94A3B8] text-[11px]">No GPS coordinates provided</div>
                )}
              </div>

              {/* Duplicate Candidates Section (Invariant 7) */}
              <div className="p-3 rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono text-[#64748B] uppercase font-semibold">Duplicate Candidates:</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200 font-semibold">
                    UNCONFIRMED
                  </span>
                </div>
                {selectedForPreview.geo_context?.duplicate_candidates && selectedForPreview.geo_context.duplicate_candidates.length > 0 ? (
                  <div className="space-y-1.5">
                    {selectedForPreview.geo_context.duplicate_candidates.map((cand, idx) => (
                      <div key={idx} className="p-2.5 rounded-lg border border-[#E2E8F0] bg-white text-[11px] shadow-2xs">
                        <div className="font-mono font-bold text-[#0F766E]">{cand.incident_id}</div>
                        <div className="text-[#64748B] text-[10px]">
                          Distance: {Math.round(cand.distance_meters)}m • Match: {(cand.match_confidence * 100).toFixed(0)}%
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-[#94A3B8] text-[11px]">No duplicate candidates within proximity radius.</p>
                )}
              </div>

              {/* Navigation Action Buttons */}
              <div className="pt-2 flex flex-col gap-2">
                <button
                  onClick={() => onSelectIncident(selectedForPreview.incident_id)}
                  className="w-full py-2.5 px-3 text-xs font-semibold rounded-lg bg-[#0F766E] hover:bg-[#115E59] text-white shadow-xs transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <Eye className="w-3.5 h-3.5" />
                  Inspect Civic Incident Twin
                </button>
                <button
                  onClick={() => onOpenCommandCenter(selectedForPreview.incident_id)}
                  className="w-full py-2.5 px-3 text-xs font-medium rounded-lg border border-[#E2E8F0] bg-white hover:bg-slate-50 text-[#172033] shadow-2xs transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <ExternalLink className="w-3.5 h-3.5 text-[#0F766E]" />
                  Open in Agent Operations
                </button>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center rounded-xl border border-dashed border-[#E2E8F0] bg-white text-[#94A3B8] text-xs shadow-2xs">
              Select an incident from the registry to inspect its properties.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
