import React from 'react';
import { ShieldAlert, Terminal } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="w-full border-t border-slate-900 bg-slate-950 py-6 px-4 text-xs text-slate-500">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-500/80" />
          <span>
            <strong className="text-slate-400 font-semibold">Demonstration & PoC Mode:</strong> All incident records, crews, resource estimates, and intervention closures are deterministic simulations. No real municipal repair crews are dispatched.
          </span>
        </div>
        <div className="flex items-center gap-4 text-[11px] font-mono text-slate-500">
          <span className="flex items-center gap-1">
            <Terminal className="w-3.5 h-3.5 text-teal-500" />
            LangGraph 6-Specialist Mesh
          </span>
          <span>•</span>
          <span>FastAPI + SQLite Persistence</span>
          <span>•</span>
          <span>Groq Vision Integration</span>
        </div>
      </div>
    </footer>
  );
};
