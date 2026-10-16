import { useState, useEffect, useCallback, lazy, Suspense } from 'react';
import { Navbar, type ActiveTab } from './components/layout/Navbar';
import { Footer } from './components/layout/Footer';
import { api } from './services/api';
import type { HealthResponse, Incident } from './types/api';
import { AlertCircle, RefreshCw, Loader2 } from 'lucide-react';

const DashboardView = lazy(() => import('./components/overview/DashboardView').then(m => ({ default: m.DashboardView })));
const IncidentExplorerView = lazy(() => import('./components/explorer/IncidentExplorerView').then(m => ({ default: m.IncidentExplorerView })));
const CitizenSubmissionForm = lazy(() => import('./components/submission/CitizenSubmissionForm').then(m => ({ default: m.CitizenSubmissionForm })));
const IncidentWorkspaceView = lazy(() => import('./components/workspace/IncidentWorkspaceView').then(m => ({ default: m.IncidentWorkspaceView })));
const AgentCommandCenterView = lazy(() => import('./components/command/AgentCommandCenterView').then(m => ({ default: m.AgentCommandCenterView })));
const SimulationLabView = lazy(() => import('./components/simulation/SimulationLabView').then(m => ({ default: m.SimulationLabView })));
const MLModelLabView = lazy(() => import('./components/ml/MLModelLabView').then(m => ({ default: m.MLModelLabView })));

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

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-teal-500/30 selection:text-teal-200">
      {/* Top Navbar */}
      <Navbar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        health={health}
        onRefreshHealth={checkHealth}
      />

      {/* Backend Offline Warning Banner */}
      {backendOffline && (
        <div className="bg-rose-950/80 border-b border-rose-800/80 px-4 py-2.5 text-rose-200 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2 max-w-5xl mx-auto w-full">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>
              <strong>Cannot connect to JanSetu AI Backend at {api.getBaseUrl()}.</strong> Ensure the FastAPI server is running (<code className="font-mono bg-rose-900/60 px-1 py-0.5 rounded">uvicorn app.main:app --port 8000</code>).
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
        <Suspense
          fallback={
            <div className="flex flex-col items-center justify-center py-24 text-slate-400">
              <Loader2 className="w-8 h-8 text-teal-400 animate-spin mb-3" />
              <span className="text-xs uppercase tracking-widest font-semibold text-slate-400">
                Loading JanSetu Component...
              </span>
            </div>
          }
        >
          {activeTab === 'operations' && (
            <DashboardView
              key={`dashboard-${refreshTrigger}`}
              onSelectIncident={handleSelectIncident}
              onNavigateToIntake={() => setActiveTab('submit')}
            />
          )}

          {activeTab === 'explorer' && (
            <IncidentExplorerView
              key={`explorer-${refreshTrigger}`}
              onSelectIncident={handleSelectIncident}
              onOpenCommandCenter={handleOpenCommandCenter}
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

          {activeTab === 'ml-lab' && (
            <MLModelLabView />
          )}
        </Suspense>
      </main>

      {/* Global Footer */}
      <Footer />
    </div>
  );
}
