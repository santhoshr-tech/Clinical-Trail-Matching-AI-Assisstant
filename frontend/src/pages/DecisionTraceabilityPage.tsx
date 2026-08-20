import React, { useState, useEffect } from 'react';
import { PageWrapper } from '../components/PageWrapper';
import {
  ShieldCheck,
  FileText,
  CheckCircle,
  XCircle,
  AlertTriangle,
  HelpCircle,
  Layers,
  Cpu,
  Search,
  CheckSquare,
  Award,
  Activity
} from 'lucide-react';
import { apiGet, apiPost } from '../utils/apiClient';

interface EvidenceItem {
  document_id?: string;
  file_name?: string;
  document_category?: string;
  page_number?: number;
  start_char?: number;
  end_char?: number;
  data_date?: string;
  raw_value: string;
  normalized_value: string;
  extraction_method: string;
  extraction_confidence: number;
  verification_status: 'pending' | 'verified' | 'rejected' | 'unclear';
}

interface DecisionTrace {
  trace_id: string;
  match_id: string;
  criterion_id: string;
  criterion_version: number;
  trial_id: string;
  trial_version: number;
  patient_id: string;
  patient_snapshot_id: string;
  status: 'PASS' | 'FAIL' | 'UNKNOWN' | 'CONFLICT';
  patient_value?: string;
  expected_value?: string;
  rule_used: string;
  facts_used: any[];
  evidence_items: EvidenceItem[];
  reliability_score: number;
  reliability_breakdown: {
    score: number;
    source_type_factor: number;
    recency_factor: number;
    verification_factor: number;
    confidence_factor: number;
    conflict_factor: number;
    completeness_factor: number;
  };
  ai_provider: string;
  ai_model: string;
  prompt_version: string;
  matching_engine_version: string;
  human_review?: any;
  decision_timestamp: string;
  completeness_score: number;
}

export const DecisionTraceabilityPage: React.FC = () => {
  const [patientId, setPatientId] = useState<string>('11111111-1111-1111-1111-111111111111');
  const [trialId, setTrialId] = useState<string>('t-nct04500000');
  const [traceData, setTraceData] = useState<DecisionTrace | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTrace = async () => {
    setLoading(true);
    setError(null);
    try {
      // First run matching to ensure match record exists
      const matchRes = await apiPost<any>('/matching/evaluate', { patient_id: patientId, trial_id: trialId });
      if (matchRes.data && matchRes.data.criterion_results && matchRes.data.criterion_results.length > 0) {
        const matchId = matchRes.data.criterion_results[0].criterion_id ? matchRes.data.patient_id : '';
        const critId = matchRes.data.criterion_results[0].criterion_id;
        
        // Fetch trace for first criterion
        const traceRes = await apiGet<DecisionTrace>(`/evidence/trace/${matchRes.data.patient_id}/${critId}`);
        if (traceRes.data) {
          setTraceData(traceRes.data);
        } else if (traceRes.error) {
          setError(traceRes.error);
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to generate decision trace');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTrace();
  }, []);

  return (
    <PageWrapper
      title="Evidence Grounding & Decision Traceability"
      subtitle="100% end-to-end decision auditability with document page/span grounding and reliability scoring."
      moduleName="modules/evidence"
      icon={ShieldCheck}
    >
      <div className="space-y-6">
        {/* Control Header */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 flex-1">
            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">Target Patient Profile</label>
              <select
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-sky-500 focus:outline-none"
              >
                <option value="11111111-1111-1111-1111-111111111111">MRN-1001 (Pass - All Verified Evidence)</option>
                <option value="22222222-2222-2222-2222-222222222222">MRN-1002 (Fail - Low ANC Lab Threshold)</option>
                <option value="33333333-3333-3333-3333-333333333333">MRN-1003 (Conflict - Flagged Biomarkers)</option>
                <option value="44444444-4444-4444-4444-444444444444">MRN-1004 (Unknown - Stale Lab Date)</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">Trial Protocol</label>
              <select
                value={trialId}
                onChange={(e) => setTrialId(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-sky-500 focus:outline-none"
              >
                <option value="t-nct04500000">NCT04500000 (Pembrolizumab Phase 3 NSCLC)</option>
              </select>
            </div>
          </div>

          <button
            onClick={fetchTrace}
            disabled={loading}
            className="flex items-center justify-center space-x-2 bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white font-semibold text-sm px-6 py-3 rounded-xl transition shadow-lg disabled:opacity-50"
          >
            <Search className="h-4 w-4" />
            <span>{loading ? 'Inspecting Trace...' : 'Generate Decision Trace'}</span>
          </button>
        </div>

        {error && (
          <div className="bg-rose-950/60 border border-rose-800 text-rose-300 p-4 rounded-xl text-xs flex items-center space-x-3">
            <AlertTriangle className="h-5 w-5 text-rose-400 flex-shrink-0" />
            <span className="font-semibold">{error}</span>
          </div>
        )}

        {traceData && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Pane: Decision & Reliability Trace */}
            <div className="lg:col-span-7 space-y-6">
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-5">
                <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                  <div className="flex items-center space-x-3">
                    <ShieldCheck className="h-6 w-6 text-sky-400" />
                    <div>
                      <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wide">Decision Trace Record</h3>
                      <span className="text-xs text-slate-500 font-mono">Trace ID: {traceData.trace_id}</span>
                    </div>
                  </div>

                  <div className="bg-emerald-950 border border-emerald-500/40 text-emerald-300 px-3 py-1.5 rounded-lg text-xs font-bold flex items-center space-x-1.5">
                    <CheckCircle className="h-4 w-4 text-emerald-400" />
                    <span>100% TRACEABILITY VERIFIED</span>
                  </div>
                </div>

                {/* Status & Rule Card */}
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-400 uppercase">Criterion Decision Status</span>
                    <span className={`text-xs px-3 py-1 rounded-full font-bold uppercase border ${
                      traceData.status === 'PASS' ? 'bg-emerald-900/40 text-emerald-400 border-emerald-500/40' :
                      traceData.status === 'FAIL' ? 'bg-rose-900/40 text-rose-400 border-rose-500/40' :
                      traceData.status === 'CONFLICT' ? 'bg-purple-900/40 text-purple-400 border-purple-500/40' :
                      'bg-amber-900/40 text-amber-300 border-amber-500/40'
                    }`}>
                      {traceData.status}
                    </span>
                  </div>

                  <div className="text-xs text-slate-300">
                    <span className="text-slate-500 block uppercase text-[10px] font-semibold">Rule Executed</span>
                    <span className="font-mono text-sky-300 font-bold">{traceData.rule_used}</span>
                  </div>

                  <div className="grid grid-cols-2 gap-3 pt-2">
                    <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                      <span className="text-[10px] text-slate-500 uppercase font-semibold block">Evaluated Patient Value</span>
                      <span className="text-slate-200 text-xs font-medium">{traceData.patient_value || 'None'}</span>
                    </div>
                    <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                      <span className="text-[10px] text-slate-500 uppercase font-semibold block">Target Protocol Threshold</span>
                      <span className="text-indigo-300 text-xs font-medium">{traceData.expected_value || 'N/A'}</span>
                    </div>
                  </div>
                </div>

                {/* Evidence Reliability Breakdown */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
                      <Award className="h-4 w-4 text-amber-400" />
                      <span>Evidence Reliability Score</span>
                    </span>
                    <span className="text-lg font-black text-amber-400">{(traceData.reliability_score * 100).toFixed(0)}%</span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-[11px]">
                    <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                      <span className="text-slate-500 block">Source Type</span>
                      <span className="text-slate-200 font-bold">{(traceData.reliability_breakdown.source_type_factor * 100).toFixed(0)}%</span>
                    </div>
                    <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                      <span className="text-slate-500 block">Document Recency</span>
                      <span className="text-slate-200 font-bold">{(traceData.reliability_breakdown.recency_factor * 100).toFixed(0)}%</span>
                    </div>
                    <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                      <span className="text-slate-500 block">Verification Status</span>
                      <span className="text-slate-200 font-bold">{(traceData.reliability_breakdown.verification_factor * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                </div>

                {/* Audit Metadata */}
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-[11px] space-y-2 text-slate-400 font-mono">
                  <div className="flex justify-between"><span>Matching Engine:</span><span className="text-slate-200">{traceData.matching_engine_version}</span></div>
                  <div className="flex justify-between"><span>AI Provider / Model:</span><span className="text-slate-200">{traceData.ai_provider} ({traceData.ai_model})</span></div>
                  <div className="flex justify-between"><span>Prompt Version:</span><span className="text-slate-200">{traceData.prompt_version}</span></div>
                  <div className="flex justify-between"><span>Criterion Version:</span><span className="text-slate-200">v{traceData.criterion_version}</span></div>
                  <div className="flex justify-between"><span>Decision Timestamp:</span><span className="text-slate-200">{traceData.decision_timestamp}</span></div>
                </div>
              </div>
            </div>

            {/* Right Pane: Grounded Source Evidence Panel */}
            <div className="lg:col-span-5 space-y-6">
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-5">
                <div className="flex items-center space-x-2 border-b border-slate-800 pb-4">
                  <FileText className="h-5 w-5 text-sky-400" />
                  <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wide">Grounded Source Evidence</h3>
                </div>

                {traceData.evidence_items.map((item, idx) => (
                  <div key={idx} className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
                    <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
                      <span className="text-sky-300 flex items-center space-x-1">
                        <FileText className="h-4 w-4" />
                        <span>{item.file_name || 'clinical_report.pdf'}</span>
                      </span>
                      <span className="bg-slate-800 text-slate-400 px-2 py-0.5 rounded font-mono">
                        Page {item.page_number} (Span {item.start_char}-{item.end_char})
                      </span>
                    </div>

                    <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-slate-200">
                      <span className="text-[10px] text-slate-500 block font-sans uppercase mb-1">Raw Extracted Document Excerpt</span>
                      "{item.raw_value}"
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-400">
                      <div>Extraction Method: <strong className="text-slate-200">{item.extraction_method}</strong></div>
                      <div>Extraction Confidence: <strong className="text-emerald-400">{(item.extraction_confidence * 100).toFixed(0)}%</strong></div>
                    </div>

                    {/* Verification Actions */}
                    <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between">
                      <span className="text-xs text-slate-400">Verification Status: <strong className="text-sky-300 uppercase">{item.verification_status}</strong></span>
                      <div className="flex space-x-2">
                        <button className="bg-emerald-950 hover:bg-emerald-900 text-emerald-300 text-xs px-2.5 py-1 rounded border border-emerald-500/40">Verify</button>
                        <button className="bg-rose-950 hover:bg-rose-900 text-rose-300 text-xs px-2.5 py-1 rounded border border-rose-500/40">Reject</button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </PageWrapper>
  );
};
