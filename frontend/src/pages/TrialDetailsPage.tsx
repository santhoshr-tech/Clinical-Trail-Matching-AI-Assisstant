import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { PageWrapper } from '../components/PageWrapper';
import {
  FileSearch, ExternalLink, RefreshCw, History, Play,
  CheckCircle, XCircle, HelpCircle, AlertTriangle, ShieldCheck,
  Award, Layers, ChevronRight, Tag, Users
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { apiGet, apiPost, BASE_URL } from '../utils/apiClient';

interface Criterion {
  id: string;
  criterion_type: string;
  category: string;
  operator: string;
  raw_text: string;
  approval_status: string;
  value_primary?: string;
  unit?: string;
}

interface CriterionResult {
  criterion_id: string;
  criterion_type: string;
  category: string;
  status: 'PASS' | 'FAIL' | 'UNKNOWN' | 'CONFLICT';
  patient_value?: string;
  expected_value?: string;
  raw_text: string;
  source_evidence?: string;
  evidence_reliability: string;
  engine_version: string;
}

interface MatchResult {
  overall_status: string;
  match_score: number;
  total_criteria: number;
  passed_count: number;
  failed_count: number;
  unknown_count: number;
  conflict_count: number;
  engine_version: string;
  criterion_results: CriterionResult[];
}

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.FC<any> }> = {
  INVESTIGATOR_REVIEW_REQUIRED: { label: 'INVESTIGATOR REVIEW REQUIRED', color: 'bg-emerald-950 text-emerald-300 border-emerald-600/50', icon: ShieldCheck },
  ELIGIBLE_FOR_REVIEW:          { label: 'ELIGIBLE FOR REVIEW',          color: 'bg-sky-950 text-sky-300 border-sky-600/50',             icon: CheckCircle },
  POTENTIALLY_ELIGIBLE:         { label: 'POTENTIALLY ELIGIBLE',         color: 'bg-amber-950 text-amber-300 border-amber-600/50',       icon: HelpCircle },
  MANUAL_REVIEW_REQUIRED:       { label: 'MANUAL REVIEW REQUIRED',       color: 'bg-purple-950 text-purple-300 border-purple-600/50',    icon: AlertTriangle },
  NOT_ELIGIBLE:                 { label: 'NOT ELIGIBLE',                 color: 'bg-rose-950 text-rose-300 border-rose-600/50',         icon: XCircle },
};

const CRIT_COLOR: Record<string, string> = {
  PASS:     'border-emerald-500/30 bg-emerald-950/10',
  FAIL:     'border-rose-500/30 bg-rose-950/10',
  UNKNOWN:  'border-amber-500/30 bg-amber-950/10',
  CONFLICT: 'border-purple-500/30 bg-purple-950/10',
};
const CRIT_BADGE: Record<string, string> = {
  PASS:     'bg-emerald-900/40 text-emerald-400 border-emerald-500/40',
  FAIL:     'bg-rose-900/40 text-rose-400 border-rose-500/40',
  UNKNOWN:  'bg-amber-900/40 text-amber-300 border-amber-500/40',
  CONFLICT: 'bg-purple-900/40 text-purple-400 border-purple-500/40',
};

export const TrialDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();

  const [trial, setTrial]         = useState<any>(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);
  const [syncing, setSyncing]     = useState(false);
  const [criteria, setCriteria]   = useState<Criterion[]>([]);
  const [patients, setPatients]   = useState<any[]>([]);
  const [selectedPat, setSelectedPat] = useState('11111111-1111-1111-1111-111111111111');
  const [matchResult, setMatchResult] = useState<MatchResult | null>(null);
  const [matching, setMatching]   = useState(false);
  const [matchError, setMatchError] = useState<string | null>(null);

  const hdrs = { 'X-User-Email': user?.email || '', 'X-User-Role': user?.role || '' };

  const fetchTrial = () => {
    setLoading(true);
    fetch(`${BASE_URL}/api/v1/trials/${id}`, { headers: hdrs })
      .then(r => r.json())
      .then(d => {
        if (d.success && d.data) {
          setTrial(d.data);
          // Fetch criteria for this trial
          apiGet<Criterion[]>(`/criteria/trial/${d.data.id}`).then(cr => {
            if (cr.data) setCriteria(cr.data.map((c: any) => ({ ...c, approval_status: c.approval_status || c.approvalStatus })));
          });
        } else {
          setError(d.error || 'Trial not found');
        }
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchTrial();
    // Load patients for matching selector
    apiGet<any[]>('/patients').then(r => { if (r.data) setPatients(r.data); });
  }, [id]);

  const handleSync = () => {
    setSyncing(true);
    fetch(`${BASE_URL}/api/v1/trials/${id}/sync`, { method: 'POST', headers: hdrs })
      .then(r => r.json())
      .then(d => { if (d.success) fetchTrial(); })
      .finally(() => setSyncing(false));
  };

  const handleRunMatching = async () => {
    if (!trial) return;
    setMatching(true);
    setMatchError(null);
    setMatchResult(null);
    try {
      const res = await apiPost<MatchResult>('/matching/evaluate', {
        patient_id: selectedPat,
        trial_id: trial.id,
      });
      if (res.data) setMatchResult(res.data);
      else setMatchError(res.error || 'Matching failed');
    } catch (e: any) {
      setMatchError(e.message);
    } finally {
      setMatching(false);
    }
  };

  if (loading) return <div className="text-center py-16 text-xs text-slate-400 animate-pulse">Loading protocol...</div>;
  if (error || !trial) return <div className="bg-red-950/50 border border-red-800 text-red-300 p-4 rounded-xl text-xs">{error || 'Protocol not found'}</div>;

  const approved = criteria.filter(c => c.approval_status === 'approved');
  const pending  = criteria.filter(c => c.approval_status === 'pending');
  const overallCfg = matchResult ? (STATUS_CONFIG[matchResult.overall_status] || STATUS_CONFIG['POTENTIALLY_ELIGIBLE']) : null;

  return (
    <PageWrapper
      title={`Protocol: ${trial.nctId}`}
      subtitle="Metadata, approved eligibility criteria, and inline patient matching engine."
      moduleName="modules/trials"
      icon={FileSearch}
    >
      <div className="space-y-6">

        {/* ── Header ── */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 border-b border-slate-800 pb-4">
            <div className="space-y-1">
              <div className="flex items-center flex-wrap gap-2">
                <h2 className="text-xl font-bold font-mono text-cyan-400">{trial.nctId}</h2>
                <span className="bg-slate-800 text-slate-200 px-2.5 py-0.5 rounded text-xs font-mono">{trial.phase}</span>
                <span className="bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded text-[10px] font-mono">{trial.recruitmentStatus}</span>
                <span className="bg-cyan-950 text-cyan-300 border border-cyan-800 px-2 py-0.5 rounded text-[10px] font-mono">v{trial.version}</span>
              </div>
              <p className="text-sm font-semibold text-slate-200">{trial.title}</p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={handleSync} disabled={syncing}
                className="flex items-center space-x-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3 py-2 rounded-lg border border-slate-700 transition disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 text-cyan-400 ${syncing ? 'animate-spin' : ''}`} />
                <span>{syncing ? 'Syncing...' : 'Sync Version'}</span>
              </button>
              <Link to={`/trials/${trial.id}/versions`}
                className="flex items-center space-x-1.5 bg-cyan-950 hover:bg-cyan-900 text-cyan-300 text-xs px-3 py-2 rounded-lg border border-cyan-800 transition">
                <History className="w-4 h-4" /><span>Version Log</span>
              </Link>
              <Link to={`/trials/${trial.id}/criteria-review`}
                className="flex items-center space-x-1.5 bg-indigo-950 hover:bg-indigo-900 text-indigo-300 text-xs px-3 py-2 rounded-lg border border-indigo-800 transition">
                <Tag className="w-4 h-4" /><span>Criteria Review</span>
              </Link>
            </div>
          </div>

          {/* Quick specs */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            {[
              { label: 'Sponsor',         val: trial.sponsor || 'N/A' },
              { label: 'Age Range',       val: `${trial.minAge || 18}–${trial.maxAge || 85} yrs` },
              { label: 'Gender',          val: trial.gender || 'ALL' },
              { label: 'Last Synced',     val: (trial.lastSyncedAt || '').slice(0, 16) || 'Just now' },
            ].map(s => (
              <div key={s.label} className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                <span className="text-slate-400 block text-[10px] uppercase font-mono mb-0.5">{s.label}</span>
                <span className="text-slate-200 font-medium font-mono text-[11px]">{s.val}</span>
              </div>
            ))}
          </div>
        </div>

        {/* ── Two-column body ── */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">

          {/* Left: criteria + eligibility text */}
          <div className="lg:col-span-3 space-y-6">

            {/* Approved Criteria */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center space-x-2">
                  <Layers className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">Structured Eligibility Criteria</h3>
                </div>
                <div className="flex items-center gap-2 text-[10px] font-mono">
                  <span className="bg-emerald-950 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded">{approved.length} approved</span>
                  {pending.length > 0 && <span className="bg-amber-950 text-amber-400 border border-amber-800 px-2 py-0.5 rounded">{pending.length} pending</span>}
                </div>
              </div>

              {criteria.length === 0 ? (
                <div className="text-xs text-slate-400 text-center py-6">
                  No structured criteria extracted yet.{' '}
                  <Link to={`/trials/${trial.id}/criteria-review`} className="text-cyan-400 hover:underline">Go to Criteria Review →</Link>
                </div>
              ) : (
                <div className="space-y-2">
                  {['inclusion', 'exclusion'].map(type => {
                    const group = criteria.filter(c => c.criterion_type === type);
                    if (!group.length) return null;
                    return (
                      <div key={type}>
                        <p className={`text-[10px] font-bold uppercase tracking-widest mb-1.5 ${type === 'inclusion' ? 'text-sky-400' : 'text-amber-400'}`}>
                          {type} criteria
                        </p>
                        {group.map(c => (
                          <div key={c.id} className={`flex items-start justify-between gap-2 px-3 py-2 rounded-lg border mb-1.5 text-xs ${c.approval_status === 'approved' ? 'border-slate-700 bg-slate-950/60' : 'border-slate-800/50 bg-slate-950/30 opacity-60'}`}>
                            <span className="text-slate-300 leading-relaxed">{c.raw_text}</span>
                            <span className={`shrink-0 text-[9px] px-1.5 py-0.5 rounded font-bold uppercase ${c.approval_status === 'approved' ? 'bg-emerald-950 text-emerald-400' : 'bg-slate-800 text-slate-500'}`}>
                              {c.approval_status}
                            </span>
                          </div>
                        ))}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Raw eligibility text */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
              <h3 className="text-xs font-bold text-slate-200 uppercase font-mono tracking-wider">Official Protocol Text</h3>
              <pre className="bg-slate-950 p-4 rounded-lg text-xs font-mono text-slate-300 whitespace-pre-wrap leading-relaxed border border-slate-800 max-h-60 overflow-y-auto">
                {trial.eligibilityCriteriaText || 'No eligibility text available.'}
              </pre>
            </div>
          </div>

          {/* Right: sidebar + matching panel */}
          <div className="lg:col-span-2 space-y-6">

            {/* Tags sidebar */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3 text-xs">
              <h3 className="font-bold text-slate-200 uppercase font-mono text-[11px]">Protocol Tags</h3>
              {[
                { label: 'Conditions',    val: trial.conditions,    color: 'text-cyan-300' },
                { label: 'Interventions', val: trial.interventions, color: 'text-emerald-300' },
                { label: 'Biomarkers',    val: trial.biomarkers || 'None required', color: 'text-purple-300' },
                { label: 'Locations',     val: trial.locations,     color: 'text-slate-300' },
              ].map(s => (
                <div key={s.label}>
                  <span className="text-[10px] text-slate-400 font-mono block mb-1">{s.label}</span>
                  <span className={`${s.color} bg-slate-950 p-2 rounded block border border-slate-800`}>{s.val}</span>
                </div>
              ))}
              <div className="pt-2 border-t border-slate-800">
                <a href={trial.sourceUrl} target="_blank" rel="noreferrer"
                  className="w-full bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-800 p-2.5 rounded-lg font-medium flex items-center justify-center space-x-2 transition text-xs">
                  <span>Open on ClinicalTrials.gov</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </div>

            {/* ── Inline Matching Panel ── */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
                <Play className="w-4 h-4 text-sky-400" />
                <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">Run Eligibility Matching</h3>
              </div>

              {approved.length === 0 ? (
                <div className="text-xs text-amber-400 bg-amber-950/20 border border-amber-800/40 rounded-lg p-3">
                  ⚠ No approved criteria. <Link to={`/trials/${trial.id}/criteria-review`} className="underline">Approve criteria</Link> before running matching.
                </div>
              ) : (
                <>
                  <div>
                    <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1.5">
                      <Users className="w-3 h-3 inline mr-1" />Select Patient
                    </label>
                    <select
                      value={selectedPat}
                      onChange={e => { setSelectedPat(e.target.value); setMatchResult(null); }}
                      className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-2 focus:ring-2 focus:ring-sky-500 focus:outline-none"
                    >
                      <option value="11111111-1111-1111-1111-111111111111">SYNTH-SCENARIO-A (58F, Stage IV NSCLC)</option>
                      <option value="22222222-2222-2222-2222-222222222222">SYNTH-SCENARIO-B (62M, Cardiac Comorbidity)</option>
                      <option value="33333333-3333-3333-3333-333333333333">SYNTH-SCENARIO-C (54F, Conflicting Biomarker)</option>
                      <option value="44444444-4444-4444-4444-444444444444">SYNTH-SCENARIO-D (71M, Stale ANC Lab)</option>
                      <option value="99999999-9999-9999-9999-999999999999">MRN-01 (Real OCR Patient)</option>
                      {patients.map(p => (
                        <option key={p.id} value={p.id}>{p.mrnSynthetic || p.id.slice(0, 8)} — {p.primaryDiagnosis?.slice(0, 35)}</option>
                      ))}
                    </select>
                  </div>

                  <button
                    onClick={handleRunMatching}
                    disabled={matching}
                    className="w-full flex items-center justify-center space-x-2 bg-gradient-to-r from-sky-600 to-blue-700 hover:from-sky-500 hover:to-blue-600 text-white font-semibold text-xs px-4 py-2.5 rounded-xl transition shadow-lg disabled:opacity-50"
                  >
                    <Play className="h-3.5 w-3.5 fill-current" />
                    <span>{matching ? 'Evaluating Criteria...' : `Run Engine (${approved.length} criteria)`}</span>
                  </button>

                  {matchError && (
                    <div className="text-xs text-rose-400 bg-rose-950/20 border border-rose-800/40 rounded-lg p-3">{matchError}</div>
                  )}
                </>
              )}

              {/* ── Match Results ── */}
              {matchResult && overallCfg && (() => {
                const Icon = overallCfg.icon;
                return (
                  <div className="space-y-4 border-t border-slate-800 pt-4">
                    {/* Overall badge */}
                    <div className={`inline-flex items-center space-x-2 border px-3 py-2 rounded-xl text-xs font-bold uppercase ${overallCfg.color}`}>
                      <Icon className="h-4 w-4" />
                      <span>{overallCfg.label}</span>
                    </div>

                    {/* Score + counts */}
                    <div className="flex items-center space-x-3 bg-slate-950 p-3 rounded-xl border border-slate-800">
                      <Award className="h-6 w-6 text-sky-400 shrink-0" />
                      <div>
                        <span className="text-[10px] text-slate-400 block uppercase font-semibold">Match Score</span>
                        <span className="text-xl font-black text-slate-100">{matchResult.match_score.toFixed(1)}%</span>
                      </div>
                      <div className="ml-auto grid grid-cols-2 gap-1 text-[10px] font-mono text-center">
                        <span className="bg-emerald-950/40 text-emerald-400 px-2 py-1 rounded border border-emerald-800/40">{matchResult.passed_count} PASS</span>
                        <span className="bg-rose-950/40 text-rose-400 px-2 py-1 rounded border border-rose-800/40">{matchResult.failed_count} FAIL</span>
                        <span className="bg-amber-950/40 text-amber-400 px-2 py-1 rounded border border-amber-800/40">{matchResult.unknown_count} UNK</span>
                        <span className="bg-purple-950/40 text-purple-400 px-2 py-1 rounded border border-purple-800/40">{matchResult.conflict_count} CONF</span>
                      </div>
                    </div>

                    {/* Per-criterion cards */}
                    <div className="space-y-2">
                      <p className="text-[10px] text-slate-400 uppercase font-semibold tracking-wider">
                        Criterion Breakdown ({matchResult.total_criteria} rules evaluated)
                      </p>
                      {matchResult.criterion_results.map((cr, i) => (
                        <div key={cr.criterion_id || i} className={`rounded-lg border p-3 space-y-1.5 ${CRIT_COLOR[cr.status]}`}>
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-1.5 flex-wrap">
                              <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase ${cr.criterion_type === 'inclusion' ? 'bg-sky-950 text-sky-300 border border-sky-800/40' : 'bg-amber-950 text-amber-300 border border-amber-800/40'}`}>
                                {cr.criterion_type}
                              </span>
                              <span className="text-[10px] text-slate-400 font-mono">{cr.category}</span>
                            </div>
                            <span className={`text-[9px] px-2 py-0.5 rounded-full font-bold border uppercase ${CRIT_BADGE[cr.status]}`}>
                              {cr.status}
                            </span>
                          </div>
                          <p className="text-xs text-slate-200 leading-snug">"{cr.raw_text}"</p>
                          {cr.patient_value && (
                            <div className="grid grid-cols-2 gap-1.5 text-[10px]">
                              <div className="bg-slate-900 rounded px-2 py-1 border border-slate-700">
                                <span className="text-slate-500 block">Patient</span>
                                <span className="text-sky-300 font-mono">{cr.patient_value}</span>
                              </div>
                              <div className="bg-slate-900 rounded px-2 py-1 border border-slate-700">
                                <span className="text-slate-500 block">Expected</span>
                                <span className="text-indigo-300 font-mono">{cr.expected_value || '—'}</span>
                              </div>
                            </div>
                          )}
                          {cr.source_evidence && (
                            <p className="text-[10px] text-slate-400 italic truncate">{cr.source_evidence}</p>
                          )}
                          <div className="text-[9px] text-slate-600 font-mono">
                            reliability: {cr.evidence_reliability} · {cr.engine_version}
                          </div>
                        </div>
                      ))}
                    </div>

                    <p className="text-[10px] text-slate-500 font-mono text-right">Engine: {matchResult.engine_version}</p>
                  </div>
                );
              })()}
            </div>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
};
