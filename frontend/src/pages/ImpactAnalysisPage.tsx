import React, { useState, useEffect } from 'react';
import { PageWrapper } from '../components/PageWrapper';
import {
  RotateCcw,
  Zap,
  Bell,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  RefreshCw,
  FileText,
  Layers,
  ArrowRight
} from 'lucide-react';
import { apiGet, apiPost } from '../utils/apiClient';

interface ReScreeningJob {
  job_id: string;
  trigger_type: string;
  trigger_source_id: string;
  patient_id?: string;
  trial_id?: string;
  idempotency_key: string;
  status: string;
  retry_count: number;
  max_retries: number;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

interface CoordinatorNotification {
  notification_id: string;
  job_id: string;
  patient_id: string;
  trial_id: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export const ImpactAnalysisPage: React.FC = () => {
  const [jobs, setJobs] = useState<ReScreeningJob[]>([]);
  const [notifications, setNotifications] = useState<CoordinatorNotification[]>([]);

  // Trigger Form State
  const [triggerType, setTriggerType] = useState<string>('new_lab');
  const [triggerSourceId, setTriggerSourceId] = useState<string>('lab-anc-update-999');
  const [targetPatientId, setTargetPatientId] = useState<string>('11111111-1111-1111-1111-111111111111');
  const [targetTrialId, setTargetTrialId] = useState<string>('t-nct04500000');

  const [loading, setLoading] = useState<boolean>(false);

  const fetchJobsAndNotifications = async () => {
    setLoading(true);
    try {
      const [jobsRes, notifRes] = await Promise.all([
        apiGet<ReScreeningJob[]>('/rescreening/jobs'),
        apiGet<CoordinatorNotification[]>('/rescreening/notifications')
      ]);

      if (jobsRes.data) setJobs(jobsRes.data);
      if (notifRes.data) setNotifications(notifRes.data);
    } catch (err) {
      console.error('Failed to load rescreening data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobsAndNotifications();
  }, []);

  const handleTriggerAndExecute = async () => {
    setLoading(true);
    try {
      const triggerRes = await apiPost<ReScreeningJob>('/rescreening/trigger', {
        trigger_type: triggerType,
        trigger_source_id: triggerSourceId,
        patient_id: targetPatientId,
        trial_id: targetTrialId
      });

      if (triggerRes.data) {
        const jobId = triggerRes.data.job_id;
        await apiPost(`/rescreening/execute/${jobId}`);
        fetchJobsAndNotifications();
      }
    } catch (err) {
      console.error('Error triggering re-screening job', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageWrapper
      title="Criteria Change Impact & Automatic Re-Screening"
      subtitle="Idempotent event-driven re-screening, historical screening run preservation, and coordinator notifications."
      moduleName="modules/rescreening"
      icon={RotateCcw}
    >
      <div className="space-y-6">
        {/* Trigger Event Control Panel */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
          <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
            <Zap className="h-5 w-5 text-amber-400" />
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wide">Trigger Automatic Re-Screening Event</h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs">
            <div>
              <label className="text-slate-400 block mb-1">Trigger Event Source:</label>
              <select
                value={triggerType}
                onChange={(e) => setTriggerType(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2.5"
              >
                <option value="new_lab">New Lab Report</option>
                <option value="new_biomarker">New Biomarker Result</option>
                <option value="criterion_change">Protocol Criterion Edit</option>
                <option value="fact_change">Clinical Fact Update</option>
                <option value="new_document">New Document Uploaded</option>
              </select>
            </div>

            <div>
              <label className="text-slate-400 block mb-1">Trigger Source ID:</label>
              <input
                type="text"
                value={triggerSourceId}
                onChange={(e) => setTriggerSourceId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2.5 font-mono"
              />
            </div>

            <div>
              <label className="text-slate-400 block mb-1">Target Patient:</label>
              <select
                value={targetPatientId}
                onChange={(e) => setTargetPatientId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2.5"
              >
                <option value="11111111-1111-1111-1111-111111111111">MRN-1001</option>
                <option value="22222222-2222-2222-2222-222222222222">MRN-1002</option>
              </select>
            </div>

            <div>
              <label className="text-slate-400 block mb-1">Protocol Trial ID:</label>
              <select
                value={targetTrialId}
                onChange={(e) => setTargetTrialId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2.5"
              >
                <option value="t-nct04500000">NCT04500000</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={handleTriggerAndExecute}
              disabled={loading}
              className="flex items-center space-x-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs px-6 py-2.5 rounded-lg transition"
            >
              <Zap className="h-4 w-4" />
              <span>{loading ? 'Processing Re-Screening...' : 'Trigger & Execute Re-Screening'}</span>
            </button>
          </div>
        </div>

        {/* Coordinator Notifications Alert Feed */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-2">
              <Bell className="h-5 w-5 text-rose-400" />
              <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wide">Coordinator Notifications Feed</h3>
            </div>
            <span className="bg-rose-950 text-rose-300 border border-rose-800 text-[10px] font-bold px-2 py-0.5 rounded">
              {notifications.length} Alerts
            </span>
          </div>

          {notifications.length === 0 ? (
            <p className="text-xs text-slate-400 py-4 italic">No coordinator notifications recorded yet.</p>
          ) : (
            <div className="space-y-3">
              {notifications.map((n) => (
                <div key={n.notification_id} className="bg-slate-950 border border-slate-800 p-4 rounded-xl space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-rose-300">{n.title}</span>
                    <span className="font-mono text-[10px] text-slate-500">{n.created_at}</span>
                  </div>
                  <p className="text-slate-300">{n.message}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Re-Screening Jobs Queue Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-2">
              <Layers className="h-5 w-5 text-sky-400" />
              <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wide">Re-Screening Jobs Monitor</h3>
            </div>

            <button
              onClick={fetchJobsAndNotifications}
              className="flex items-center space-x-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs px-3 py-1.5 rounded transition"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Refresh Queue</span>
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                  <th className="py-2.5 px-3">Job ID</th>
                  <th className="py-2.5 px-3">Trigger Type</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Idempotency Key</th>
                  <th className="py-2.5 px-3">Retries</th>
                  <th className="py-2.5 px-3">Created At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                {jobs.map((j) => (
                  <tr key={j.job_id} className="hover:bg-slate-800/40">
                    <td className="py-3 px-3 font-bold text-sky-400">{j.job_id.slice(0, 12)}...</td>
                    <td className="py-3 px-3">{j.trigger_type}</td>
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded uppercase font-bold text-[10px] border ${
                        j.status === 'completed' ? 'bg-emerald-950 text-emerald-300 border-emerald-800' :
                        j.status === 'failed' ? 'bg-rose-950 text-rose-300 border-rose-800' :
                        'bg-amber-950 text-amber-300 border-amber-800'
                      }`}>
                        {j.status}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-[10px] text-slate-400">{j.idempotency_key}</td>
                    <td className="py-3 px-3">{j.retry_count}/{j.max_retries}</td>
                    <td className="py-3 px-3 text-slate-400">{j.created_at?.slice(0, 19)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
};
