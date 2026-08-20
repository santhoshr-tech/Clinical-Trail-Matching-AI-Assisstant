import React, { useState, useEffect } from 'react';
import { PageWrapper } from '../components/PageWrapper';
import {
  MessageSquare,
  BarChart3,
  Download,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ThumbsUp,
  ThumbsDown,
  ShieldCheck,
  Cpu,
  RefreshCw
} from 'lucide-react';
import { apiGet, apiPost } from '../utils/apiClient';

interface AnalyticsData {
  total_evaluations: number;
  agree_count: number;
  disagree_count: number;
  agreement_rate: number;
  disagreement_rate: number;
  false_pass_count: number;
  false_fail_count: number;
  category_breakdown: Record<string, number>;
  model_version_comparison: Record<string, { total: number; agree: number; disagree: number }>;
  most_disputed_criteria: Array<{ criterion_id: string; disagreement_count: number }>;
}

interface FeedbackRecord {
  feedback_id: string;
  patient_id: string;
  trial_id: string;
  criterion_id: string;
  ai_decision: string;
  human_decision: string;
  agreement_status: string;
  error_type: string;
  disagreement_category?: string;
  override_reason?: string;
  reviewer_id: string;
  model_version: string;
  prompt_version: string;
  created_at: string;
}

export const FeedbackAnalyticsPage: React.FC = () => {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [records, setRecords] = useState<FeedbackRecord[]>([]);

  // Submission Form State
  const [patientId, setPatientId] = useState<string>('11111111-1111-1111-1111-111111111111');
  const [trialId, setTrialId] = useState<string>('t-nct04500000');
  const [criterionId, setCriterionId] = useState<string>('crit-001');
  const [aiDecision, setAiDecision] = useState<string>('PASS');
  const [humanDecision, setHumanDecision] = useState<string>('FAIL');
  const [disagreementCategory, setDisagreementCategory] = useState<string>('extraction_error');
  const [overrideReason, setOverrideReason] = useState<string>('Source document explicitly indicates ANC is 0.8 10*3/uL, AI incorrectly extracted 2.8.');

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalyticsAndReviews = async () => {
    setLoading(true);
    try {
      const [anRes, recRes] = await Promise.all([
        apiGet<AnalyticsData>('/feedback/analytics'),
        apiGet<FeedbackRecord[]>('/feedback/reviews')
      ]);

      if (anRes.data) setAnalytics(anRes.data);
      if (recRes.data) setRecords(recRes.data);
    } catch (err) {
      console.error('Failed to load feedback analytics', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalyticsAndReviews();
  }, []);

  const handleSubmitFeedback = async () => {
    setLoading(true);
    setError(null);
    try {
      await apiPost('/feedback/submit', {
        patient_id: patientId,
        trial_id: trialId,
        criterion_id: criterionId,
        ai_decision: aiDecision,
        human_decision: humanDecision,
        disagreement_category: disagreementCategory,
        override_reason: overrideReason,
        reviewer_id: 'dr_investigator@clinicaltrial.ai',
        model_version: 'gemini-1.5-pro-v1',
        prompt_version: 'v2.1'
      });
      fetchAnalyticsAndReviews();
    } catch (err: any) {
      setError(err.message || 'Error submitting feedback');
    } finally {
      setLoading(false);
    }
  };

  const handleExportDeidentified = async () => {
    try {
      const res = await apiGet<any[]>('/feedback/export/deidentified');
      if (res.data) {
        const jsonStr = JSON.stringify(res.data, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `deidentified_evaluations_${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
      }
    } catch (err) {
      console.error('Export failed', err);
    }
  };

  return (
    <PageWrapper
      title="Researcher Feedback & Disagreement Analytics"
      subtitle="Track AI-human concordance rates, override categories, false-pass/fail metrics, and export evaluation datasets."
      moduleName="modules/feedback"
      icon={BarChart3}
    >
      <div className="space-y-6">
        {/* Metric Cards Banner */}
        {analytics && (
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-slate-200">
            <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl space-y-2 shadow">
              <span className="text-xs font-semibold text-slate-400 uppercase">Agreement Rate</span>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-black text-emerald-400">{analytics.agreement_rate}%</span>
                <span className="text-xs font-mono text-slate-400">{analytics.agree_count}/{analytics.total_evaluations}</span>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl space-y-2 shadow">
              <span className="text-xs font-semibold text-slate-400 uppercase">Disagreement Rate</span>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-black text-rose-400">{analytics.disagreement_rate}%</span>
                <span className="text-xs font-mono text-slate-400">{analytics.disagree_count}/{analytics.total_evaluations}</span>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl space-y-2 shadow">
              <span className="text-xs font-semibold text-slate-400 uppercase">False Pass Cases</span>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-black text-amber-400">{analytics.false_pass_count}</span>
                <span className="text-[10px] text-slate-500 uppercase font-mono">AI PASS / Human FAIL</span>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl space-y-2 shadow">
              <span className="text-xs font-semibold text-slate-400 uppercase">False Fail Cases</span>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-black text-purple-400">{analytics.false_fail_count}</span>
                <span className="text-[10px] text-slate-500 uppercase font-mono">AI FAIL / Human PASS</span>
              </div>
            </div>
          </div>
        )}

        {/* Feedback Submission & Override Form */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-2">
              <MessageSquare className="h-5 w-5 text-sky-400" />
              <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wide">Submit Reviewer Feedback / Decision Override</h3>
            </div>

            <button
              onClick={handleExportDeidentified}
              className="flex items-center space-x-1.5 bg-slate-800 hover:bg-slate-700 text-sky-300 font-semibold text-xs px-4 py-2 rounded-lg transition"
            >
              <Download className="h-4 w-4" />
              <span>Export De-Identified Data</span>
            </button>
          </div>

          {error && (
            <div className="bg-rose-950/60 border border-rose-800 text-rose-200 text-xs p-3 rounded-lg flex items-center space-x-2">
              <AlertTriangle className="h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs">
            <div>
              <label className="text-slate-400 block mb-1">Criterion ID:</label>
              <input
                type="text"
                value={criterionId}
                onChange={(e) => setCriterionId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2.5 font-mono"
              />
            </div>

            <div>
              <label className="text-slate-400 block mb-1">AI Decision:</label>
              <select
                value={aiDecision}
                onChange={(e) => setAiDecision(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2.5 font-bold"
              >
                <option value="PASS">PASS</option>
                <option value="FAIL">FAIL</option>
                <option value="UNKNOWN">UNKNOWN</option>
                <option value="CONFLICT">CONFLICT</option>
              </select>
            </div>

            <div>
              <label className="text-slate-400 block mb-1">Human Decision Override:</label>
              <select
                value={humanDecision}
                onChange={(e) => setHumanDecision(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2.5 font-bold"
              >
                <option value="PASS">PASS</option>
                <option value="FAIL">FAIL</option>
                <option value="UNKNOWN">UNKNOWN</option>
                <option value="CONFLICT">CONFLICT</option>
              </select>
            </div>

            <div>
              <label className="text-slate-400 block mb-1">Disagreement Category:</label>
              <select
                value={disagreementCategory}
                onChange={(e) => setDisagreementCategory(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2.5"
              >
                <option value="extraction_error">extraction_error</option>
                <option value="normalization_error">normalization_error</option>
                <option value="negation_error">negation_error</option>
                <option value="temporal_error">temporal_error</option>
                <option value="missing_data_error">missing_data_error</option>
                <option value="conflict_error">conflict_error</option>
                <option value="evidence_error">evidence_error</option>
                <option value="rule_error">rule_error</option>
                <option value="reviewer_error">reviewer_error</option>
                <option value="other">other</option>
              </select>
            </div>

            <div className="sm:col-span-4">
              <label className="text-slate-400 block mb-1">Mandatory Override Rationale (min 5 chars):</label>
              <textarea
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                rows={2}
                placeholder="Explain the clinical rationale for overriding the AI criterion decision..."
                className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2.5"
              />
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={handleSubmitFeedback}
              disabled={loading}
              className="bg-sky-500 hover:bg-sky-400 text-white font-bold text-xs px-6 py-2.5 rounded-lg transition"
            >
              {loading ? 'Submitting...' : 'Submit Feedback / Override'}
            </button>
          </div>
        </div>

        {/* Feedback Records Feed */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wide">Submitted Feedback Log</h3>
            <button onClick={fetchAnalyticsAndReviews} className="text-slate-400 hover:text-slate-200">
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                  <th className="py-2.5 px-3">Criterion</th>
                  <th className="py-2.5 px-3">AI Decision</th>
                  <th className="py-2.5 px-3">Human Decision</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Category</th>
                  <th className="py-2.5 px-3">Rationale</th>
                  <th className="py-2.5 px-3">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                {records.map((r) => (
                  <tr key={r.feedback_id} className="hover:bg-slate-800/40">
                    <td className="py-3 px-3 font-bold text-sky-400">{r.criterion_id}</td>
                    <td className="py-3 px-3 text-slate-400">{r.ai_decision}</td>
                    <td className="py-3 px-3 font-bold text-emerald-300">{r.human_decision}</td>
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold border ${
                        r.agreement_status === 'AGREE' ? 'bg-emerald-950 text-emerald-300 border-emerald-800' : 'bg-rose-950 text-rose-300 border-rose-800'
                      }`}>
                        {r.agreement_status}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-slate-400">{r.disagreement_category || 'N/A'}</td>
                    <td className="py-3 px-3 max-w-xs truncate text-slate-300">{r.override_reason || 'Agreed'}</td>
                    <td className="py-3 px-3 text-slate-500 text-[10px]">{r.created_at.slice(0, 19)}</td>
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
