import React, { useState, useRef } from 'react';
import {
  AlertCircle,
  Camera,
  CheckCircle2,
  Info,
  LocateFixed,
  Trash2,
  Upload,
} from 'lucide-react';
import type { Incident, IncidentCategory, LocationSource } from '../../types/api';
import { api } from '../../services/api';
import { OperationalStatusBadge, EvidenceStatusBadge } from '../common/StatusBadge';

interface CitizenSubmissionFormProps {
  onSuccess: (incident: Incident) => void;
}

export const CitizenSubmissionForm: React.FC<CitizenSubmissionFormProps> = ({ onSuccess }) => {
  const [complaint, setComplaint] = useState<string>('');
  const [category, setCategory] = useState<IncidentCategory>('pothole');
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);

  // Location state
  const [latitude, setLatitude] = useState<number | null>(null);
  const [longitude, setLongitude] = useState<number | null>(null);
  const [accuracy, setAccuracy] = useState<number | null>(null);
  const [locationSource, setLocationSource] = useState<LocationSource>('MANUAL_ENTRY');
  const [addressText, setAddressText] = useState<string>('');
  const [isConfirmed, setIsConfirmed] = useState<boolean>(false);
  const [locating, setLocating] = useState<boolean>(false);
  const [locationNotice, setLocationNotice] = useState<string | null>(null);

  // Clues & severity flags
  const [clues, setClues] = useState<{
    arterialRoad: boolean;
    pedestrianSkidHazard: boolean;
    standingWaterDepth: boolean;
    overflowDump: boolean;
  }>({
    arterialRoad: false,
    pedestrianSkidHazard: false,
    standingWaterDepth: false,
    overflowDump: false,
  });

  // Submission state
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submittedIncident, setSubmittedIncident] = useState<Incident | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  // Geolocation handler (single snapshot, triggered by explicit user action)
  const handleCaptureLocation = () => {
    if (!navigator.geolocation) {
      setLocationNotice('Geolocation is not supported by your browser. Please enter the location address manually.');
      return;
    }

    setLocating(true);
    setLocationNotice(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLatitude(position.coords.latitude);
        setLongitude(position.coords.longitude);
        setAccuracy(position.coords.accuracy);
        setLocationSource('DEVICE_GPS');
        setIsConfirmed(true);
        setLocationNotice(`Location acquired with ±${Math.round(position.coords.accuracy)}m accuracy.`);
        setLocating(false);
      },
      (error) => {
        setLocating(false);
        if (error.code === error.PERMISSION_DENIED) {
          setLocationNotice('Location permission was denied. You can specify the street or landmark address manually.');
        } else {
          setLocationNotice('Unable to acquire GPS coordinates. Please use manual address entry.');
        }
        setLocationSource('MANUAL_ENTRY');
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    );
  };

  const handlePhotoSelect = (file: File) => {
    if (file.size > 10 * 1024 * 1024) {
      setErrorMessage('Photograph exceeds maximum 10MB limit.');
      return;
    }
    setPhotoFile(file);
    const objectUrl = URL.createObjectURL(file);
    setPhotoPreview(objectUrl);
    setErrorMessage(null);
  };

  const handleRemovePhoto = () => {
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setPhotoFile(null);
    setPhotoPreview(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (complaint.trim().length < 5) {
      setErrorMessage('Please describe the problem with at least 5 characters.');
      return;
    }

    setSubmitting(true);
    setErrorMessage(null);

    // Build synthesized description with selected clues
    const clueSnippets = [];
    if (clues.arterialRoad) clueSnippets.push('Located on main arterial road.');
    if (clues.pedestrianSkidHazard) clueSnippets.push('Immediate hazard for two-wheelers or pedestrians.');
    if (clues.standingWaterDepth) clueSnippets.push('Water accumulation depth exceeds 1 foot.');
    if (clues.overflowDump) clueSnippets.push('Active waste overflow and severe odor.');

    const finalDescription = clueSnippets.length > 0
      ? `${complaint.trim()}\n\n[Citizen Clues]: ${clueSnippets.join(' ')}`
      : complaint.trim();

    try {
      const formData = new FormData();
      formData.append('complaint', finalDescription);
      formData.append('category', category);

      if (latitude !== null && longitude !== null) {
        formData.append('latitude', String(latitude));
        formData.append('longitude', String(longitude));
        if (accuracy !== null) formData.append('accuracy_meters', String(accuracy));
        formData.append('location_source', locationSource);
        formData.append('is_user_confirmed', String(isConfirmed));
      }

      if (addressText.trim()) {
        formData.append('address_text', addressText.trim());
      }

      if (photoFile) {
        formData.append('image', photoFile);
      }

      const created = await api.createIncident(formData);
      setSubmittedIncident(created);
      onSuccess(created);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to submit incident report.');
    } finally {
      setSubmitting(false);
    }
  };

  if (submittedIncident) {
    return (
      <div className="max-w-2xl mx-auto p-6 rounded-xl border border-emerald-200 bg-white shadow-sm text-center space-y-6 animate-in zoom-in-95 duration-200">
        <div className="w-14 h-14 rounded-full bg-emerald-50 border border-emerald-200 flex items-center justify-center mx-auto text-emerald-600 shadow-2xs">
          <CheckCircle2 className="w-8 h-8" />
        </div>
        <div className="space-y-1.5">
          <h2 className="text-xl font-bold text-[#172033] tracking-tight">Citizen Report Successfully Logged</h2>
          <p className="text-xs text-[#64748B]">
            Your complaint has been permanently archived in the municipal dispatch registry.
          </p>
        </div>

        <div className="p-4 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] text-left space-y-3 font-mono text-xs">
          <div className="flex justify-between items-center border-b border-[#E2E8F0] pb-2">
            <span className="text-[#64748B]">Tracking Reference:</span>
            <span className="font-bold text-[#0F766E] text-sm">{submittedIncident.incident_id}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-[#64748B]">Operational Lifecycle:</span>
            <OperationalStatusBadge status={submittedIncident.operational_status} size="sm" />
          </div>
          <div className="flex justify-between items-center">
            <span className="text-[#64748B]">Photographic Evidence:</span>
            <EvidenceStatusBadge outcome={submittedIncident.evidence_status} size="sm" />
          </div>
          <div className="flex justify-between items-center">
            <span className="text-[#64748B]">Location Record:</span>
            <span className="text-[#172033]">
              {submittedIncident.location?.latitude
                ? `${submittedIncident.location.latitude.toFixed(4)}° N, ${submittedIncident.location.longitude?.toFixed(4)}° E (${submittedIncident.location.source})`
                : submittedIncident.location?.address_text || 'Manual address entry'}
            </span>
          </div>
        </div>

        <div className="pt-2 flex justify-center gap-3">
          <button
            onClick={() => {
              setSubmittedIncident(null);
              setComplaint('');
              handleRemovePhoto();
              setLatitude(null);
              setLongitude(null);
              setAddressText('');
            }}
            className="px-4 py-2 text-xs font-semibold rounded-lg border border-[#E2E8F0] bg-white text-[#172033] hover:bg-slate-50 shadow-2xs cursor-pointer"
          >
            Submit Another Complaint
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-in fade-in duration-300">
      <div>
        <h1 className="text-2xl font-bold text-[#172033] tracking-tight flex items-center gap-2">
          Citizen Civic Incident Reporting
        </h1>
        <p className="text-xs text-[#64748B] mt-1">
          Submit potholes, waterlogging, or sanitation backlogs. Photographs are recommended for verification but never required.
        </p>
      </div>

      {errorMessage && (
        <div className="p-4 rounded-xl border border-rose-200 bg-rose-50 text-rose-800 text-xs flex items-center gap-2.5 shadow-2xs">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span className="font-medium">{errorMessage}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* 1. Category Selection */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-[#172033]">Incident Category</label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            {[
              { id: 'pothole', label: 'Pothole', sub: 'Road crater / skid' },
              { id: 'waterlogging', label: 'Waterlogging', sub: 'Flooding / blocked drain' },
              { id: 'garbage', label: 'Garbage Dump', sub: 'Sanitation / odor' },
              { id: 'uncertain_other', label: 'Other / Uncertain', sub: 'General defect' },
            ].map((cat) => {
              const active = category === cat.id;
              return (
                <button
                  type="button"
                  key={cat.id}
                  onClick={() => setCategory(cat.id as IncidentCategory)}
                  className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                    active
                      ? 'border-[#0F766E] bg-teal-50 text-[#172033] shadow-xs'
                      : 'border-[#E2E8F0] bg-white text-[#64748B] hover:border-slate-300 hover:text-[#172033]'
                  }`}
                >
                  <div className={`font-semibold text-xs ${active ? 'text-[#0F766E]' : 'text-[#172033]'}`}>{cat.label}</div>
                  <div className="text-[10px] text-[#64748B] mt-0.5">{cat.sub}</div>
                </button>
              );
            })}
          </div>
        </div>

        {/* 2. Problem Description */}
        <div className="space-y-1.5">
          <div className="flex justify-between items-center text-xs">
            <label className="font-semibold text-[#172033]">Complaint Description</label>
            <span className={`text-[11px] font-mono ${complaint.length > 1900 ? 'text-amber-600' : 'text-[#64748B]'}`}>
              {complaint.length} / 2000
            </span>
          </div>
          <textarea
            rows={4}
            value={complaint}
            onChange={(e) => setComplaint(e.target.value)}
            placeholder="Describe the issue, defect dimensions, surrounding hazards, and nearest landmark..."
            className="w-full px-3.5 py-2.5 rounded-xl border border-[#E2E8F0] bg-white text-[#172033] placeholder-[#94A3B8] text-xs focus:outline-none focus:border-[#0F766E] focus:ring-1 focus:ring-[#0F766E] shadow-2xs"
          />
        </div>

        {/* 3. Severity & Exposure Clues */}
        <div className="p-4 rounded-xl border border-[#E2E8F0] bg-white shadow-sm space-y-3">
          <label className="text-xs font-semibold text-[#172033] flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-[#0F766E]" />
            Public Hazard Clues (Assists Transparent Priority Triage)
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs text-[#172033]">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={clues.arterialRoad}
                onChange={(e) => setClues({ ...clues, arterialRoad: e.target.checked })}
                className="rounded border-[#E2E8F0] text-[#0F766E] focus:ring-[#0F766E] accent-[#0F766E]"
              />
              <span>High-traffic arterial road or flyover</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={clues.pedestrianSkidHazard}
                onChange={(e) => setClues({ ...clues, pedestrianSkidHazard: e.target.checked })}
                className="rounded border-[#E2E8F0] text-[#0F766E] focus:ring-[#0F766E] accent-[#0F766E]"
              />
              <span>Immediate accident or skid hazard</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={clues.standingWaterDepth}
                onChange={(e) => setClues({ ...clues, standingWaterDepth: e.target.checked })}
                className="rounded border-[#E2E8F0] text-[#0F766E] focus:ring-[#0F766E] accent-[#0F766E]"
              />
              <span>Submerged &gt; 1 ft depth</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={clues.overflowDump}
                onChange={(e) => setClues({ ...clues, overflowDump: e.target.checked })}
                className="rounded border-[#E2E8F0] text-[#0F766E] focus:ring-[#0F766E] accent-[#0F766E]"
              />
              <span>Spilling onto roadway with odor</span>
            </label>
          </div>
        </div>

        {/* 4. Optional Photo Capture / Upload */}
        <div className="p-4 rounded-xl border border-[#E2E8F0] bg-white shadow-sm space-y-3">
          <div className="flex justify-between items-center">
            <div>
              <label className="text-xs font-semibold text-[#172033]">Incident Photograph (Optional)</label>
              <p className="text-[11px] text-[#64748B]">
                Helps Groq Vision verify category and severity. EXIF metadata is scrubbed automatically.
              </p>
            </div>
            <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-slate-100 text-[#64748B] font-medium">
              Max 10MB
            </span>
          </div>

          {photoPreview ? (
            <div className="relative rounded-xl overflow-hidden border border-[#E2E8F0] bg-[#F8FAFC] max-w-sm mx-auto shadow-2xs">
              <img src={photoPreview} alt="Incident preview" className="w-full h-48 object-cover" />
              <button
                type="button"
                onClick={handleRemovePhoto}
                className="absolute top-2 right-2 p-1.5 rounded-full bg-white/90 text-rose-600 hover:bg-white transition-colors shadow-sm cursor-pointer"
                title="Remove photo"
              >
                <Trash2 className="w-4 h-4" />
              </button>
              <div className="p-2 text-center text-[11px] font-mono text-[#64748B] border-t border-[#E2E8F0] bg-white">
                {photoFile?.name} ({(photoFile!.size / (1024 * 1024)).toFixed(2)} MB)
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              {/* Direct Camera Capture (Mobile Rear Camera) */}
              <button
                type="button"
                onClick={() => cameraInputRef.current?.click()}
                className="flex items-center justify-center gap-2 p-3 rounded-xl border border-dashed border-teal-300 bg-teal-50/50 hover:bg-teal-50 text-[#0F766E] text-xs font-semibold transition-all cursor-pointer"
              >
                <Camera className="w-4 h-4" />
                Take Photo (Camera)
              </button>
              <input
                ref={cameraInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                capture="environment"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && handlePhotoSelect(e.target.files[0])}
              />

              {/* Standard File Upload */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center justify-center gap-2 p-3 rounded-xl border border-dashed border-[#E2E8F0] bg-[#F8FAFC] hover:bg-slate-100 text-[#172033] text-xs font-medium transition-all cursor-pointer"
              >
                <Upload className="w-4 h-4 text-[#64748B]" />
                Upload File from Device
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && handlePhotoSelect(e.target.files[0])}
              />
            </div>
          )}
        </div>

        {/* 5. Location Capture & Confirmation */}
        <div className="p-4 rounded-xl border border-[#E2E8F0] bg-white shadow-sm space-y-3">
          <div className="flex justify-between items-center">
            <div>
              <label className="text-xs font-semibold text-[#172033]">Incident Location</label>
              <p className="text-[11px] text-[#64748B]">
                A single coordinate snapshot is requested only upon clicking below.
              </p>
            </div>
            {latitude !== null && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-teal-50 text-[#0F766E] border border-teal-200 font-medium">
                {locationSource}
              </span>
            )}
          </div>

          <div className="flex flex-col sm:flex-row gap-2">
            <button
              type="button"
              onClick={handleCaptureLocation}
              disabled={locating}
              className="flex items-center justify-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg bg-white hover:bg-slate-50 text-[#172033] border border-[#E2E8F0] shadow-2xs transition-colors disabled:opacity-50 cursor-pointer"
            >
              <LocateFixed className={`w-3.5 h-3.5 text-[#0F766E] ${locating ? 'animate-spin' : ''}`} />
              {locating ? 'Acquiring GPS...' : 'Capture My Location'}
            </button>

            {latitude !== null && longitude !== null && (
              <div className="flex-1 px-3 py-2 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] font-mono text-xs text-[#172033] flex items-center justify-between">
                <span>
                  {latitude.toFixed(5)}°, {longitude.toFixed(5)}°
                </span>
                {accuracy !== null && (
                  <span className="text-[10px] text-[#64748B]">±{Math.round(accuracy)}m accuracy</span>
                )}
              </div>
            )}
          </div>

          {locationNotice && (
            <p className="text-[11px] text-[#0F766E] font-medium">{locationNotice}</p>
          )}

          {/* Manual Address Input */}
          <div className="pt-1">
            <input
              type="text"
              value={addressText}
              onChange={(e) => setAddressText(e.target.value)}
              placeholder="Or specify landmark / street address (e.g., Near Mayur Vihar Flyover, Ring Road)..."
              className="w-full px-3 py-2 rounded-lg border border-[#E2E8F0] bg-white text-[#172033] placeholder-[#94A3B8] text-xs focus:outline-none focus:border-[#0F766E] focus:ring-1 focus:ring-[#0F766E] shadow-2xs"
            />
          </div>
        </div>

        {/* Submit Action */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={submitting}
            className="w-full py-3 px-4 rounded-xl font-bold text-sm bg-[#0F766E] hover:bg-[#115E59] text-white shadow-sm transition-all disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer"
          >
            {submitting ? 'Registering Citizen Complaint...' : 'Submit Citizen Incident Report'}
          </button>
        </div>
      </form>
    </div>
  );
};
