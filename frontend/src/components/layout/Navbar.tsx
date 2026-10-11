import React, { useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Database,
  Layers,
  MapPin,
  Menu,
  PlayCircle,
  RefreshCw,
  Sliders,
  X,
} from 'lucide-react';
import type { HealthResponse } from '../../types/api';
import { api } from '../../services/api';

export type ActiveTab =
  | 'operations'
  | 'submit'
  | 'workspace'
  | 'command-center'
  | 'simulation-lab'
  | 'audit'
  | 'health';

interface NavbarProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  health: HealthResponse | null;
  onRefreshHealth: () => void;
  onSeeded?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onTabChange,
  health,
  onRefreshHealth,
  onSeeded,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [seedNotice, setSeedNotice] = useState<string | null>(null);

  const navItems: { id: ActiveTab; label: string; icon: React.ReactNode }[] = [
    { id: 'operations', label: 'Operations Overview', icon: <Layers className="w-4 h-4" /> },
    { id: 'submit', label: 'Citizen Intake', icon: <MapPin className="w-4 h-4" /> },
    { id: 'workspace', label: 'Incident Workspace', icon: <AlertTriangle className="w-4 h-4" /> },
    { id: 'command-center', label: 'Agent Command Center', icon: <Activity className="w-4 h-4" /> },
    { id: 'simulation-lab', label: 'Simulation Lab', icon: <PlayCircle className="w-4 h-4" /> },
    { id: 'audit', label: 'Audit Timeline', icon: <Database className="w-4 h-4" /> },
    { id: 'health', label: 'System Health', icon: <Sliders className="w-4 h-4" /> },
  ];

  const handleSeed = async () => {
    setSeeding(true);
    setSeedNotice(null);
    try {
      const res = await api.seedDemonstrationData();
      setSeedNotice(res.message);
      if (onSeeded) onSeeded();
      setTimeout(() => setSeedNotice(null), 4000);
    } catch (err: any) {
      setSeedNotice(`Seed failed: ${err.message}`);
      setTimeout(() => setSeedNotice(null), 4000);
    } finally {
      setSeeding(false);
    }
  };

  const isHealthy = health?.status === 'healthy';

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-slate-950/95 backdrop-blur supports-[backdrop-filter]:bg-slate-950/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Product Title */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-teal-600 to-emerald-500 p-0.5 shadow-md shadow-teal-500/20">
              <div className="w-full h-full bg-slate-950 rounded-[7px] flex items-center justify-center">
                <span className="font-extrabold text-sm tracking-wider text-teal-400">JS</span>
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-black tracking-tight text-lg text-slate-100">JANSETU AI</span>
                <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-teal-500/10 text-teal-300 border border-teal-500/30">
                  Command Center
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium tracking-tight">Adaptive Civic Incident Resolution</p>
            </div>
          </div>

          {/* Desktop Navigation Tabs */}
          <nav className="hidden lg:flex items-center space-x-1">
            {navItems.map((item) => {
              const active = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onTabChange(item.id)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                    active
                      ? 'bg-teal-500/15 text-teal-300 border border-teal-500/40 shadow-sm shadow-teal-500/10'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
                  }`}
                >
                  {item.icon}
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* Right Action Bar */}
          <div className="hidden sm:flex items-center gap-3">
            {/* Seed Demo Button */}
            <button
              onClick={handleSeed}
              disabled={seeding}
              className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md border border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800 hover:text-white transition-colors disabled:opacity-50"
              title="Seed representative civic cases for demonstration"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-teal-400 ${seeding ? 'animate-spin' : ''}`} />
              {seeding ? 'Seeding...' : 'Seed Demo Data'}
            </button>

            {/* Health Indicator */}
            <div
              onClick={onRefreshHealth}
              className="cursor-pointer flex items-center gap-2 px-2.5 py-1 rounded-md text-xs border border-slate-800 bg-slate-900/60 hover:bg-slate-900"
              title="Click to re-check API health"
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
          <div className="flex lg:hidden items-center gap-2">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-md text-slate-400 hover:text-white hover:bg-slate-900"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Seed Notice Toast */}
      {seedNotice && (
        <div className="bg-teal-950/90 border-t border-b border-teal-500/40 px-4 py-2 text-center text-xs text-teal-200 animate-in fade-in">
          {seedNotice}
        </div>
      )}

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-t border-slate-800 bg-slate-950 px-4 pt-2 pb-4 space-y-1">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => {
                onTabChange(item.id);
                setMobileMenuOpen(false);
              }}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium text-left ${
                activeTab === item.id
                  ? 'bg-teal-500/15 text-teal-300 border border-teal-500/30'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900'
              }`}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
          <div className="pt-2 border-t border-slate-800 flex justify-between items-center">
            <button
              onClick={handleSeed}
              disabled={seeding}
              className="px-3 py-1.5 text-xs font-medium rounded border border-slate-700 bg-slate-900 text-slate-300"
            >
              {seeding ? 'Seeding...' : 'Seed Demo Data'}
            </button>
            <span className="text-xs text-slate-400 font-mono">
              {isHealthy ? '● API Connected' : '○ API Offline'}
            </span>
          </div>
        </div>
      )}
    </header>
  );
};
