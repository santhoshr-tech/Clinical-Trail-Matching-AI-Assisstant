import React, { useState, useEffect } from 'react';
import { PageWrapper } from '../components/PageWrapper';
import {
  AlertTriangle,
  FileText,
  CheckCircle,
  XCircle,
  HelpCircle,
  Layers,
  ArrowRightLeft,
  ShieldAlert,
  BarChart3,
  Award,
  RefreshCw
} from 'lucide-react';
import { apiGet, apiPost } from '../utils/apiClient';

interface SourceFactDetail {
  fact_id: string;
  document_id?: string;
  file_name: string;
  document_date: string;
  reliability_score: number;
  raw_value: string;
  normalized_value: string;
  is_negated: boolean;
}

interface ConflictCase {
  conflict_id: string;
  patient_id: string;
  category: string;
  description: string;
  source_a: SourceFactDetail;
  source_b: SourceFactDetail;
  status: string;
  resolution_reason?: string;
  resolved_by?: string;
  resolved_at?: string;
}

interface ConflictAnalytics {
  total_conflicts: number;
  unresolved_count: number;
  resolved_count: number;
  category_breakdown: Record<string, number>;
  average_resolution_time_hours: number;
}

export const ConflictResolverPage: React.FC = () => {
  const [patientId, setPatientId] = useState<string>('33333333-3333-3333-3333-333333333333');
  const [conflicts, setConflicts] = useState<ConflictCase[]>([]);
  const [analytics, setAnalytics] = useState<ConflictAnalytics | null>(null);
  const [selectedChoice, setSelectedChoice] = useState<'accept_a' | 'accept_b' | 'custom_correction' | 'mark_unresolved'>('accept_a');
  const [resolutionReason, setResolutionReason] = useState<string>('');
  const [customValue, setCustomValue] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchConflictData = async () => {
    setLoading(true);
    setError(null);
    try {
      const casesRes = await apiGet<ConflictCase[]>(`/conflicts/cases/patient/${patientId}`);
      if (casesRes.data) {
        setConflicts(casesRes.data);
      }
      
      const analyticsRes = await apiGet<ConflictAnalytics>('/conflicts/analytics');
      if (analyticsRes.data) {
        setAnalytics(analyticsRes.data);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load conflict cases');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConflictData();
  }, [patientId]);

  const handleResolve = async (conflictId: string) => {
    if (!resolutionReason || resolutionReason.trim().length < 5) {
      setError('A resolution reason (minimum 5 characters) is required to resolve a clinical conflict.');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await apiPost<any>('/conflicts/resolve', {
        conflict_id: conflictId,
        resolution_choice: selectedChoice,
        custom_corrected_value: selectedChoice === 'custom_correction' ? customValue : undefined,
        resolution_reason: resolutionReason
      });

      if (res.data) {
        setSuccessMsg(`Conflict resolved successfully as '${res.data.status}'. Eligibility re-screening triggered.`);
        setResolutionReason('');
        setCustomValue('');
        fetchConflictData();
      } else if (res.error) {
        setError(res.error);
      }
    } catch (err: any) {
      setError(err.message || 'Resolution failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageWrapper
      title="Clinical Evidence Conflict Resolver"
      subtitle="Resolve contradictory patient facts via controlled human workflow without deleting historical records."
      moduleName="modules/conflicts"
      icon={AlertTriangle}
    >
      <div className="space-y-6">
        {/* Analytics Header */}
        {analytics && (
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl shadow">
              <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Total Conflicts</span>
              <span className="text-2xl font-black text-slate-100">{analytics.total_conflicts}</span>
            </div>
            <div className="bg-slate-900 border border-purple-800/60 p-4 rounded-xl shadow">
              <span className="text-[10px] text-purple-400 font-bold uppercase tracking-wider block">Unresolved Conflicts</span>
              <span className="text-2xl font-black text-purple-400">{analytics.unresolved_count}</span>
            </div>
            <div className="bg-slate-900 border border-emerald-800/60 p-4 rounded-xl shadow">
              <span className="text-[10px] text-emerald-400 font-bold uppercase tracking-wider block">Resolved Conflicts</span>
              <span className="text-2xl font-black text-emerald-400">{analytics.resolved_count}</span>
            </div>
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl shadow">
              <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Avg Resolution Time</span>
              <span className="text-2xl font-black text-sky-400">{analytics.average_resolution_time_hours} hrs</span>
            </div>
          </div>
        )}

        {/* Patient selector bar */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-3 w-full sm:w-auto">
            <label className="text-xs font-semibold text-slate-400 uppercase">Target Patient Profile:</label>
            <select
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-sky-500 focus:outline-none"
            >
              <option value="33333333-3333-3333-3333-333333333333">MRN-1003 (Conflicting EGFR Biomarkers)</option>
              <option value="11111111-1111-1111-1111-111111111111">MRN-1001 (Pass - No Active Conflicts)</option>
            </select>
          </div>

          <button
            onClick={fetchConflictData}
            disabled={loading}
            className="flex items-center space-x-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs px-4 py-2.5 rounded-lg transition"
          >
            <RefreshCw className="h-4 w-4" />
            <span>Refresh Analytics</span>
          </button>
        </div>

        {error && (
          <div className="bg-rose-950/60 border border-rose-800 text-rose-300 p-4 rounded-xl text-xs flex items-center space-x-3">
            <AlertTriangle className="h-5 w-5 text-rose-400 flex-shrink-0" />
            <span className="font-semibold">{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="bg-emerald-950/60 border border-emerald-800 text-emerald-300 p-4 rounded-xl text-xs flex items-center space-x-3">
            <CheckCircle className="h-5 w-5 text-emerald-400 flex-shrink-0" />
            <span className="font-semibold">{successMsg}</span>
          </div>
        )}

        {/* Side-by-Side Conflict Comparison */}
        {conflicts.length === 0 ? (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-8 text-center text-slate-400 text-sm">
            No active evidence conflicts detected for this patient profile.
          </div>
        ) : (
          conflicts.map((caseItem) => (
            <div key={caseItem.conflict_id} className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div className="flex items-center space-x-3">
                  <ShieldAlert className="h-6 w-6 text-purple-400" />
                  <div>
                    <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wide">
                      Clinical Conflict: {caseItem.category}
                    </h3>
                    <p className="text-xs text-slate-400">{caseItem.description}</p>
                  </div>
                </div>

                <span className={`text-xs px-3 py-1 rounded-full font-bold uppercase border ${
                  caseItem.status === 'unresolved' ? 'bg-purple-950 text-purple-300 border-purple-500/40' :
                  'bg-emerald-950 text-emerald-300 border-emerald-500/40'
                }`}>
                  {caseItem.status}
                </span>
              </div>

              {/* Dual Pane Comparison Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Source A Card */}
                <div className="bg-slate-950 p-5 rounded-xl border border-slate-800 space-y-3 relative">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-sky-400 uppercase tracking-wider">Source Document A</span>
                    <span className="text-xs font-mono text-amber-400 font-bold">{(caseItem.source_a.reliability_score * 100).toFixed(0)}% Reliability</span>
                  </div>

                  <div className="text-xs space-y-1">
                    <div className="flex justify-between text-slate-400"><span>File:</span><span className="text-slate-200 font-mono">{caseItem.source_a.file_name}</span></div>
                    <div className="flex justify-between text-slate-400"><span>Date:</span><span className="text-slate-200">{caseItem.source_a.document_date}</span></div>
                  </div>

                  <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-slate-200">
                    <span className="text-[10px] text-slate-500 block uppercase mb-1">Raw Excerpt</span>
                    "{caseItem.source_a.raw_value}"
                  </div>

                  <div className="bg-slate-900 p-2.5 rounded border border-slate-800 text-xs">
                    <span className="text-[10px] text-slate-500 block uppercase font-semibold">Normalized Fact</span>
                    <strong className="text-emerald-300 font-mono">{caseItem.source_a.normalized_value}</strong>
                  </div>
                </div>

                {/* Source B Card */}
                <div className="bg-slate-950 p-5 rounded-xl border border-slate-800 space-y-3 relative">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-purple-400 uppercase tracking-wider">Source Document B</span>
                    <span className="text-xs font-mono text-amber-400 font-bold">{(caseItem.source_b.reliability_score * 100).toFixed(0)}% Reliability</span>
                  </div>

                  <div className="text-xs space-y-1">
                    <div className="flex justify-between text-slate-400"><span>File:</span><span className="text-slate-200 font-mono">{caseItem.source_b.file_name}</span></div>
                    <div className="flex justify-between text-slate-400"><span>Date:</span><span className="text-slate-200">{caseItem.source_b.document_date}</span></div>
                  </div>

                  <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-slate-200">
                    <span className="text-[10px] text-slate-500 block uppercase mb-1">Raw Excerpt</span>
                    "{caseItem.source_b.raw_value}"
                  </div>

                  <div className="bg-slate-900 p-2.5 rounded border border-slate-800 text-xs">
                    <span className="text-[10px] text-slate-500 block uppercase font-semibold">Normalized Fact</span>
                    <strong className="text-rose-300 font-mono">{caseItem.source_b.normalized_value}</strong>
                  </div>
                </div>
              </div>

              {/* Resolution Workflow Form */}
              <div className="bg-slate-950 p-5 rounded-xl border border-slate-800 space-y-4">
                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Controlled Resolution Action</h4>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <button
                    onClick={() => setSelectedChoice('accept_a')}
                    className={`p-3 rounded-lg border font-semibold text-center transition ${
                      selectedChoice === 'accept_a' ? 'bg-sky-950 border-sky-500 text-sky-300' : 'bg-slate-900 border-slate-800 text-slate-400'
                    }`}
                  >
                    Accept Source A
                  </button>
                  <button
                    onClick={() => setSelectedChoice('accept_b')}
                    className={`p-3 rounded-lg border font-semibold text-center transition ${
                      selectedChoice === 'accept_b' ? 'bg-purple-950 border-purple-500 text-purple-300' : 'bg-slate-900 border-slate-800 text-slate-400'
                    }`}
                  >
                    Accept Source B
                  </button>
                  <button
                    onClick={() => setSelectedChoice('custom_correction')}
                    className={`p-3 rounded-lg border font-semibold text-center transition ${
                      selectedChoice === 'custom_correction' ? 'bg-indigo-950 border-indigo-500 text-indigo-300' : 'bg-slate-900 border-slate-800 text-slate-400'
                    }`}
                  >
                    Custom Corrected Fact
                  </button>
                  <button
                    onClick={() => setSelectedChoice('mark_unresolved')}
                    className={`p-3 rounded-lg border font-semibold text-center transition ${
                      selectedChoice === 'mark_unresolved' ? 'bg-slate-800 border-slate-600 text-slate-300' : 'bg-slate-900 border-slate-800 text-slate-400'
                    }`}
                  >
                    Mark Unresolved
                  </button>
                </div>

                {selectedChoice === 'custom_correction' && (
                  <div>
                    <label className="text-xs text-slate-400 block mb-1">Custom Corrected Canonical Fact Value:</label>
                    <input
                      type="text"
                      value={customValue}
                      onChange={(e) => setCustomValue(e.target.value)}
                      placeholder="e.g. EGFR Mutation: POSITIVE (Confirmed on Biopsy 1)"
                      className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-lg p-2.5 focus:ring-2 focus:ring-sky-500 focus:outline-none"
                    />
                  </div>
                )}

                <div>
                  <label className="text-xs text-slate-400 block mb-1">
                    Mandatory Resolution Rationale & Clinical Rationale <span className="text-rose-400">*</span>:
                  </label>
                  <textarea
                    rows={2}
                    value={resolutionReason}
                    onChange={(e) => setResolutionReason(e.target.value)}
                    placeholder="Provide mandatory clinical reasoning for resolving this conflicting evidence..."
                    className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-lg p-2.5 focus:ring-2 focus:ring-sky-500 focus:outline-none"
                  />
                </div>

                <div className="flex justify-end">
                  <button
                    onClick={() => handleResolve(caseItem.conflict_id)}
                    disabled={loading}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs px-6 py-2.5 rounded-lg transition disabled:opacity-50"
                  >
                    {loading ? 'Submitting Resolution...' : 'Submit Resolution & Re-screen'}
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </PageWrapper>
  );
};
