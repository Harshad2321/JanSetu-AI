import { useState, useEffect, useCallback } from 'react';
import { Navbar, type ActiveTab } from './components/layout/Navbar';
import { Footer } from './components/layout/Footer';
import { DashboardView } from './components/overview/DashboardView';
import { CitizenSubmissionForm } from './components/submission/CitizenSubmissionForm';
import { IncidentWorkspaceView } from './components/workspace/IncidentWorkspaceView';
import { AgentCommandCenterView } from './components/command/AgentCommandCenterView';
import { SimulationLabView } from './components/simulation/SimulationLabView';
import { AuditTimelineView } from './components/audit/AuditTimelineView';
import { SystemHealthView } from './components/health/SystemHealthView';
import { api } from './services/api';
import type { HealthResponse, Incident } from './types/api';
import { AlertCircle, RefreshCw } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('operations');
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);
  const [backendOffline, setBackendOffline] = useState<boolean>(false);
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);

  const checkHealth = useCallback(async () => {
    setHealthLoading(true);
    try {
      const res = await api.getHealth();
      setHealth(res);
      setBackendOffline(false);
    } catch {
      setHealth(null);
      setBackendOffline(true);
    } finally {
      setHealthLoading(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  const handleSelectIncident = (id: string) => {
    setSelectedIncidentId(id);
    setActiveTab('workspace');
  };

  const handleOpenCommandCenter = (id: string) => {
    setSelectedIncidentId(id);
    setActiveTab('command-center');
  };

  const handleSubmissionSuccess = (incident: Incident) => {
    setSelectedIncidentId(incident.incident_id);
    setActiveTab('workspace');
    setRefreshTrigger((prev) => prev + 1);
  };

  const handleDemonstrationSeeded = () => {
    checkHealth();
    setRefreshTrigger((prev) => prev + 1);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-teal-500/30 selection:text-teal-200">
      {/* Top Navbar */}
      <Navbar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        health={health}
        onRefreshHealth={checkHealth}
        onSeeded={handleDemonstrationSeeded}
      />

      {/* Backend Offline Warning Banner */}
      {backendOffline && (
        <div className="bg-rose-950/80 border-b border-rose-800/80 px-4 py-2.5 text-rose-200 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2 max-w-5xl mx-auto w-full">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>
              <strong>Cannot connect to JanSetu AI Backend at {api.getBaseUrl()}.</strong> Ensure the FastAPI server is running (`uvicorn app.main:app --port 8000`).
            </span>
            <button
              onClick={checkHealth}
              disabled={healthLoading}
              className="ml-auto inline-flex items-center gap-1 px-2.5 py-1 bg-rose-900 hover:bg-rose-800 text-white rounded text-[11px] font-medium transition-colors"
            >
              <RefreshCw className={`w-3 h-3 ${healthLoading ? 'animate-spin' : ''}`} />
              Retry Connection
            </button>
          </div>
        </div>
      )}

      {/* Main View Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'operations' && (
          <DashboardView
            key={`dashboard-${refreshTrigger}`}
            onSelectIncident={handleSelectIncident}
            onNavigateToIntake={() => setActiveTab('submit')}
          />
        )}

        {activeTab === 'submit' && (
          <CitizenSubmissionForm onSuccess={handleSubmissionSuccess} />
        )}

        {activeTab === 'workspace' && (
          <IncidentWorkspaceView
            key={`workspace-${selectedIncidentId || 'default'}-${refreshTrigger}`}
            incidentId={selectedIncidentId}
            onSelectIncident={setSelectedIncidentId}
            onOpenCommandCenter={handleOpenCommandCenter}
          />
        )}

        {activeTab === 'command-center' && (
          <AgentCommandCenterView
            key={`command-${selectedIncidentId || 'default'}-${refreshTrigger}`}
            incidentId={selectedIncidentId}
            onSelectIncident={setSelectedIncidentId}
          />
        )}

        {activeTab === 'simulation-lab' && (
          <SimulationLabView
            key={`simulation-${selectedIncidentId || 'default'}-${refreshTrigger}`}
            incidentId={selectedIncidentId}
            onSelectIncident={setSelectedIncidentId}
          />
        )}

        {activeTab === 'audit' && (
          <AuditTimelineView
            key={`audit-${selectedIncidentId || 'default'}-${refreshTrigger}`}
            incidentId={selectedIncidentId}
            onSelectIncident={setSelectedIncidentId}
          />
        )}

        {activeTab === 'health' && (
          <SystemHealthView
            health={health}
            onRefreshHealth={checkHealth}
          />
        )}
      </main>

      {/* Global Footer */}
      <Footer />
    </div>
  );
}
