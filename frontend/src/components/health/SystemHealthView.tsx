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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">
              System Health & Diagnostics
            </h1>
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                isHealthy
                  ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                  : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  isHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'
                }`}
              />
              {isHealthy ? 'Operational' : 'Service Disrupted'}
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Real-time backend telemetry, service capability matrix, and demonstration boundary audit
          </p>
        </div>

        <button
          onClick={checkPing}
          disabled={checking}
          className="self-start sm:self-auto flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold bg-teal-600 hover:bg-teal-500 text-white transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${checking ? 'animate-spin' : ''}`} />
          {checking ? 'Pinging Backend...' : 'Ping Diagnostics'}
        </button>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Core Service</span>
            <Server className="w-4 h-4 text-teal-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-bold text-slate-100">{health?.service || 'JanSetu AI API'}</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1 font-mono">
            Status: {health?.status || 'Unknown'}
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Persistence Layer</span>
            <Database className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-bold text-slate-100">SQLite + WAL</span>
          </div>
          <p className="text-[11px] text-emerald-400/90 mt-1 font-mono">
            Connection: {health?.database || 'Connected'} (Thread-safe)
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Vision Inference</span>
            <Eye className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-bold text-slate-100">Groq Multimodal</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1 font-mono">
            {health?.groq_configured ? (
              <span className="text-cyan-400">API Key Verified (Active)</span>
            ) : (
              <span className="text-amber-400">Fallback Heuristic Mode</span>
            )}
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">API Latency</span>
            <Activity className="w-4 h-4 text-teal-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-bold text-slate-100">
              {latencyMs !== null ? `${latencyMs} ms` : '—'}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1 font-mono">
            Checked at {lastChecked}
          </p>
        </div>
      </div>

      {/* Main Grid: Architecture & Capabilities */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Capabilities Matrix */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <Zap className="w-4 h-4 text-teal-400" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
              Agent System Capabilities Matrix
            </h2>
          </div>

          <div className="divide-y divide-slate-800/80 text-xs">
            <div className="py-2.5 flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-200">Incident Intelligence Agent</p>
                <p className="text-slate-400 text-[11px]">Groq Vision multimodal verification with EXIF sanitization</p>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                ACTIVE
              </span>
            </div>

            <div className="py-2.5 flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-200">GeoCivic Duplicate Detection</p>
                <p className="text-slate-400 text-[11px]">Haversine proximity analysis with coordinate confidence</p>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                ACTIVE
              </span>
            </div>

            <div className="py-2.5 flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-200">Parallel Priority Intelligence</p>
                <p className="text-slate-400 text-[11px]">Multi-factor scoring (Exposure, Hazard, Artery, Duplicate Penalty)</p>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                ACTIVE
              </span>
            </div>

            <div className="py-2.5 flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-200">Resolution Planning Specialist</p>
                <p className="text-slate-400 text-[11px]">Bifurcated mitigation and permanent repair plan synthesis</p>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                ACTIVE
              </span>
            </div>

            <div className="py-2.5 flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-200">Adaptive Recovery Agent</p>
                <p className="text-slate-400 text-[11px]">Dynamic resource constraint mitigation with retry caps</p>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                ACTIVE
              </span>
            </div>

            <div className="py-2.5 flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-200">Critic & Verification Gatekeeper</p>
                <p className="text-slate-400 text-[11px]">Deterministic closure verification; blocks false resolutions</p>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                ACTIVE
              </span>
            </div>
          </div>
        </div>

        {/* Security & Boundary Guarantees */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <ShieldCheck className="w-4 h-4 text-teal-400" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
              Operational Safety & Boundaries
            </h2>
          </div>

          <div className="space-y-3 text-xs text-slate-300 leading-relaxed">
            <div className="flex items-start gap-2.5 bg-slate-950/60 rounded-lg p-3 border border-slate-800">
              <Lock className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-slate-200">Credential & Secret Protection</p>
                <p className="text-slate-400 text-[11px] mt-0.5">
                  Backend API credentials, Groq tokens, and file system paths are strictly isolated on the server. No client bundle or response contains sensitive credentials.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-2.5 bg-slate-950/60 rounded-lg p-3 border border-slate-800">
              <Shield className="w-4 h-4 text-teal-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-slate-200">Deterministic Closure Gate</p>
                <p className="text-slate-400 text-[11px] mt-0.5">
                  An incident can never be marked as resolved simply by completing an execution loop. Verified photographic post-repair closure evidence is mandatory.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-2.5 bg-slate-950/60 rounded-lg p-3 border border-slate-800">
              <Globe className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-slate-200">Simulated Municipal Demonstration</p>
                <p className="text-slate-400 text-[11px] mt-0.5">
                  All work orders, crew dispatch records, and material inventory states are simulated demonstrations. No real municipal crews are dispatched from this environment.
                </p>
              </div>
            </div>
          </div>

          {/* Connection Details */}
          <div className="rounded-lg border border-slate-800/80 bg-slate-950 p-3 space-y-1.5 font-mono text-[11px]">
            <div className="flex justify-between text-slate-400">
              <span>API Gateway:</span>
              <span className="text-teal-300">{api.getBaseUrl()}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Environment:</span>
              <span className="text-slate-200">{health?.environment || 'development'}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>CORS Policy:</span>
              <span className="text-slate-200">Configured for Frontend</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
