import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error in component tree:', error, errorInfo);
  }

  private handleReload = () => {
    window.location.reload();
  };

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.href = '/';
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#F5F7FA] text-[#172033] flex items-center justify-center p-6 font-sans">
          <div className="max-w-md w-full p-8 rounded-2xl border border-[#E2E8F0] bg-white shadow-xl space-y-5 text-center">
            <div className="w-14 h-14 rounded-full bg-rose-50 border border-rose-200 flex items-center justify-center mx-auto text-rose-600">
              <AlertTriangle className="w-7 h-7" />
            </div>

            <div className="space-y-1.5">
              <h3 className="text-lg font-bold text-[#172033] tracking-tight">
                JanSetu AI Interface Guard
              </h3>
              <p className="text-xs text-slate-500">
                A component error was caught safely. No municipal data or incident progress was lost.
              </p>
            </div>

            {this.state.error && (
              <div className="p-3.5 rounded-lg bg-slate-50 border border-[#E2E8F0] text-left font-mono text-[11px] text-rose-800 max-h-32 overflow-y-auto">
                {this.state.error.message || String(this.state.error)}
              </div>
            )}

            <div className="flex justify-center gap-3 pt-2">
              <button
                onClick={this.handleReload}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-teal-700 hover:bg-teal-800 text-white flex items-center gap-2 shadow-xs transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Reload Application
              </button>
              <button
                onClick={this.handleReset}
                className="px-4 py-2 text-xs font-semibold rounded-lg border border-[#E2E8F0] bg-white text-slate-700 hover:bg-slate-50 flex items-center gap-2 shadow-xs transition-colors"
              >
                <Home className="w-3.5 h-3.5" />
                Return to Dashboard
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
