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
    sm: 'px-2 py-0.5 text-[11px]',
    md: 'px-2.5 py-1 text-xs',
    lg: 'px-3 py-1.5 text-sm',
  }[size];

  switch (status) {
    case 'SIMULATED_RESOLVED':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-semibold rounded-full border border-teal-200/90 bg-teal-50 text-teal-800 shadow-2xs ${sizeClasses}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-[#0F766E] animate-pulse" />
          SIMULATED RESOLVED
          <span className="text-[10px] font-mono font-medium tracking-wide px-1.5 py-0.2 rounded-full bg-teal-100/90 text-teal-800 border border-teal-200">
            DEMO
          </span>
        </span>
      );
    case 'RESOLVED':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-semibold rounded-full border border-emerald-200 bg-emerald-50 text-emerald-800 shadow-2xs ${sizeClasses}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
          RESOLVED
        </span>
      );
    case 'CLOSURE_BLOCKED':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-semibold rounded-full border border-rose-200 bg-rose-50 text-rose-800 shadow-2xs ${sizeClasses}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-rose-600" />
          CLOSURE BLOCKED
        </span>
      );
    case 'TRIAGED':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full border border-teal-200 bg-teal-50 text-teal-800 shadow-2xs ${sizeClasses}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-[#0F766E]" />
          TRIAGED
        </span>
      );
    case 'PLANNING':
    case 'VALIDATING':
    case 'SIMULATING':
    case 'VERIFYING_CLOSURE':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full border border-blue-200 bg-blue-50 text-blue-800 shadow-2xs ${sizeClasses}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-spin" />
          {status.replace('_', ' ')}
        </span>
      );
    case 'RECOVERING':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full border border-amber-200 bg-amber-50 text-amber-800 shadow-2xs ${sizeClasses}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-amber-600" />
          RECOVERING
        </span>
      );
    case 'ESCALATED':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-bold rounded-full border border-red-200 bg-red-50 text-red-800 shadow-2xs ${sizeClasses}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-red-600" />
          ESCALATED
        </span>
      );
    case 'RECORDED_PENDING_REVIEW':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full border border-slate-200 bg-slate-100 text-slate-700 shadow-2xs ${sizeClasses}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
          PENDING REVIEW
        </span>
      );
    case 'AWAITING_CLARIFICATION':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full border border-amber-200 bg-amber-50 text-amber-800 shadow-2xs ${sizeClasses}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-amber-600" />
          AWAITING CLARIFICATION
        </span>
      );
    case 'AWAITING_EVIDENCE_RETAKE':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full border border-amber-200 bg-amber-50 text-amber-800 shadow-2xs ${sizeClasses}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-amber-600" />
          RETAKE REQUESTED
        </span>
      );
    case 'DUPLICATE':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full border border-purple-200 bg-purple-50 text-purple-800 shadow-2xs ${sizeClasses}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-purple-600" />
          DUPLICATE
        </span>
      );
    default:
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full border border-slate-200 bg-slate-100 text-slate-700 shadow-2xs ${sizeClasses}`}
        >
          {status}
        </span>
      );
  }
};

export const EvidenceStatusBadge: React.FC<EvidenceBadgeProps> = ({ outcome, size = 'md' }) => {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-[11px]',
    md: 'px-2.5 py-1 text-xs',
    lg: 'px-3 py-1.5 text-sm',
  }[size];

  switch (outcome) {
    case 'MATCHED':
      return (
        <span
          className={`inline-flex items-center gap-1 font-semibold rounded-full border border-emerald-200 bg-emerald-50 text-emerald-800 shadow-2xs ${sizeClasses}`}
        >
          <span className="text-[10px] text-emerald-600">✓</span> PHOTO MATCHED
        </span>
      );
    case 'MISMATCH':
      return (
        <span
          className={`inline-flex items-center gap-1 font-semibold rounded-full border border-amber-200 bg-amber-50 text-amber-800 shadow-2xs ${sizeClasses}`}
        >
          <span className="text-[10px] text-amber-600">⚠</span> PHOTO MISMATCH
        </span>
      );
    case 'LOW_QUALITY':
      return (
        <span
          className={`inline-flex items-center gap-1 font-medium rounded-full border border-amber-200 bg-amber-50 text-amber-800 shadow-2xs ${sizeClasses}`}
        >
          <span className="text-[10px] text-amber-600">⚡</span> LOW QUALITY
        </span>
      );
    case 'INCONCLUSIVE':
      return (
        <span
          className={`inline-flex items-center gap-1 font-medium rounded-full border border-slate-200 bg-slate-100 text-slate-600 shadow-2xs ${sizeClasses}`}
        >
          INCONCLUSIVE
        </span>
      );
    case 'NOT_PROVIDED':
    default:
      return (
        <span
          className={`inline-flex items-center gap-1 font-medium rounded-full border border-slate-200 bg-slate-50 text-slate-500 shadow-2xs ${sizeClasses}`}
        >
          NO PHOTO
        </span>
      );
  }
};
