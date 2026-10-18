import React, { useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Cpu,
  Layers,
  MapPin,
  Menu,
  PlayCircle,
  Search,
  X,
} from 'lucide-react';
import type { HealthResponse } from '../../types/api';

export type ActiveTab =
  | 'operations'
  | 'explorer'
  | 'submit'
  | 'workspace'
  | 'command-center'
  | 'simulation-lab'
  | 'ml-lab';

interface NavbarProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  health: HealthResponse | null;
  onRefreshHealth: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onTabChange,
  health,
  onRefreshHealth,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems: { id: ActiveTab; label: string; icon: React.ReactNode }[] = [
    { id: 'operations', label: 'Operations', icon: <Layers className="w-3.5 h-3.5" /> },
    { id: 'explorer', label: 'Incident Explorer', icon: <Search className="w-3.5 h-3.5" /> },
    { id: 'submit', label: 'Report Incident', icon: <MapPin className="w-3.5 h-3.5" /> },
    { id: 'workspace', label: 'Civic Twin', icon: <AlertTriangle className="w-3.5 h-3.5" /> },
    { id: 'command-center', label: 'Agent Operations', icon: <Activity className="w-3.5 h-3.5" /> },
    { id: 'simulation-lab', label: 'Simulation Lab', icon: <PlayCircle className="w-3.5 h-3.5" /> },
    { id: 'ml-lab', label: 'ML Model Lab', icon: <Cpu className="w-3.5 h-3.5" /> },
  ];

  const isHealthy = health?.status === 'healthy';

  return (
    <header className="sticky top-0 z-40 w-full border-b border-[#E2E8F0] bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/90 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Product Title */}
          <div
            onClick={() => onTabChange('operations')}
            className="flex items-center gap-3 cursor-pointer shrink-0 group"
          >
            <div className="w-8 h-8 rounded-lg bg-[#0F766E] flex items-center justify-center shadow-sm shadow-teal-900/10 transition-transform group-hover:scale-105">
              <span className="font-extrabold text-xs tracking-wider text-white">JS</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold tracking-tight text-base text-[#172033]">JANSETU AI</span>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-teal-50 text-[#0F766E] border border-teal-200/80 font-medium">
                  Command Center
                </span>
              </div>
              <p className="text-[11px] text-[#64748B] font-medium tracking-tight">Adaptive Civic Incident Resolution</p>
            </div>
          </div>

          {/* Desktop Navigation Tabs */}
          <nav className="hidden xl:flex items-center space-x-1">
            {navItems.map((item) => {
              const active = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onTabChange(item.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    active
                      ? 'bg-[#CCFBF1] text-[#0F766E] font-semibold border border-teal-200/70 shadow-2xs'
                      : 'text-[#64748B] hover:text-[#172033] hover:bg-slate-100/80 border border-transparent'
                  }`}
                >
                  <span className={active ? 'text-[#0F766E]' : 'text-[#64748B]'}>{item.icon}</span>
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* System Health Status Indicator */}
          <div className="hidden sm:flex items-center gap-2">
            <button
              onClick={onRefreshHealth}
              className="flex items-center gap-2 px-3 py-1 rounded-full text-xs border border-[#E2E8F0] bg-[#F8FAFC] hover:bg-slate-100 hover:border-slate-300 transition-all shadow-2xs cursor-pointer"
              title="Click to check API health"
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  isHealthy ? 'bg-[#16A34A] shadow-xs shadow-emerald-500/50' : 'bg-[#DC2626]'
                }`}
              />
              <span className="text-[11px] text-[#172033] font-medium">
                {isHealthy ? 'Backend Live' : 'Offline'}
              </span>
            </button>
          </div>

          {/* Mobile Hamburger Button */}
          <div className="flex xl:hidden items-center gap-2">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-[#64748B] hover:text-[#172033] hover:bg-slate-100 border border-[#E2E8F0]"
              aria-label="Toggle Navigation Menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="xl:hidden border-t border-[#E2E8F0] bg-white px-4 pt-2 pb-4 space-y-1 shadow-md">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => {
                onTabChange(item.id);
                setMobileMenuOpen(false);
              }}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium text-left transition-colors ${
                activeTab === item.id
                  ? 'bg-[#CCFBF1] text-[#0F766E] font-bold border border-teal-200/70'
                  : 'text-[#64748B] hover:text-[#172033] hover:bg-slate-100'
              }`}
            >
              <span className={activeTab === item.id ? 'text-[#0F766E]' : 'text-[#64748B]'}>{item.icon}</span>
              {item.label}
            </button>
          ))}
          <div className="pt-2 border-t border-[#E2E8F0] flex justify-between items-center text-xs text-[#64748B]">
            <span className="flex items-center gap-1.5 font-medium">
              <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-[#16A34A]' : 'bg-[#DC2626]'}`} />
              Status: {isHealthy ? 'Backend Live' : 'Offline'}
            </span>
            <button onClick={onRefreshHealth} className="text-[#0F766E] hover:underline font-medium">
              Refresh Health
            </button>
          </div>
        </div>
      )}
    </header>
  );
};
