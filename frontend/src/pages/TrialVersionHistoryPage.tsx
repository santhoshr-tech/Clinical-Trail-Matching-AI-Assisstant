import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { PageWrapper } from '../components/PageWrapper';
import { History, ArrowLeft, GitCommit, Clock, CheckCircle, Shield } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const TrialVersionHistoryPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [versions, setVersions] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuth();

  useEffect(() => {
    fetch(`/api/v1/trials/${id}/versions`, {
      headers: {
        'X-User-Email': user?.email || '',
        'X-User-Role': user?.role || '',
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success && Array.isArray(data.data)) {
          setVersions(data.data);
        } else {
          setError(data.error || 'Failed to fetch protocol version log');
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id, user]);

  return (
    <PageWrapper
      title="Protocol Version History Log"
      subtitle="Audit-compliant log of trial protocol amendments, metadata changes, and sync timestamps."
      moduleName="modules/protocols"
      icon={History}
    >
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Link
            to={`/trials/${id}`}
            className="inline-flex items-center space-x-1 text-xs text-cyan-400 hover:text-cyan-300 font-mono"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Return to Protocol Details</span>
          </Link>
        </div>

        {loading ? (
          <div className="text-center py-12 text-xs text-slate-400 animate-pulse">Loading protocol version log...</div>
        ) : error ? (
          <div className="bg-red-950/50 border border-red-800 text-red-300 p-4 rounded-xl text-xs">{error}</div>
        ) : versions.length === 0 ? (
          <div className="bg-slate-900 border border-slate-800 p-8 rounded-xl text-center text-xs text-slate-400">
            No version history logged for this protocol yet.
          </div>
        ) : (
          <div className="relative border-l-2 border-slate-800 ml-4 space-y-6 py-2">
            {versions.map((v, index) => (
              <div key={v.id} className="relative pl-6 space-y-2">
                {/* Node indicator */}
                <div className="absolute -left-2.5 top-0 w-5 h-5 rounded-full bg-slate-900 border-2 border-cyan-500 flex items-center justify-center">
                  <GitCommit className="w-3 h-3 text-cyan-400" />
                </div>

                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                    <div className="flex items-center space-x-3">
                      <span className="bg-cyan-950 text-cyan-300 border border-cyan-800 px-2.5 py-0.5 rounded text-xs font-mono font-bold">
                        Version {v.versionNumber}
                      </span>
                      {index === 0 && (
                        <span className="bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded text-[10px] font-mono">
                          LATEST ACTIVE
                        </span>
                      )}
                    </div>

                    <div className="flex items-center space-x-2 text-[11px] text-slate-400 font-mono">
                      <Clock className="w-3.5 h-3.5 text-slate-500" />
                      <span>Synced at: {v.syncedAt}</span>
                    </div>
                  </div>

                  <p className="text-xs text-slate-200 font-medium">{v.changeSummary}</p>

                  {/* Snapshot JSON Preview */}
                  <div>
                    <span className="text-[10px] text-slate-400 font-mono block mb-1">Version Snapshot Payload:</span>
                    <pre className="bg-slate-950 p-3 rounded text-[11px] font-mono text-cyan-400/90 overflow-x-auto border border-slate-800">
                      {JSON.stringify(JSON.parse(v.snapshotJson || '{}'), null, 2)}
                    </pre>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </PageWrapper>
  );
};

