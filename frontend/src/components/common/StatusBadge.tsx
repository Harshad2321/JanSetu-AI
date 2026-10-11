import React from 'react';
import type { OperationalStatus, EvidenceOutcome } from '../../types/api';

interface StatusBadgeProps {
  status: OperationalStatus | string;
  size?: 'sm' | 'md' | 'lg';
}

interface EvidenceBadgeProps {
  outcome: EvidenceOutcome | string;
  size?: 'sm' | 'md' | 'lg';
}

export const OperationalStatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-xs',
    lg: 'px-3 py-1.5 text-sm',
  }[size];

  switch (status) {
    case 'SIMULATED_RESOLVED':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-semibold rounded-full border border-emerald-500/40 bg-emerald-500/10 text-emerald-400 ${sizeClasses}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          SIMULATED RESOLVED
          <span className="text-[10px] font-normal tracking-wide px-1 rounded bg-emerald-950 text-emerald-300 border border-emerald-700/50">
            DEMO
          </span>
        </span>
      );
    case 'RESOLVED':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-semibold rounded-full border border-emerald-500/40 bg-emerald-500/10 text-emerald-400 ${sizeClasses}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          RESOLVED
        </span>
      );
    case 'CLOSURE_BLOCKED':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-semibold rounded-full border border-rose-500/40 bg-rose-500/10 text-rose-400 ${sizeClasses}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
          CLOSURE BLOCKED
        </span>
      );
    case 'TRIAGED':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full border border-teal-500/40 bg-teal-500/10 text-teal-300 ${sizeClasses}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-teal-400" />
          TRIAGED
        </span>
      );
    case 'PLANNING':
    case 'VALIDATING':
    case 'SIMULATING':
    case 'VERIFYING_CLOSURE':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full border border-sky-500/40 bg-sky-500/10 text-sky-300 ${sizeClasses}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-spin" />
          {status.replace('_', ' ')}
        </span>
      );
    case 'RECOVERING':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full border border-amber-500/40 bg-amber-500/10 text-amber-300 ${sizeClasses}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
          RECOVERING
        </span>
      );
    case 'ESCALATED':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-bold rounded-full border border-red-500/50 bg-red-500/15 text-red-400 ${sizeClasses}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
          ESCALATED
        </span>
      );
    case 'RECORDED_PENDING_REVIEW':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full border border-slate-700 bg-slate-800/80 text-slate-300 ${sizeClasses}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
          PENDING REVIEW
        </span>
      );
    case 'AWAITING_CLARIFICATION':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full border border-amber-500/40 bg-amber-500/10 text-amber-400 ${sizeClasses}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
          AWAITING CLARIFICATION
        </span>
      );
    case 'AWAITING_EVIDENCE_RETAKE':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full border border-amber-500/40 bg-amber-500/10 text-amber-400 ${sizeClasses}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
          RETAKE REQUESTED
        </span>
      );
    case 'DUPLICATE':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full border border-purple-500/40 bg-purple-500/10 text-purple-300 ${sizeClasses}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
          DUPLICATE
        </span>
      );
    default:
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full border border-slate-700 bg-slate-800 text-slate-300 ${sizeClasses}`}
        >
          {status}
        </span>
      );
  }
};

export const EvidenceStatusBadge: React.FC<EvidenceBadgeProps> = ({ outcome, size = 'md' }) => {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-xs',
    lg: 'px-3 py-1.5 text-sm',
  }[size];

  switch (outcome) {
    case 'MATCHED':
      return (
        <span
          className={`inline-flex items-center gap-1 font-semibold rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 ${sizeClasses}`}
        >
          <span className="text-[10px]">✓</span> PHOTO MATCHED
        </span>
      );
    case 'MISMATCH':
      return (
        <span
          className={`inline-flex items-center gap-1 font-semibold rounded-full border border-amber-500/40 bg-amber-500/10 text-amber-400 ${sizeClasses}`}
        >
          <span className="text-[10px]">⚠</span> PHOTO MISMATCH
        </span>
      );
    case 'LOW_QUALITY':
      return (
        <span
          className={`inline-flex items-center gap-1 font-medium rounded-full border border-amber-500/40 bg-amber-500/10 text-amber-300 ${sizeClasses}`}
        >
          <span className="text-[10px]">⚡</span> LOW QUALITY
        </span>
      );
    case 'INCONCLUSIVE':
      return (
        <span
          className={`inline-flex items-center gap-1 font-medium rounded-full border border-slate-700 bg-slate-800 text-slate-400 ${sizeClasses}`}
        >
          INCONCLUSIVE
        </span>
      );
    case 'NOT_PROVIDED':
    default:
      return (
        <span
          className={`inline-flex items-center gap-1 font-medium rounded-full border border-slate-800 bg-slate-900 text-slate-500 ${sizeClasses}`}
        >
          NO PHOTO
        </span>
      );
  }
};
