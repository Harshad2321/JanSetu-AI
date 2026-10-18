import React, { useState, useEffect } from 'react';
import {
  Activity,
  Database,
  Eye,
  Globe,
  Lock,
  RefreshCw,
  Server,
  Shield,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import type { HealthResponse } from '../../types/api';
import { api } from '../../services/api';

interface SystemHealthViewProps {
  health: HealthResponse | null;
  onRefreshHealth: () => void;
}

export const SystemHealthView: React.FC<SystemHealthViewProps> = ({
  health,
  onRefreshHealth,
}) => {
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [checking, setChecking] = useState<boolean>(false);
  const [lastChecked, setLastChecked] = useState<string>(new Date().toLocaleTimeString());

  const checkPing = async () => {
    setChecking(true);
    const start = performance.now();
    try {
      await api.getHealth();
      const end = performance.now();
      setLatencyMs(Math.round(end - start));
      setLastChecked(new Date().toLocaleTimeString());
      onRefreshHealth();
    } catch {
      setLatencyMs(null);
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    checkPing();
  }, []);

  const isHealthy = health?.status === 'healthy';

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E2E8F0] pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-[#172033]">
              System Health & Diagnostics
            </h1>
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                isHealthy
                  ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                  : 'bg-rose-50 text-rose-800 border border-rose-200'
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  isHealthy ? 'bg-emerald-600 animate-pulse' : 'bg-rose-600'
                }`}
              />
              {isHealthy ? 'Operational' : 'Service Disrupted'}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Real-time backend telemetry, service capability matrix, and demonstration boundary audit.
          </p>
        </div>

        <button
          onClick={checkPing}
          disabled={checking}
          className="self-start sm:self-auto flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-white hover:bg-slate-50 border border-[#E2E8F0] text-slate-700 shadow-xs transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${checking ? 'animate-spin text-teal-600' : 'text-slate-500'}`} />
          {checking ? 'Pinging Backend...' : 'Ping Diagnostics'}
        </button>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Core Service</span>
            <Server className="w-4 h-4 text-teal-700" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-bold text-[#172033]">{health?.service || 'JanSetu AI API'}</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1 font-mono">
            Status: {health?.status || 'Unknown'}
          </p>
        </div>

        <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Persistence Layer</span>
            <Database className="w-4 h-4 text-emerald-700" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-bold text-[#172033]">SQLite + WAL</span>
          </div>
          <p className="text-[11px] text-emerald-800 mt-1 font-mono font-medium">
            Connection: {health?.database || 'Connected'} (Thread-safe)
          </p>
        </div>

        <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Vision Inference</span>
            <Eye className="w-4 h-4 text-teal-700" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-bold text-[#172033]">Groq Multimodal</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1 font-mono">
            {health?.groq_configured ? (
              <span className="text-teal-800 font-semibold">API Key Verified (Active)</span>
            ) : (
              <span className="text-amber-800 font-medium">Fallback Heuristic Mode</span>
            )}
          </p>
        </div>

        <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">API Latency</span>
            <Activity className="w-4 h-4 text-teal-700" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-bold text-[#172033]">
              {latencyMs !== null ? `${latencyMs} ms` : '—'}
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1 font-mono">
            Checked at {lastChecked}
          </p>
        </div>
      </div>

      {/* Main Grid: Architecture & Capabilities */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Capabilities Matrix */}
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 space-y-4 shadow-xs">
          <div className="flex items-center gap-2 border-b border-[#E2E8F0] pb-3">
            <Zap className="w-4 h-4 text-teal-700" />
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-800">
              Agent System Capabilities Matrix
            </h2>
          </div>

          <div className="divide-y divide-[#E2E8F0] text-xs">
            <div className="py-2.5 flex items-center justify-between">
              <div>
                <p className="font-semibold text-slate-800">Incident Intelligence Agent</p>
                <p className="text-slate-500 text-[11px]">Groq Vision multimodal verification with EXIF sanitization</p>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold">
                ACTIVE
              </span>
            </div>

            <div className="py-2.5 flex items-center justify-between">
              <div>
                <p className="font-semibold text-slate-800">GeoCivic Duplicate Detection</p>
                <p className="text-slate-500 text-[11px]">Haversine proximity analysis with coordinate confidence</p>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold">
                ACTIVE
              </span>
            </div>

            <div className="py-2.5 flex items-center justify-between">
              <div>
                <p className="font-semibold text-slate-800">Parallel Priority Intelligence</p>
                <p className="text-slate-500 text-[11px]">Multi-factor scoring (Exposure, Hazard, Artery, Duplicate Penalty)</p>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold">
                ACTIVE
              </span>
            </div>

            <div className="py-2.5 flex items-center justify-between">
              <div>
                <p className="font-semibold text-slate-800">Resolution Planning Specialist</p>
                <p className="text-slate-500 text-[11px]">Bifurcated mitigation and permanent repair plan synthesis</p>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold">
                ACTIVE
              </span>
            </div>

            <div className="py-2.5 flex items-center justify-between">
              <div>
                <p className="font-semibold text-slate-800">Adaptive Recovery Agent</p>
                <p className="text-slate-500 text-[11px]">Dynamic resource constraint mitigation with retry caps</p>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold">
                ACTIVE
              </span>
            </div>

            <div className="py-2.5 flex items-center justify-between">
              <div>
                <p className="font-semibold text-slate-800">Critic & Verification Gatekeeper</p>
                <p className="text-slate-500 text-[11px]">Deterministic closure verification; blocks false resolutions</p>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold">
                ACTIVE
              </span>
            </div>
          </div>
        </div>

        {/* Security & Boundary Guarantees */}
        <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 space-y-4 shadow-xs">
          <div className="flex items-center gap-2 border-b border-[#E2E8F0] pb-3">
            <ShieldCheck className="w-4 h-4 text-teal-700" />
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-800">
              Operational Safety & Boundaries
            </h2>
          </div>

          <div className="space-y-3 text-xs text-slate-600 leading-relaxed">
            <div className="flex items-start gap-2.5 bg-slate-50 rounded-lg p-3 border border-[#E2E8F0]">
              <Lock className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-slate-800">Credential & Secret Protection</p>
                <p className="text-slate-500 text-[11px] mt-0.5">
                  Backend API credentials, Groq tokens, and file system paths are strictly isolated on the server. No client bundle or response contains sensitive credentials.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-2.5 bg-slate-50 rounded-lg p-3 border border-[#E2E8F0]">
              <Shield className="w-4 h-4 text-teal-700 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-slate-800">Deterministic Closure Gate</p>
                <p className="text-slate-500 text-[11px] mt-0.5">
                  An incident can never be marked as resolved simply by completing an execution loop. Verified photographic post-repair closure evidence is mandatory.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-2.5 bg-slate-50 rounded-lg p-3 border border-[#E2E8F0]">
              <Globe className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-slate-800">Simulated Municipal Demonstration</p>
                <p className="text-slate-500 text-[11px] mt-0.5">
                  All work orders, crew dispatch records, and material inventory states are simulated demonstrations. No real municipal crews are dispatched from this environment.
                </p>
              </div>
            </div>
          </div>

          {/* Connection Details */}
          <div className="rounded-lg border border-[#E2E8F0] bg-slate-50 p-3.5 space-y-1.5 font-mono text-[11px]">
            <div className="flex justify-between text-slate-500">
              <span>API Gateway:</span>
              <span className="text-teal-800 font-semibold">{api.getBaseUrl()}</span>
            </div>
            <div className="flex justify-between text-slate-500">
              <span>Environment:</span>
              <span className="text-slate-800">{health?.environment || 'development'}</span>
            </div>
            <div className="flex justify-between text-slate-500">
              <span>CORS Policy:</span>
              <span className="text-slate-800">Configured for Frontend</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
