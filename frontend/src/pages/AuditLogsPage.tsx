import React, { useEffect, useState } from 'react';
import { PageWrapper } from '../components/PageWrapper';
import { ScrollText, ShieldCheck, Lock, Activity } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { BASE_URL } from '../utils/apiClient';

export const AuditLogsPage: React.FC = () => {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuth();

  useEffect(() => {
    fetch(`${BASE_URL}/api/v1/audit/logs`, {
      headers: {
        'X-User-Email': user?.email || '',
        'X-User-Role': user?.role || '',
      },
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (data.success && Array.isArray(data.data)) {
          setLogs(data.data);
        } else {
          setError(data.error || 'Failed to load audit trail');
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [user]);

  const getActionBadge = (action: string) => {
    switch (action) {
      case 'AUTHENTICATION':
        return <span className="bg-blue-950/80 text-blue-400 border border-blue-800 px-2 py-0.5 rounded text-[10px] font-mono font-semibold">AUTHENTICATION</span>;
      case 'DATA_CHANGE':
        return <span className="bg-emerald-950/80 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded text-[10px] font-mono font-semibold">DATA_CHANGE</span>;
      case 'SCREENING_RUN':
        return <span className="bg-cyan-950/80 text-cyan-400 border border-cyan-800 px-2 py-0.5 rounded text-[10px] font-mono font-semibold">SCREENING_RUN</span>;
      case 'REVIEW_SUBMIT':
        return <span className="bg-amber-950/80 text-amber-400 border border-amber-800 px-2 py-0.5 rounded text-[10px] font-mono font-semibold">REVIEW_SUBMIT</span>;
      case 'EXTRACTION_APPROVAL':
        return <span className="bg-purple-950/80 text-purple-400 border border-purple-800 px-2 py-0.5 rounded text-[10px] font-mono font-semibold">EXTRACTION_APPROVAL</span>;
      default:
        return <span className="bg-slate-800 text-slate-300 border border-slate-700 px-2 py-0.5 rounded text-[10px] font-mono font-semibold">{action}</span>;
    }
  };

  return (
    <PageWrapper
      title="Immutable Governance & Audit Logs"
      subtitle="100% decision traceability audit trail recording system actions, user roles, snapshots, and timestamps."
      moduleName="modules/audit"
      icon={ScrollText}
    >
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="flex items-center space-x-3">
            <ShieldCheck className="w-6 h-6 text-emerald-400" />
            <div>
              <h3 className="text-lg font-semibold text-white">System Compliance Audit Ledger</h3>
              <p className="text-xs text-slate-400">
                Audit records are append-only. Modification and deletion operations are prohibited by database policies.
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2 text-xs bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 text-emerald-400 font-mono">
            <Lock className="w-3.5 h-3.5" />
            <span>Traceability: 100%</span>
          </div>
        </div>

        {loading ? (
          <div className="text-xs text-slate-400 animate-pulse py-6 text-center">Loading audit log entries...</div>
        ) : error ? (
          <div className="bg-red-950/50 border border-red-800 text-red-300 p-4 rounded-lg text-xs">
            Failed to load audit logs: {error}
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center text-xs text-slate-400 py-8">No audit log records logged yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 uppercase font-mono border-b border-slate-800">
                <tr>
                  <th className="p-3">Timestamp</th>
                  <th className="p-3">Action</th>
                  <th className="p-3">Target Entity</th>
                  <th className="p-3">User ID</th>
                  <th className="p-3">Payload Snapshot</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-300">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-850 transition-colors">
                    <td className="p-3 font-mono text-slate-400 text-[11px]">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="p-3">{getActionBadge(log.action)}</td>
                    <td className="p-3 font-mono text-cyan-300">
                      {log.entityType}:{log.entityId ? log.entityId.slice(0, 8) : 'sys'}
                    </td>
                    <td className="p-3 font-mono text-slate-400 text-[11px]">
                      {log.userId ? log.userId.slice(0, 8) : 'system'}
                    </td>
                    <td className="p-3 font-mono text-[11px] text-slate-400 max-w-xs truncate">
                      {JSON.stringify(log.payload)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </PageWrapper>
  );
};
