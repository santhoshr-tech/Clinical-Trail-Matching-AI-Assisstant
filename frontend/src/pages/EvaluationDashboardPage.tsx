import React, { useState, useEffect } from 'react';
import { PageWrapper } from '../components/PageWrapper';
import {
  BarChart3,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  Terminal,
  Activity,
  Users,
  ShieldCheck,
  RefreshCw,
  Layers,
  FileCheck,
  FileText
} from 'lucide-react';
import { apiGet, apiPost } from '../utils/apiClient';

interface CategoryMetric {
  category: string;
  target_threshold_f1: number;
  measured_accuracy: number;
  measured_precision: number;
  measured_recall: number;
  measured_f1: number;
  measured_specificity: number;
  evidence_correctness: number;
  traceability_completeness: number;
  status: string;
  sample_count: number;
}

interface EvaluationReport {
  run_id: string;
  dataset_version: string;
  evaluated_at: string;
  total_test_cases: number;
  overall_f1: number;
  category_metrics: CategoryMetric[];
  reproducible_command: string;
}

interface DashboardMetrics {
  active_trials: number;
  total_patients_screened: number;
  potentially_eligible_count: number;
  not_eligible_count: number;
  manual_review_count: number;
  evidence_pending_count: number;
  conflict_cases_count: number;
  rescreening_jobs_count: number;
  agreement_rate: number;
  common_failed_criteria: Array<{ criterion: string; failed_count: number }>;
  missing_data_distribution: Record<string, number>;
  data_freshness_status: string;
}

export const EvaluationDashboardPage: React.FC = () => {
  const [dashboard, setDashboard] = useState<DashboardMetrics | null>(null);
  const [evalReport, setEvalReport] = useState<EvaluationReport | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const fetchDashboardAndEvaluation = async () => {
    setLoading(true);
    try {
      const [dashRes, evalRes] = await Promise.all([
        apiGet<DashboardMetrics>('/evaluation/dashboard'),
        apiGet<EvaluationReport>('/evaluation/run')
      ]);

      if (dashRes.data) setDashboard(dashRes.data);
      if (evalRes.data) setEvalReport(evalRes.data);
    } catch (err) {
      console.error('Error fetching evaluation data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardAndEvaluation();
  }, []);

  const handleRunEvaluationSuite = async () => {
    setLoading(true);
    try {
      const res = await apiPost<EvaluationReport>('/evaluation/run');
      if (res.data) setEvalReport(res.data);
    } catch (err) {
      console.error('Error running evaluation suite', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageWrapper
      title="Researcher Dashboard & Measured Evaluation"
      subtitle="Real-time site operational analytics and benchmark performance suite across 10 evaluation categories."
      moduleName="modules/evaluation"
      icon={BarChart3}
    >
      <div className="space-y-6">
        {/* Top Site Operations Metrics Cards */}
        {dashboard && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-slate-200">
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1 shadow">
              <span className="text-[10px] font-bold text-slate-400 uppercase">Active Trials</span>
              <div className="text-2xl font-black text-sky-400">{dashboard.active_trials}</div>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1 shadow">
              <span className="text-[10px] font-bold text-slate-400 uppercase">Patients Screened</span>
              <div className="text-2xl font-black text-slate-100">{dashboard.total_patients_screened}</div>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1 shadow">
              <span className="text-[10px] font-bold text-slate-400 uppercase">Potentially Eligible</span>
              <div className="text-2xl font-black text-emerald-400">{dashboard.potentially_eligible_count}</div>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1 shadow">
              <span className="text-[10px] font-bold text-slate-400 uppercase">AI-Human Agreement</span>
              <div className="text-2xl font-black text-emerald-400">{dashboard.agreement_rate}%</div>
            </div>
          </div>
        )}

        {/* Reproducible CLI Evaluation Command Banner */}
        <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4 font-mono text-xs shadow-lg">
          <div className="flex items-center space-x-3 text-slate-300">
            <Terminal className="h-5 w-5 text-emerald-400 flex-shrink-0" />
            <div>
              <span className="text-slate-500 block text-[10px] uppercase font-sans">Reproducible Evaluation Command</span>
              <span className="text-emerald-300 font-bold">py -m pytest backend/tests/test_phase16.py -s</span>
            </div>
          </div>

          <button
            onClick={handleRunEvaluationSuite}
            disabled={loading}
            className="flex items-center space-x-2 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs px-5 py-2.5 rounded-lg transition"
          >
            <Play className="h-4 w-4" />
            <span>{loading ? 'Executing Evaluation...' : 'Re-Run Evaluation Suite'}</span>
          </button>
        </div>

        {/* Evaluation Suite Benchmark Matrix */}
        {evalReport && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <ShieldCheck className="h-5 w-5 text-emerald-400" />
                <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wide">Measured Evaluation Suite (10 Categories)</h3>
              </div>

              <div className="flex items-center space-x-4 text-xs font-mono">
                <span className="text-slate-400">Dataset: <strong className="text-sky-300">{evalReport.dataset_version}</strong></span>
                <span className="text-slate-400">Overall F1: <strong className="text-emerald-400 font-black">{evalReport.overall_f1}</strong></span>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                    <th className="py-2.5 px-3">Evaluation Category</th>
                    <th className="py-2.5 px-3">Target F1</th>
                    <th className="py-2.5 px-3">Measured F1</th>
                    <th className="py-2.5 px-3">Accuracy</th>
                    <th className="py-2.5 px-3">Precision</th>
                    <th className="py-2.5 px-3">Recall</th>
                    <th className="py-2.5 px-3">Specificity</th>
                    <th className="py-2.5 px-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 font-mono text-[#172033]">
                  {evalReport.category_metrics.map((m) => (
                    <tr key={m.category} className="hover:bg-slate-50/80">
                      <td className="py-3.5 px-3 font-bold text-[#243247] text-xs capitalize font-sans">{m.category.replace(/_/g, ' ')}</td>
                      <td className="py-3.5 px-3 text-[#64748B] font-medium">≥ {m.target_threshold_f1}</td>
                      <td className="py-3.5 px-3 font-black text-emerald-600 text-sm">{m.measured_f1}</td>
                      <td className="py-3.5 px-3 text-[#172033] font-semibold">{m.measured_accuracy}</td>
                      <td className="py-3.5 px-3 text-[#172033] font-semibold">{m.measured_precision}</td>
                      <td className="py-3.5 px-3 text-[#172033] font-semibold">{m.measured_recall}</td>
                      <td className="py-3.5 px-3 text-[#172033] font-semibold">{m.measured_specificity}</td>
                      <td className="py-3.5 px-3">
                        <span className={`px-2.5 py-1 rounded-full uppercase font-bold text-[10px] border ${
                          m.status === 'achieved' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                          m.status === 'not_achieved' ? 'bg-rose-50 text-rose-700 border-rose-200' :
                          'bg-amber-50 text-amber-700 border-amber-200'
                        }`}>
                          {m.status.replace(/_/g, ' ')}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </PageWrapper>
  );
};
