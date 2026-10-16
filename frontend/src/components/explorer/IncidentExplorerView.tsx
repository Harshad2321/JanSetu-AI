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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Search className="w-6 h-6 text-teal-400" />
            Civic Incident Explorer
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Search, filter, and inspect registered municipal incidents, unconfirmed duplicate candidates, and geo-spatial coordinates.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadIncidents}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3.5 py-1.5 text-xs font-semibold rounded-lg border border-slate-700 bg-slate-900 hover:bg-slate-800 text-slate-300 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh Registry
          </button>
          <button
            onClick={onNavigateToIntake}
            className="px-3.5 py-1.5 text-xs font-bold rounded-lg bg-teal-600 hover:bg-teal-500 text-white shadow-md shadow-teal-500/20 transition-all"
          >
            + Report Incident
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl border border-rose-500/40 bg-rose-500/10 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
        <div className="relative flex-1 max-w-md">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search incident ID, complaint keywords, address..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-slate-700 bg-slate-950 text-white placeholder-slate-500 focus:outline-none focus:border-teal-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 border border-slate-700 rounded-lg bg-slate-950 px-2.5 py-1">
            <span className="text-[10px] uppercase font-mono text-slate-500">Category:</span>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="bg-transparent text-slate-300 text-xs focus:outline-none"
            >
              <option value="all">All</option>
              <option value="pothole">Pothole</option>
              <option value="waterlogging">Waterlogging</option>
              <option value="garbage">Garbage</option>
              <option value="uncertain_other">Uncertain / Other</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 border border-slate-700 rounded-lg bg-slate-950 px-2.5 py-1">
            <span className="text-[10px] uppercase font-mono text-slate-500">Status:</span>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="bg-transparent text-slate-300 text-xs focus:outline-none"
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

          <div className="flex items-center gap-1.5 border border-slate-700 rounded-lg bg-slate-950 px-2.5 py-1">
            <span className="text-[10px] uppercase font-mono text-slate-500">Evidence:</span>
            <select
              value={selectedEvidence}
              onChange={(e) => setSelectedEvidence(e.target.value)}
              className="bg-transparent text-slate-300 text-xs focus:outline-none"
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
          <div className="flex items-center justify-between text-xs text-slate-400 px-1">
            <span>Showing {filtered.length} of {incidents.length} incidents</span>
            {filtered.length !== incidents.length && (
              <button
                onClick={() => {
                  setSearchTerm('');
                  setSelectedCategory('all');
                  setSelectedStatus('all');
                  setSelectedEvidence('all');
                }}
                className="text-teal-400 hover:underline"
              >
                Clear all filters
              </button>
            )}
          </div>

          {filtered.length === 0 ? (
            <div className="p-12 text-center rounded-2xl border border-dashed border-slate-800 bg-slate-900/30 space-y-3">
              <p className="text-slate-400 text-sm">
                {incidents.length === 0
                  ? 'No incidents recorded in database. The system is ready to receive citizen reports.'
                  : 'No incidents match the active search or filters.'}
              </p>
              {incidents.length === 0 && (
                <button
                  onClick={onNavigateToIntake}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-teal-600 hover:bg-teal-500 text-white shadow-md shadow-teal-500/20"
                >
                  Submit First Citizen Report
                </button>
              )}
            </div>
          ) : (
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden shadow-lg">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 uppercase font-mono text-[10px] tracking-wider">
                    <tr>
                      <th className="py-3 px-3">Case ID</th>
                      <th className="py-3 px-3">Category</th>
                      <th className="py-3 px-3">Complaint</th>
                      <th className="py-3 px-3">Status</th>
                      <th className="py-3 px-3">Evidence</th>
                      <th className="py-3 px-3">Priority</th>
                      <th className="py-3 px-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {filtered.map((inc) => {
                      const isSelected = selectedForPreview?.incident_id === inc.incident_id;
                      return (
                        <tr
                          key={inc.incident_id}
                          onClick={() => setSelectedForPreview(inc)}
                          className={`cursor-pointer transition-colors ${
                            isSelected ? 'bg-teal-950/30 border-l-2 border-l-teal-400' : 'hover:bg-slate-800/40'
                          }`}
                        >
                          <td className="py-3 px-3 font-mono font-bold text-teal-400">
                            {inc.incident_id}
                          </td>
                          <td className="py-3 px-3 capitalize text-slate-300">
                            {inc.category.replace('_', ' ')}
                          </td>
                          <td className="py-3 px-3 text-slate-300 max-w-xs truncate" title={inc.complaint}>
                            {inc.complaint}
                          </td>
                          <td className="py-3 px-3">
                            <OperationalStatusBadge status={inc.operational_status} size="sm" />
                          </td>
                          <td className="py-3 px-3">
                            <EvidenceStatusBadge outcome={inc.evidence_status} size="sm" />
                          </td>
                          <td className="py-3 px-3">
                            {inc.priority ? (
                              <span className="font-mono text-slate-200">
                                {inc.priority.priority_score} <span className="text-[10px] text-slate-500">({inc.priority.priority_band})</span>
                              </span>
                            ) : (
                              <span className="text-slate-500 text-[10px]">Unscored</span>
                            )}
                          </td>
                          <td className="py-3 px-3 text-right">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                onSelectIncident(inc.incident_id);
                              }}
                              className="text-teal-400 hover:text-teal-300 font-semibold text-[11px]"
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
            <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/70 backdrop-blur-md space-y-4 sticky top-24">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div>
                  <span className="text-[10px] font-mono text-slate-400 uppercase">Case Summary</span>
                  <div className="font-mono font-bold text-base text-teal-400">
                    {selectedForPreview.incident_id}
                  </div>
                </div>
                <OperationalStatusBadge status={selectedForPreview.operational_status} size="sm" />
              </div>

              {/* Full Description */}
              <div className="space-y-1">
                <span className="text-[10px] font-mono text-slate-400 uppercase">Original Complaint:</span>
                <p className="text-xs text-slate-200 bg-slate-950/80 p-3 rounded-lg border border-slate-800/80 leading-relaxed font-sans">
                  "{selectedForPreview.complaint}"
                </p>
              </div>

              {/* Geo Details */}
              <div className="p-3 rounded-lg border border-slate-800 bg-slate-950/60 space-y-2 text-xs">
                <div className="flex items-center gap-1.5 text-slate-400 text-[10px] font-mono uppercase">
                  <MapPin className="w-3.5 h-3.5 text-teal-400" />
                  <span>Geo-Spatial Coordinates</span>
                </div>
                {selectedForPreview.location?.latitude ? (
                  <div className="space-y-1 font-mono text-[11px] text-slate-300">
                    <div>Lat: {selectedForPreview.location.latitude.toFixed(5)}, Lon: {selectedForPreview.location.longitude?.toFixed(5)}</div>
                    <div className="text-slate-400 text-[10px] truncate">{selectedForPreview.location.address_text || 'Address recorded'}</div>
                    <div className="text-slate-500 text-[10px]">Source: {selectedForPreview.location.source} • Confirmed: {selectedForPreview.location.is_user_confirmed ? 'Yes' : 'No'}</div>
                  </div>
                ) : (
                  <div className="text-slate-500 text-[11px]">No GPS coordinates provided</div>
                )}
              </div>

              {/* Duplicate Candidates Section (Invariant 7) */}
              <div className="p-3 rounded-lg border border-slate-800 bg-slate-950/60 space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono text-slate-400 uppercase">Duplicate Candidates:</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                    UNCONFIRMED
                  </span>
                </div>
                {selectedForPreview.geo_context?.duplicate_candidates && selectedForPreview.geo_context.duplicate_candidates.length > 0 ? (
                  <div className="space-y-1.5">
                    {selectedForPreview.geo_context.duplicate_candidates.map((cand, idx) => (
                      <div key={idx} className="p-2 rounded border border-slate-800 bg-slate-900/60 text-[11px]">
                        <div className="font-mono font-bold text-teal-300">{cand.incident_id}</div>
                        <div className="text-slate-400 text-[10px]">
                          Distance: {Math.round(cand.distance_meters)}m • Match: {(cand.match_confidence * 100).toFixed(0)}%
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-500 text-[11px]">No duplicate candidates within proximity radius.</p>
                )}
              </div>

              {/* Navigation Action Buttons */}
              <div className="pt-2 flex flex-col gap-2">
                <button
                  onClick={() => onSelectIncident(selectedForPreview.incident_id)}
                  className="w-full py-2 px-3 text-xs font-bold rounded-lg bg-teal-600 hover:bg-teal-500 text-white shadow-md shadow-teal-500/20 transition-all flex items-center justify-center gap-1.5"
                >
                  <Eye className="w-3.5 h-3.5" />
                  Inspect Civic Incident Twin
                </button>
                <button
                  onClick={() => onOpenCommandCenter(selectedForPreview.incident_id)}
                  className="w-full py-2 px-3 text-xs font-medium rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors flex items-center justify-center gap-1.5"
                >
                  <ExternalLink className="w-3.5 h-3.5 text-teal-400" />
                  Open in Agent Operations
                </button>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center rounded-2xl border border-dashed border-slate-800 bg-slate-900/20 text-slate-500 text-xs">
              Select an incident from the registry to inspect its properties.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
