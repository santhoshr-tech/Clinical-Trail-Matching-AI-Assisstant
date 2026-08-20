import React, { useEffect, useState } from 'react';
import { PageWrapper } from '../components/PageWrapper';
import { Settings, ShieldCheck, Cpu, Database, Globe } from 'lucide-react';
import { ProviderHealthStatus } from '../types';

export const SettingsPage: React.FC = () => {
  const [healthStatus, setHealthStatus] = useState<ProviderHealthStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/config/status')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (data.success && data.data) {
          setHealthStatus(data.data);
        } else {
          setError(data.error || 'Failed to fetch provider config status');
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const renderBadge = (status?: string) => {
    if (status === 'configured') {
      return <span className="bg-emerald-950/80 text-emerald-400 border border-emerald-800 px-2.5 py-0.5 rounded text-xs font-mono font-semibold">configured</span>;
    }
    if (status === 'invalid') {
      return <span className="bg-red-950/80 text-red-400 border border-red-800 px-2.5 py-0.5 rounded text-xs font-mono font-semibold">invalid</span>;
    }
    return <span className="bg-amber-950/80 text-amber-400 border border-amber-800 px-2.5 py-0.5 rounded text-xs font-mono font-semibold">missing</span>;
  };

  return (
    <PageWrapper
      title="Settings & AI Provider Health"
      subtitle="Inspect system configuration status (Sanitized outputs only: configured, missing, or invalid)."
      moduleName="core/config"
      icon={Settings}
    >
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
        <div className="flex items-center space-x-3 text-white border-b border-slate-800 pb-4">
          <ShieldCheck className="w-6 h-6 text-cyan-400" />
          <div>
            <h3 className="text-lg font-semibold">System Secret Security & Provider Status</h3>
            <p className="text-xs text-slate-400">
              Per security policy, API key values are never exposed or printed. All status calls report sanitized flags only.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="text-xs text-slate-400 animate-pulse py-4">Checking provider health status endpoint...</div>
        ) : error ? (
          <div className="bg-red-950/50 border border-red-800 text-red-300 p-4 rounded-lg text-xs">
            Failed to connect to backend configuration API: {error}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-slate-950 border border-slate-800 p-4 rounded-lg space-y-3">
              <div className="flex items-center space-x-2 text-cyan-300 font-semibold text-sm">
                <Cpu className="w-4 h-4" />
                <span>Active AI Provider Mode</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">AI_PROVIDER Environment:</span>
                <span className="font-mono text-cyan-400 font-bold uppercase">{healthStatus?.aiProvider || 'mock'}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Provider Health Status:</span>
                {renderBadge(healthStatus?.status)}
              </div>
            </div>

            <div className="bg-slate-950 border border-slate-800 p-4 rounded-lg space-y-3">
              <div className="flex items-center space-x-2 text-blue-300 font-semibold text-sm">
                <Globe className="w-4 h-4" />
                <span>External Integration Health</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Gemini API Key Config:</span>
                {renderBadge(healthStatus?.geminiStatus)}
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Ollama Local Instance:</span>
                {renderBadge(healthStatus?.ollamaStatus)}
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">ClinicalTrials.gov API v2:</span>
                {renderBadge(healthStatus?.clinicalTrialsApiStatus)}
              </div>
            </div>
          </div>
        )}
      </div>
    </PageWrapper>
  );
};
