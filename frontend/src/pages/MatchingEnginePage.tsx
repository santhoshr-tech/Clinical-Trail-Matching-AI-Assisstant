import React, { useState, useEffect } from 'react';
import { PageWrapper } from '../components/PageWrapper';
import {
  Cpu,
  Play,
  CheckCircle,
  XCircle,
  HelpCircle,
  AlertTriangle,
  ShieldCheck,
  Award,
  Layers,
  Search,
  Clock
} from 'lucide-react';
import { apiGet, apiPost } from '../utils/apiClient';

interface CriterionResult {
  criterion_id: string;
  criterion_type: string;
  category: string;
  operator: string;
  raw_text: string;
  status: 'PASS' | 'FAIL' | 'UNKNOWN' | 'CONFLICT';
  patient_value?: string;
  expected_value?: string;
  rule_used: string;
  source_evidence?: string;
  evidence_reliability: 'verified' | 'unverified' | 'stale' | 'conflicting';
  data_date?: string;
  decision_timestamp: string;
  criterion_version: number;
  engine_version: string;
}

interface MatchResult {
  patient_id: string;
  trial_id: string;
  overall_status: string;
  match_score: number;
  total_criteria: number;
  passed_count: number;
  failed_count: number;
  unknown_count: number;
  conflict_count: number;
  evaluated_at: string;
  engine_version: string;
  criterion_results: CriterionResult[];
}

export const MatchingEnginePage: React.FC = () => {
  const [selectedPatientId, setSelectedPatientId] = useState<string>('11111111-1111-1111-1111-111111111111');
  const [selectedTrialId, setSelectedTrialId] = useState<string>('t-nct04500000');
  const [matchData, setMatchData] = useState<MatchResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [patients, setPatients] = useState<any[]>([]);
  const [trials, setTrials] = useState<any[]>([]);
  const [trialsLoading, setTrialsLoading] = useState<boolean>(true);
  const [criteriaMap, setCriteriaMap] = useState<Record<string, number>>({});

  useEffect(() => {
    // Load all patients from DB
    apiGet<any[]>('/patients').then(res => {
      if (res.data) setPatients(res.data);
    });

    // Load all trials dynamically from DB
    setTrialsLoading(true);
    apiGet<any[]>('/trials/search').then(res => {
      if (res.data && Array.isArray(res.data)) {
        setTrials(res.data);
        // Ensure selected trial is still valid; default to first if not
        if (res.data.length > 0 && !res.data.find((t: any) => t.id === 't-nct04500000')) {
          setSelectedTrialId(res.data[0].id);
        }
      }
      setTrialsLoading(false);
    }).catch(() => setTrialsLoading(false));
  }, []);

  // When a trial is selected, fetch its approved criteria count
  useEffect(() => {
    if (!selectedTrialId || criteriaMap[selectedTrialId] !== undefined) return;
    apiGet<any[]>(`/criteria/${selectedTrialId}`).then(res => {
      if (res.data && Array.isArray(res.data)) {
        const approvedCount = res.data.filter((c: any) => c.approvalStatus === 'approved').length;
        setCriteriaMap(prev => ({ ...prev, [selectedTrialId]: approvedCount }));
      }
    }).catch(() => {});
  }, [selectedTrialId]);

  const handleRunMatching = async () => {
    setLoading(true);
    try {
      const res = await apiPost<MatchResult>('/matching/evaluate', {
        patient_id: selectedPatientId,
        trial_id: selectedTrialId
      });
      if (res.data) {
        setMatchData(res.data);
      }
    } catch (err) {
      console.error("Match evaluation error:", err);
    } finally {
      setLoading(false);
    }
  };

  const getOverallBadge = (status?: string) => {
    switch (status) {
      case 'INVESTIGATOR_REVIEW_REQUIRED':
        return { label: 'INVESTIGATOR REVIEW REQUIRED (ALL VERIFIED PASS)', color: 'bg-emerald-950 text-emerald-300 border-emerald-500/40', icon: ShieldCheck };
      case 'ELIGIBLE_FOR_REVIEW':
        return { label: 'ELIGIBLE FOR REVIEW (UNVERIFIED PASS)', color: 'bg-sky-950 text-sky-300 border-sky-500/40', icon: CheckCircle };
      case 'POTENTIALLY_ELIGIBLE':
        return { label: 'POTENTIALLY ELIGIBLE (MISSING DATA)', color: 'bg-amber-950 text-amber-300 border-amber-500/40', icon: HelpCircle };
      case 'MANUAL_REVIEW_REQUIRED':
        return { label: 'MANUAL REVIEW REQUIRED (CONFLICT DETECTED)', color: 'bg-purple-950 text-purple-300 border-purple-500/40', icon: AlertTriangle };
      case 'NOT_ELIGIBLE':
        return { label: 'NOT ELIGIBLE (CRITERION FAILED)', color: 'bg-rose-950 text-rose-300 border-rose-500/40', icon: XCircle };
      default:
        return { label: 'READY FOR MATCHING', color: 'bg-slate-800 text-slate-400 border-slate-700', icon: Cpu };
    }
  };

  const badge = getOverallBadge(matchData?.overall_status);
  const BadgeIcon = badge.icon;

  return (
    <PageWrapper
      title="Deterministic Rule Engine & Criterion Matching"
      subtitle="Evaluates approved trial criteria against verified patient clinical facts. Zero AI overriding permitted."
      moduleName="modules/matching"
      icon={Cpu}
    >
      <div className="space-y-6">
        {/* Controls Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 flex-1">
            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">Target Patient Profile</label>
              <select
                value={selectedPatientId}
                onChange={(e) => setSelectedPatientId(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-sky-500 focus:outline-none"
              >
                <option value="11111111-1111-1111-1111-111111111111">MRN-1001 (Fully Eligible - NSCLC Stage IV)</option>
                <option value="22222222-2222-2222-2222-222222222222">MRN-1002 (Excluded - Severe Cardiac Comorbidity)</option>
                <option value="33333333-3333-3333-3333-333333333333">MRN-1003 (Conflict - Unverified Lab vs Biopsy)</option>
                <option value="44444444-4444-4444-4444-444444444444">MRN-1004 (Unknown - Stale ANC Lab Date)</option>
                {patients.map(p => (
                  <option key={p.id} value={p.id}>{p.mrnSynthetic || p.id} - {p.primaryDiagnosis}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Target Trial Protocol
                {criteriaMap[selectedTrialId] !== undefined && (
                  <span className={`ml-2 px-1.5 py-0.5 rounded text-[10px] font-bold ${
                    criteriaMap[selectedTrialId] > 0
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                      : 'bg-rose-950 text-rose-400 border border-rose-800'
                  }`}>
                    {criteriaMap[selectedTrialId]} approved criteria
                  </span>
                )}
              </label>
              <select
                value={selectedTrialId}
                onChange={(e) => setSelectedTrialId(e.target.value)}
                disabled={trialsLoading}
                className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-sky-500 focus:outline-none disabled:opacity-60"
              >
                {trialsLoading ? (
                  <option value="">Loading trials...</option>
                ) : trials.length === 0 ? (
                  <option value="">No trials available</option>
                ) : (
                  trials.map((t: any) => (
                    <option key={t.id} value={t.id}>
                      {t.nctId} — {t.title?.slice(0, 52)}{t.title?.length > 52 ? '…' : ''} [{t.phase}]
                    </option>
                  ))
                )}
              </select>
              {selectedTrialId && criteriaMap[selectedTrialId] === 0 && (
                <p className="text-[10px] text-amber-400 mt-1 font-medium">
                  ⚠ No approved criteria — go to Criteria Review to approve criteria before running.
                </p>
              )}
            </div>
          </div>

          <button
            onClick={handleRunMatching}
            disabled={loading}
            className="flex items-center justify-center space-x-2 bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white font-semibold text-sm px-6 py-3 rounded-xl transition shadow-lg disabled:opacity-50"
          >
            <Play className="h-4 w-4 fill-current" />
            <span>{loading ? 'Evaluating Rules...' : 'Run Eligibility Engine'}</span>
          </button>
        </div>

        {/* Evaluation Summary Card */}
        {matchData && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
              <div className="space-y-1">
                <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Determined Eligibility Status</span>
                <div className={`inline-flex items-center space-x-2 border px-4 py-2 rounded-xl text-sm font-bold uppercase tracking-wide ${badge.color}`}>
                  <BadgeIcon className="h-5 w-5" />
                  <span>{badge.label}</span>
                </div>
              </div>

              {/* Match Score Gauge */}
              <div className="flex items-center space-x-4 bg-slate-950 p-4 rounded-xl border border-slate-800">
                <Award className="h-8 w-8 text-sky-400" />
                <div>
                  <span className="text-xs text-slate-400 uppercase block font-semibold">Transparent Match Score</span>
                  <span className="text-2xl font-black text-slate-100">{matchData.match_score.toFixed(1)}%</span>
                </div>
              </div>
            </div>

            {/* Counts Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="bg-emerald-950/20 border border-emerald-500/30 p-4 rounded-xl text-center">
                <span className="text-xs text-emerald-400 uppercase font-semibold block">PASS</span>
                <span className="text-2xl font-bold text-emerald-300">{matchData.passed_count}</span>
              </div>
              <div className="bg-rose-950/20 border border-rose-500/30 p-4 rounded-xl text-center">
                <span className="text-xs text-rose-400 uppercase font-semibold block">FAIL</span>
                <span className="text-2xl font-bold text-rose-300">{matchData.failed_count}</span>
              </div>
              <div className="bg-amber-950/20 border border-amber-500/30 p-4 rounded-xl text-center">
                <span className="text-xs text-amber-400 uppercase font-semibold block">UNKNOWN</span>
                <span className="text-2xl font-bold text-amber-300">{matchData.unknown_count}</span>
              </div>
              <div className="bg-purple-950/20 border border-purple-500/30 p-4 rounded-xl text-center">
                <span className="text-xs text-purple-400 uppercase font-semibold block">CONFLICT</span>
                <span className="text-2xl font-bold text-purple-300">{matchData.conflict_count}</span>
              </div>
            </div>

            {/* Detailed Criterion Results */}
            <div className="space-y-4 pt-4">
              <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center space-x-2">
                <Layers className="h-4 w-4 text-sky-400" />
                <span>Deterministic Criterion Evaluation Results ({matchData.total_criteria} Rules)</span>
              </h3>

              <div className="space-y-3">
                {matchData.criterion_results.map((item, idx) => (
                  <div
                    key={item.criterion_id || idx}
                    className={`p-4 rounded-xl border transition ${
                      item.status === 'PASS'
                        ? 'bg-emerald-950/10 border-emerald-500/20'
                        : item.status === 'FAIL'
                        ? 'bg-rose-950/10 border-rose-500/20'
                        : item.status === 'CONFLICT'
                        ? 'bg-purple-950/10 border-purple-500/20'
                        : 'bg-amber-950/10 border-amber-500/20'
                    }`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                      <div className="flex items-center space-x-2">
                        <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                          item.criterion_type === 'inclusion' ? 'bg-sky-950 text-sky-300 border border-sky-500/30' : 'bg-amber-950 text-amber-300 border border-amber-500/30'
                        }`}>
                          {item.criterion_type}
                        </span>
                        <span className="text-xs font-semibold text-slate-400 uppercase">
                          {item.category}
                        </span>
                      </div>

                      <span className={`text-xs px-3 py-1 rounded-full font-bold uppercase border ${
                        item.status === 'PASS'
                          ? 'bg-emerald-900/40 text-emerald-400 border-emerald-500/40'
                          : item.status === 'FAIL'
                          ? 'bg-rose-900/40 text-rose-400 border-rose-500/40'
                          : item.status === 'CONFLICT'
                          ? 'bg-purple-900/40 text-purple-400 border-purple-500/40'
                          : 'bg-amber-900/40 text-amber-300 border-amber-500/40'
                      }`}>
                        STATUS: {item.status}
                      </span>
                    </div>

                    <p className="text-slate-200 text-sm font-medium mb-3">"{item.raw_text}"</p>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs mb-3">
                      <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                        <span className="text-slate-500 block text-[10px] uppercase font-semibold">Patient Value</span>
                        <span className="text-sky-300 font-semibold">{item.patient_value || 'None recorded'}</span>
                      </div>

                      <div className="bg-slate-950 p-2.5 rounded border border-slate-800">
                        <span className="text-slate-500 block text-[10px] uppercase font-semibold">Expected Rule Value</span>
                        <span className="text-indigo-300 font-semibold">{item.expected_value || 'N/A'}</span>
                      </div>
                    </div>

                    {item.source_evidence && (
                      <div className="p-2.5 bg-slate-950/80 rounded border border-slate-800 text-xs text-slate-300 mb-2">
                        <span className="text-slate-500 text-[10px] block uppercase font-semibold">Source Clinical Evidence</span>
                        <span>{item.source_evidence}</span>
                      </div>
                    )}

                    <div className="flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-800/60">
                      <span>Reliability: <strong className="text-slate-300 uppercase">{item.evidence_reliability}</strong></span>
                      <span>Engine: {item.engine_version} (Rule v{item.criterion_version})</span>
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
