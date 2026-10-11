import React from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import type { Incident } from '../../types/api';
import { OperationalStatusBadge } from '../common/StatusBadge';

interface IncidentMapProps {
  incidents: Incident[];
  onSelectIncident: (id: string) => void;
}

function createMarkerIcon(priority?: string) {
  let color = '#2dd4bf'; // teal (medium/default)
  if (priority === 'Critical') color = '#ef4444'; // red
  else if (priority === 'High') color = '#f59e0b'; // amber
  else if (priority === 'Low') color = '#94a3b8'; // slate

  const html = `
    <div style="
      background-color: ${color};
      width: 22px;
      height: 22px;
      border-radius: 50%;
      border: 2.5px solid #0f172a;
      box-shadow: 0 0 10px ${color}88;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #0f172a;
      font-weight: bold;
      font-size: 10px;
    ">
      •
    </div>
  `;

  return L.divIcon({
    className: 'custom-incident-pin',
    html,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });
}

export const IncidentMap: React.FC<IncidentMapProps> = ({ incidents, onSelectIncident }) => {
  // Filter incidents that have valid coordinates
  const geoIncidents = incidents.filter(
    (inc) =>
      inc.location &&
      typeof inc.location.latitude === 'number' &&
      typeof inc.location.longitude === 'number'
  );

  // Center on first incident or default to New Delhi
  const defaultCenter: [number, number] =
    geoIncidents.length > 0
      ? [geoIncidents[0].location.latitude!, geoIncidents[0].location.longitude!]
      : [28.6139, 77.209];

  return (
    <div className="w-full h-80 rounded-xl overflow-hidden border border-slate-800 shadow-inner relative z-0">
      <MapContainer
        center={defaultCenter}
        zoom={geoIncidents.length > 0 ? 13 : 11}
        scrollWheelZoom={false}
        className="w-full h-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {geoIncidents.map((inc) => (
          <Marker
            key={inc.incident_id}
            position={[inc.location.latitude!, inc.location.longitude!]}
            icon={createMarkerIcon(inc.priority?.priority_band)}
          >
            <Popup className="incident-map-popup">
              <div className="p-1 space-y-2 text-slate-900 min-w-[200px]">
                <div className="flex justify-between items-center border-b pb-1">
                  <span className="font-mono font-bold text-xs">{inc.incident_id}</span>
                  <span className="text-[10px] uppercase font-semibold text-slate-500">{inc.category}</span>
                </div>
                <p className="text-xs text-slate-700 line-clamp-2">{inc.complaint}</p>
                <div className="flex justify-between items-center pt-1">
                  <OperationalStatusBadge status={inc.operational_status} size="sm" />
                  <button
                    onClick={() => onSelectIncident(inc.incident_id)}
                    className="text-[11px] font-semibold text-teal-600 hover:text-teal-800 underline"
                  >
                    View Case →
                  </button>
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      {geoIncidents.length === 0 && (
        <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center pointer-events-none">
          <p className="text-xs text-slate-400">No geo-tagged incidents with confirmed coordinates recorded yet.</p>
        </div>
      )}
    </div>
  );
};
