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
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-slate-950/95 backdrop-blur supports-[backdrop-filter]:bg-slate-950/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Product Title */}
          <div
            onClick={() => onTabChange('operations')}
            className="flex items-center gap-3 cursor-pointer shrink-0"
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-teal-600 to-emerald-500 p-0.5 shadow-md shadow-teal-500/20">
              <div className="w-full h-full bg-slate-950 rounded-[6px] flex items-center justify-center">
                <span className="font-extrabold text-xs tracking-wider text-teal-400">JS</span>
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-black tracking-tight text-base text-slate-100">JANSETU AI</span>
                <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-teal-500/10 text-teal-300 border border-teal-500/30">
                  Command Center
                </span>
              </div>
              <p className="text-[10px] text-slate-400 font-medium tracking-tight">Adaptive Civic Incident Resolution</p>
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
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    active
                      ? 'bg-teal-500/15 text-teal-300 border border-teal-500/40 shadow-sm'
                      : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900'
                  }`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* System Health Status Indicator */}
          <div className="hidden sm:flex items-center gap-2">
            <div
              onClick={onRefreshHealth}
              className="cursor-pointer flex items-center gap-2 px-2.5 py-1 rounded-md text-xs border border-slate-800 bg-slate-900/60 hover:bg-slate-900 transition-colors"
              title="Click to check API health"
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  isHealthy ? 'bg-emerald-400 animate-pulse shadow-sm shadow-emerald-400' : 'bg-rose-500'
                }`}
              />
              <span className="text-[11px] text-slate-400 font-mono">
                {isHealthy ? 'Backend Live' : 'Offline'}
              </span>
            </div>
          </div>

          {/* Mobile Hamburger Button */}
          <div className="flex xl:hidden items-center gap-2">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-md text-slate-400 hover:text-white hover:bg-slate-900"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="xl:hidden border-t border-slate-800 bg-slate-950 px-4 pt-2 pb-4 space-y-1">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => {
                onTabChange(item.id);
                setMobileMenuOpen(false);
              }}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium text-left ${
                activeTab === item.id
                  ? 'bg-teal-500/15 text-teal-300 border border-teal-500/30 font-bold'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900'
              }`}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
          <div className="pt-2 border-t border-slate-800 flex justify-between items-center text-xs text-slate-400 font-mono">
            <span>Status: {isHealthy ? '● Backend Live' : '○ Offline'}</span>
            <button onClick={onRefreshHealth} className="text-teal-400 hover:underline">
              Refresh Health
            </button>
          </div>
        </div>
      )}
    </header>
  );
};
