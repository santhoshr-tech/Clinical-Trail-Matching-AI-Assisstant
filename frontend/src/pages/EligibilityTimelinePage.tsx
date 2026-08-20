import React, { useState, useEffect } from 'react';
import { PageWrapper } from '../components/PageWrapper';
import {
  Clock,
  Calendar,
  CheckCircle,
  XCircle,
  AlertCircle,
  HelpCircle,
  ArrowRight,
  RefreshCw,
  Sliders,
  History
} from 'lucide-react';
import { apiGet, apiPost } from '../utils/apiClient';

interface TimelineEvent {
  event_id: string;
  patient_id: string;
  trial_id: string;
  criterion_id: string;
  timestamp: string;
  old_status: string;
  new_status: string;
  old_value?: string;
  new_value?: string;
  trigger_reason: string;
}

interface PatientEligibilityTimeline {
  patient_id: string;
  trial_id: string;
  events: TimelineEvent[];
}

interface TemporalValidationResult {
  is_valid: boolean;
  rule_type: string;
  event_date?: string;
  reference_date?: string;
  days_difference?: number;
  date_quality: string;
  is_stale: boolean;
  temporal_explanation: string;
  requires_human_review: boolean;
}

export const EligibilityTimelinePage: React.FC = () => {
  const [patientId, setPatientId] = useState<string>('11111111-1111-1111-1111-111111111111');
  const [trialId, setTrialId] = useState<string>('t-nct04500000');
  const [timeline, setTimeline] = useState<PatientEligibilityTimeline | null>(null);

  // Temporal Validator Interactive State
  const [ruleType, setRuleType] = useState<string>('within_last_n_days');
  const [eventDateInput, setEventDateInput] = useState<string>('2026-07-16');
  const [referenceDateInput, setReferenceDateInput] = useState<string>('2026-08-15');
  const [windowDaysInput, setWindowDaysInput] = useState<number>(30);
  const [validationResult, setValidationResult] = useState<TemporalValidationResult | null>(null);

  const [loading, setLoading] = useState<boolean>(false);

  const fetchTimeline = async () => {
    setLoading(true);
    try {
      const res = await apiGet<PatientEligibilityTimeline>(`/temporal/timeline/patient/${patientId}/${trialId}`);
      if (res.data) {
        setTimeline(res.data);
      }
    } catch (err) {
      console.error('Failed to load eligibility timeline', err);
    } finally {
      setLoading(false);
    }
  };

  const handleEvaluateTemporalRule = async () => {
    try {
      const res = await apiPost<TemporalValidationResult>('/temporal/validate', {
        rule_type: ruleType,
        event_date: eventDateInput,
        reference_date: referenceDateInput,
        window_days: Number(windowDaysInput)
      });
      if (res.data) {
        setValidationResult(res.data);
      }
    } catch (err) {
      console.error('Failed to evaluate temporal rule', err);
    }
  };

  useEffect(() => {
    fetchTimeline();
    handleEvaluateTemporalRule();
  }, [patientId, trialId]);

  return (
    <PageWrapper
      title="Patient Eligibility Timeline & Temporal Validation"
      subtitle="Track criterion state transitions, date quality arithmetic, recency windows, and boundary conditions."
      moduleName="modules/temporal"
      icon={Clock}
    >
      <div className="space-y-6">
        {/* Header Control Bar */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center space-x-2">
              <label className="text-xs font-semibold text-slate-400 uppercase">Patient:</label>
              <select
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
                className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 focus:outline-none"
              >
                <option value="11111111-1111-1111-1111-111111111111">MRN-1001 (Pass Timeline)</option>
                <option value="33333333-3333-3333-3333-333333333333">MRN-1003 (Conflict Resolved Timeline)</option>
              </select>
            </div>

            <div className="flex items-center space-x-2">
              <label className="text-xs font-semibold text-slate-400 uppercase">Trial Protocol:</label>
              <select
                value={trialId}
                onChange={(e) => setTrialId(e.target.value)}
                className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 focus:outline-none"
              >
                <option value="t-nct04500000">NCT04500000 (Osimertinib NSCLC)</option>
              </select>
            </div>
          </div>

          <button
            onClick={fetchTimeline}
            disabled={loading}
            className="flex items-center space-x-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs px-4 py-2.5 rounded-lg transition"
          >
            <RefreshCw className="h-4 w-4" />
            <span>Refresh Timeline</span>
          </button>
        </div>

        {/* Interactive Temporal Rule Validator Panel */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
          <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
            <Sliders className="h-5 w-5 text-sky-400" />
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wide">Interactive Temporal Rule & Boundary Validator</h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs">
            <div>
              <label className="text-slate-400 block mb-1">Temporal Rule Type:</label>
              <select
                value={ruleType}
                onChange={(e) => setRuleType(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2.5"
              >
                <option value="within_last_n_days">within_last_n_days</option>
                <option value="recent_lab">recent_lab (max 28 days)</option>
                <option value="before_enrollment">before_enrollment</option>
                <option value="after_diagnosis">after_diagnosis</option>
                <option value="current_medication">current_medication</option>
              </select>
            </div>

            <div>
              <label className="text-slate-400 block mb-1">Source Event Date:</label>
              <input
                type="text"
                value={eventDateInput}
                onChange={(e) => setEventDateInput(e.target.value)}
                placeholder="YYYY-MM-DD or partial"
                className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2.5"
              />
            </div>

            <div>
              <label className="text-slate-400 block mb-1">Reference Enrollment Date:</label>
              <input
                type="text"
                value={referenceDateInput}
                onChange={(e) => setReferenceDateInput(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2.5"
              />
            </div>

            <div>
              <label className="text-slate-400 block mb-1">Window Limit (Days):</label>
              <input
                type="number"
                value={windowDaysInput}
                onChange={(e) => setWindowDaysInput(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2.5"
              />
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={handleEvaluateTemporalRule}
              className="bg-sky-500 hover:bg-sky-400 text-white font-bold text-xs px-5 py-2 rounded-lg transition"
            >
              Evaluate Temporal Boundary
            </button>
          </div>

          {/* Validation Result Display */}
          {validationResult && (
            <div className={`p-4 rounded-xl border text-xs space-y-2 ${
              validationResult.is_valid ? 'bg-emerald-950/40 border-emerald-800 text-emerald-200' : 'bg-rose-950/40 border-rose-800 text-rose-200'
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 font-bold uppercase">
                  {validationResult.is_valid ? <CheckCircle className="h-4 w-4 text-emerald-400" /> : <XCircle className="h-4 w-4 text-rose-400" />}
                  <span>{validationResult.is_valid ? 'Temporal Boundary VALID' : 'Temporal Boundary INVALID'}</span>
                </div>

                <div className="flex space-x-2">
                  <span className="bg-slate-900 border border-slate-700 px-2 py-0.5 rounded font-mono text-[10px]">
                    Quality: {validationResult.date_quality}
                  </span>
                  {validationResult.is_stale && (
                    <span className="bg-amber-950 text-amber-300 border border-amber-800 px-2 py-0.5 rounded font-mono text-[10px]">
                      STALE EVIDENCE
                    </span>
                  )}
                </div>
              </div>

              <p className="font-mono text-slate-300">{validationResult.temporal_explanation}</p>
            </div>
          )}
        </div>

        {/* Chronological Eligibility Timeline Visualization */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
          <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
            <History className="h-5 w-5 text-purple-400" />
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wide">Criterion State Transition Timeline</h3>
          </div>

          {!timeline || timeline.events.length === 0 ? (
            <div className="text-center text-slate-400 text-xs py-8">
              No timeline events recorded yet.
            </div>
          ) : (
            <div className="relative border-l-2 border-slate-800 ml-4 space-y-8 pl-6">
              {timeline.events.map((evt, idx) => (
                <div key={evt.event_id || idx} className="relative group">
                  {/* Node Dot */}
                  <div className={`absolute -left-[31px] top-1.5 h-4 w-4 rounded-full border-2 ${
                    evt.new_status === 'PASS' ? 'bg-emerald-500 border-emerald-300' :
                    evt.new_status === 'FAIL' ? 'bg-rose-500 border-rose-300' : 'bg-purple-500 border-purple-300'
                  }`} />

                  <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl space-y-3 shadow-md">
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                      <span className="font-mono text-slate-400">{evt.timestamp}</span>
                      <span className="font-mono text-sky-400 font-bold">Criterion: {evt.criterion_id}</span>
                    </div>

                    <div className="flex items-center space-x-3 text-xs">
                      <span className="bg-slate-900 border border-slate-700 text-slate-400 px-2 py-0.5 rounded uppercase font-bold">
                        {evt.old_status}
                      </span>
                      <ArrowRight className="h-4 w-4 text-slate-500" />
                      <span className={`px-2.5 py-0.5 rounded uppercase font-bold border ${
                        evt.new_status === 'PASS' ? 'bg-emerald-950 text-emerald-300 border-emerald-500/40' :
                        evt.new_status === 'FAIL' ? 'bg-rose-950 text-rose-300 border-rose-500/40' :
                        'bg-purple-950 text-purple-300 border-purple-500/40'
                      }`}>
                        {evt.new_status}
                      </span>
                    </div>

                    {(evt.old_value || evt.new_value) && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono pt-1">
                        {evt.old_value && <div className="bg-slate-900 p-2 rounded text-slate-400"><span className="text-[10px] text-slate-500 block uppercase">Old Value</span>{evt.old_value}</div>}
                        {evt.new_value && <div className="bg-slate-900 p-2 rounded text-emerald-300"><span className="text-[10px] text-slate-500 block uppercase">New Value</span>{evt.new_value}</div>}
                      </div>
                    )}

                    <div className="text-xs text-slate-400 italic pt-1">
                      Trigger: {evt.trigger_reason}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </PageWrapper>
  );
};
