import React from 'react';
import { ShieldAlert, Terminal } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="w-full border-t border-[#E2E8F0] bg-white py-6 px-4 text-xs text-[#64748B] mt-auto">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
          <span>
            <strong className="text-[#172033] font-semibold">Demonstration & PoC Mode:</strong> All incident records, crews, resource estimates, and intervention closures are deterministic simulations. No real municipal repair crews are dispatched.
          </span>
        </div>
        <div className="flex items-center gap-3 text-[11px] font-mono text-[#64748B]">
          <span className="flex items-center gap-1.5 font-medium text-[#172033]">
            <Terminal className="w-3.5 h-3.5 text-[#0F766E]" />
            LangGraph 6-Specialist Mesh
          </span>
          <span className="text-[#94A3B8]">•</span>
          <span>FastAPI + SQLite Persistence</span>
          <span className="text-[#94A3B8]">•</span>
          <span>Groq Vision Integration</span>
        </div>
      </div>
    </footer>
  );
};
