import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertOctagon, RefreshCw } from 'lucide-react';

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
    console.error('Unhandled UI Error:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
          <div className="bg-slate-900 border border-red-500/40 rounded-xl p-6 max-w-lg w-full shadow-2xl space-y-4">
            <div className="flex items-center space-x-3 text-red-400">
              <AlertOctagon className="w-8 h-8 shrink-0" />
              <h2 className="text-xl font-bold">Application Render Error</h2>
            </div>
            <p className="text-sm text-slate-300">
              An unexpected error occurred while rendering this module. Safe state recovery is enabled.
            </p>
            <div className="bg-slate-950 p-3 rounded font-mono text-xs text-red-300 overflow-x-auto border border-slate-800">
              {this.state.error?.message || 'Unknown React component error'}
            </div>
            <button
              onClick={this.handleReset}
              className="w-full flex items-center justify-center space-x-2 bg-red-600 hover:bg-red-500 text-white font-medium py-2 px-4 rounded-lg transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Reload Workbench</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
