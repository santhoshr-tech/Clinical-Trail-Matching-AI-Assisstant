import React, { useEffect, useState } from 'react';
import { Users, TrendingUp, TrendingDown, AlertTriangle, CheckCircle2, UserX, Calendar, Plus, RefreshCw, Activity, ArrowRight, ShieldCheck } from 'lucide-react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { useAuth } from '../context/AuthContext';
import { BASE_URL } from '../utils/apiClient';

export const MyTrialCohortSection: React.FC = () => {
  const [trials, setTrials] = useState<any[]>([]);
  const [selectedTrialId, setSelectedTrialId] = useState<string>('t-nct04500000');
  const [cohort, setCohort] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedPatient, setSelectedPatient] = useState<any | null>(null);
  
  // Weekly progress upload form state
  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);
  const [uploadTargetEnrollment, setUploadTargetEnrollment] = useState<any | null>(null);
  const [newMetricValue, setNewMetricValue] = useState<string>('');
  const [uploadNotes, setUploadNotes] = useState<string>('');
  const [uploadFeedback, setUploadFeedback] = useState<any | null>(null);
  const [submittingProgress, setSubmittingProgress] = useState<boolean>(false);

  // Discontinue confirmation modal state
  const [discontinueTarget, setDiscontinueTarget] = useState<any | null>(null);
  const [discontinueReason, setDiscontinueReason] = useState<string>('no_improvement_after_N_weeks');
  const [discontinuing, setDiscontinuing] = useState<boolean>(false);

  const { user } = useAuth();

  useEffect(() => {
    // Fetch available trials
    fetch(`${BASE_URL}/api/v1/trials/search`, {
      headers: {
        'X-User-Email': user?.email || '',
        'X-User-Role': user?.role || '',
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success && Array.isArray(data.data) && data.data.length > 0) {
          setTrials(data.data);
          if (!selectedTrialId) {
            setSelectedTrialId(data.data[0].id);
          }
        }
      })
      .catch((err) => console.error(err));
  }, [user]);

  const fetchCohort = () => {
    if (!selectedTrialId) return;
    setLoading(true);
    fetch(`${BASE_URL}/api/v1/enrollment/cohort/${selectedTrialId}`, {
      headers: {
        'X-User-Email': user?.email || '',
        'X-User-Role': user?.role || '',
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success && Array.isArray(data.data)) {
          setCohort(data.data);
          if (data.data.length > 0 && !selectedPatient) {
            setSelectedPatient(data.data[0]);
          }
        }
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchCohort();
  }, [selectedTrialId, user]);

  const handleUploadProgress = (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadTargetEnrollment || !newMetricValue) return;

    setSubmittingProgress(true);
    setUploadFeedback(null);

    fetch(`${BASE_URL}/api/v1/enrollment/progress`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Email': user?.email || '',
        'X-User-Role': user?.role || '',
      },
      body: JSON.stringify({
        enrollment_id: uploadTargetEnrollment.enrollment_id,
        key_metric_value: parseFloat(newMetricValue),
        notes: uploadNotes || undefined,
      }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success && data.data) {
          setUploadFeedback(data.data);
          fetchCohort();
        }
      })
      .catch((err) => console.error(err))
      .finally(() => setSubmittingProgress(false));
  };

  const handleDiscontinuePatient = () => {
    if (!discontinueTarget) return;
    setDiscontinuing(true);

    fetch(`${BASE_URL}/api/v1/enrollment/discontinue`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Email': user?.email || '',
        'X-User-Role': user?.role || '',
      },
      body: JSON.stringify({
        enrollment_id: discontinueTarget.enrollment_id,
        reason: discontinueReason,
      }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          setDiscontinueTarget(null);
          fetchCohort();
        }
      })
      .catch((err) => console.error(err))
      .finally(() => setDiscontinuing(false));
  };

  const currentTrial = trials.find((t) => t.id === selectedTrialId);

  return (
    <div className="space-y-6">
      {/* Header & Trial Selector Row */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-cyan-400">
              <Users className="w-5 h-5 text-cyan-400" />
              <h3 className="text-lg font-bold text-white">My Trial Cohort & Treatment Progress</h3>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Ongoing weekly monitoring of enrolled patients, disease-agnostic metric trends, and non-responder handling.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <select
              value={selectedTrialId}
              onChange={(e) => {
                setSelectedTrialId(e.target.value);
                setSelectedPatient(null);
              }}
              className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg p-2.5 font-mono focus:outline-none focus:border-cyan-500"
            >
              {trials.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.nctId || t.nct_id} — {t.title}
                </option>
              ))}
            </select>

            <button
              onClick={fetchCohort}
              className="bg-slate-800 hover:bg-slate-700 text-slate-200 p-2.5 rounded-lg border border-slate-700 transition-colors"
              title="Refresh Cohort"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
            </button>
          </div>
        </div>

        {currentTrial && (
          <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 flex flex-wrap items-center justify-between text-xs text-slate-300 gap-2">
            <div>
              <span className="text-slate-400">Target Metric: </span>
              <span className="font-bold text-cyan-300">{currentTrial.keyMetricName || currentTrial.key_metric_name || 'HbA1c'}</span>
            </div>
            <div>
              <span className="text-slate-400">Improvement Target: </span>
              <span className="font-bold text-emerald-400 capitalize">
                {currentTrial.improvementDirection || currentTrial.improvement_direction || 'decrease'}
              </span>
            </div>
            <div>
              <span className="text-slate-400">Non-Responder Threshold: </span>
              <span className="font-bold text-amber-400">
                {currentTrial.improvementThresholdWeeks || currentTrial.improvement_threshold_weeks || 2} consecutive weeks
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Cohort Patient Table & Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-bold text-white flex items-center space-x-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              <span>Enrolled Patient Cohort ({cohort.length})</span>
            </h4>

            <span className="text-xs text-slate-400">
              Active: {cohort.filter((p) => p.status === 'active').length} | Discontinued: {cohort.filter((p) => p.status === 'discontinued').length}
            </span>
          </div>

          {cohort.length === 0 ? (
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-8 text-center text-xs text-slate-400 space-y-2">
              <p>No patients currently enrolled in this trial cohort.</p>
              <p className="text-[11px] text-slate-400">Upload a patient report under Document Upload to screen and enroll eligible candidates.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] font-mono border-b border-slate-800">
                  <tr>
                    <th className="p-3">Enrollment ID</th>
                    <th className="p-3">Patient MRN</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Week</th>
                    <th className="p-3">Baseline / Current</th>
                    <th className="p-3">Trend</th>
                    <th className="p-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {cohort.map((p) => {
                    const isSelected = selectedPatient?.enrollment_id === p.enrollment_id;
                    const isDiscontinued = p.status === 'discontinued';

                    return (
                      <tr
                        key={p.enrollment_id}
                        onClick={() => setSelectedPatient(p)}
                        className={`cursor-pointer transition-colors ${
                          isSelected ? 'bg-cyan-950/30' : 'hover:bg-slate-950/60'
                        }`}
                      >
                        <td className="p-3 font-mono font-bold text-cyan-300">{p.enrollment_id}</td>
                        <td className="p-3 font-medium text-slate-200">
                          {p.mrn_synthetic}
                          <span className="block text-[10px] text-slate-400">{p.primary_diagnosis}</span>
                        </td>
                        <td className="p-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold capitalize ${
                              isDiscontinued
                                ? 'bg-red-950 text-red-400 border border-red-800'
                                : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                            }`}
                          >
                            {p.status}
                          </span>
                        </td>
                        <td className="p-3 font-mono font-semibold text-slate-300">Week {p.week_number}</td>
                        <td className="p-3 font-mono">
                          <span className="text-slate-400">{p.baseline_metric_value ?? 'N/A'}</span>
                          <span className="mx-1 text-slate-600">&rarr;</span>
                          <span className="font-bold text-white">{p.current_metric_value ?? 'N/A'}</span>
                        </td>
                        <td className="p-3">
                          {isDiscontinued ? (
                            <span className="text-[11px] text-red-400 font-semibold flex items-center space-x-1">
                              <UserX className="w-3.5 h-3.5" />
                              <span>Discontinued</span>
                            </span>
                          ) : p.consecutive_non_improving_weeks >= (currentTrial?.improvementThresholdWeeks || 2) ? (
                            <span className="text-[11px] text-amber-400 font-bold flex items-center space-x-1">
                              <AlertTriangle className="w-3.5 h-3.5" />
                              <span>No Improvement</span>
                            </span>
                          ) : p.is_improving ? (
                            <span className="text-[11px] text-emerald-400 font-semibold flex items-center space-x-1">
                              <TrendingDown className="w-3.5 h-3.5" />
                              <span>Improving</span>
                            </span>
                          ) : (
                            <span className="text-[11px] text-slate-400 font-semibold">Stable</span>
                          )}
                        </td>
                        <td className="p-3 text-right space-x-2">
                          {!isDiscontinued && (
                            <>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setUploadTargetEnrollment(p);
                                  setShowUploadModal(true);
                                  setUploadFeedback(null);
                                }}
                                className="bg-slate-800 hover:bg-slate-700 text-cyan-300 px-2 py-1 rounded text-[11px] font-medium border border-slate-700"
                                title="Upload Weekly Progress"
                              >
                                + Weekly Report
                              </button>

                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setDiscontinueTarget(p);
                                }}
                                className="bg-red-950/60 hover:bg-red-900/80 text-red-300 px-2 py-1 rounded text-[11px] font-medium border border-red-800"
                                title="Discontinue Patient"
                              >
                                Discontinue
                              </button>
                            </>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Selected Patient Recharts Weekly Trend Line Chart */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-bold text-white flex items-center space-x-2">
              <TrendingUp className="w-4 h-4 text-cyan-400" />
              <span>Weekly Metric Trend Line</span>
            </h4>

            {selectedPatient && (
              <span className="text-xs font-mono text-cyan-300 font-bold">{selectedPatient.enrollment_id}</span>
            )}
          </div>

          {selectedPatient && selectedPatient.history && selectedPatient.history.length > 0 ? (
            <div className="space-y-4">
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs space-y-1">
                <div className="flex justify-between">
                  <span className="text-slate-400">Patient MRN:</span>
                  <span className="font-mono text-slate-200">{selectedPatient.mrn_synthetic}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Tracked Metric:</span>
                  <span className="font-bold text-cyan-300">{selectedPatient.key_metric_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Latest Trend:</span>
                  <span
                    className={`font-bold ${
                      selectedPatient.is_improving ? 'text-emerald-400' : 'text-amber-400'
                    }`}
                  >
                    {selectedPatient.is_improving ? "YES, it's working" : "No improvement"}
                  </span>
                </div>
              </div>

              {/* Recharts Line Chart */}
              <div className="h-56 w-full pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={selectedPatient.history}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="week_number" stroke="#94a3b8" tickFormatter={(w) => `Wk ${w}`} />
                    <YAxis stroke="#94a3b8" domain={['auto', 'auto']} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc' }}
                      formatter={(val: any) => [`${val} (${selectedPatient.key_metric_name})`, 'Value']}
                      labelFormatter={(w) => `Week ${w}`}
                    />
                    <Line
                      type="monotone"
                      dataKey="key_metric_value"
                      stroke="#06b6d4"
                      strokeWidth={3}
                      dot={{ r: 5, fill: '#06b6d4' }}
                      activeDot={{ r: 7 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : (
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-6 text-center text-xs text-slate-400">
              Select an enrolled patient from the table to view their weekly progress trend line chart.
            </div>
          )}
        </div>
      </div>

      {/* Weekly Progress Upload Modal */}
      {showUploadModal && uploadTargetEnrollment && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full space-y-4">
            <h4 className="text-sm font-bold text-white flex items-center space-x-2">
              <Plus className="w-4 h-4 text-cyan-400" />
              <span>Upload Weekly Progress Report</span>
            </h4>

            <p className="text-xs text-slate-400">
              Enrollment ID: <span className="font-mono text-cyan-300 font-bold">{uploadTargetEnrollment.enrollment_id}</span>
            </p>

            <form onSubmit={handleUploadProgress} className="space-y-4">
              <div className="space-y-1">
                <label className="block text-xs font-mono text-slate-300">
                  Weekly Metric Value ({uploadTargetEnrollment.key_metric_name}) *
                </label>
                <input
                  type="number"
                  step="0.1"
                  required
                  placeholder="e.g. 6.9 or 3.2"
                  value={newMetricValue}
                  onChange={(e) => setNewMetricValue(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-mono text-slate-300">Notes / Clinical Observations</label>
                <textarea
                  rows={2}
                  placeholder="Patient tolerated dosage well, no adverse events."
                  value={uploadNotes}
                  onChange={(e) => setUploadNotes(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              {uploadFeedback && (
                <div
                  className={`p-3 rounded-lg border text-xs ${
                    uploadFeedback.is_improving
                      ? 'bg-emerald-950/40 border-emerald-500 text-emerald-300'
                      : 'bg-amber-950/40 border-amber-500 text-amber-300'
                  }`}
                >
                  <p className="font-bold">{uploadFeedback.feedback_message}</p>
                  <p className="text-[11px] text-slate-300 mt-1">
                    Week {uploadFeedback.week_number} recorded. Next report due on {uploadFeedback.next_expected_report_date}.
                  </p>
                </div>
              )}

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowUploadModal(false);
                    setUploadTargetEnrollment(null);
                  }}
                  className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-2 rounded-lg text-xs font-medium"
                >
                  Close
                </button>
                <button
                  type="submit"
                  disabled={submittingProgress}
                  className="bg-cyan-600 hover:bg-cyan-500 text-white px-4 py-2 rounded-lg text-xs font-semibold disabled:opacity-50"
                >
                  {submittingProgress ? 'Saving Report...' : 'Submit Weekly Report'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Discontinue Non-Responder Confirmation Modal */}
      {discontinueTarget && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-red-800/80 rounded-xl p-6 max-w-md w-full space-y-4">
            <div className="flex items-center space-x-2 text-red-400">
              <AlertTriangle className="w-5 h-5" />
              <h4 className="text-sm font-bold text-white">Discontinue Patient from Trial?</h4>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Are you sure you want to discontinue enrollment{' '}
              <span className="font-mono text-cyan-300 font-bold">{discontinueTarget.enrollment_id}</span>?
            </p>

            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-[11px] text-slate-400 space-y-1">
              <div className="flex items-center space-x-1 text-emerald-400 font-semibold">
                <ShieldCheck className="w-4 h-4" />
                <span>Audit Trail & Data Retention Policy</span>
              </div>
              <p>
                All historical progress reports, clinical facts, and audit logs will be permanently retained and archived in compliance with GCP rules. No data will be hard deleted.
              </p>
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-mono text-slate-300">Discontinuation Reason</label>
              <select
                value={discontinueReason}
                onChange={(e) => setDiscontinueReason(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-200"
              >
                <option value="no_improvement_after_N_weeks">No improvement after N consecutive weeks</option>
                <option value="adverse_event">Adverse Event / Toxicity</option>
                <option value="patient_withdrawal">Patient Voluntary Withdrawal</option>
                <option value="protocol_violation">Protocol Deviation</option>
              </select>
            </div>

            <div className="flex justify-end space-x-2 pt-2">
              <button
                type="button"
                onClick={() => setDiscontinueTarget(null)}
                className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-2 rounded-lg text-xs font-medium"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDiscontinuePatient}
                disabled={discontinuing}
                className="bg-red-600 hover:bg-red-500 text-white px-4 py-2 rounded-lg text-xs font-semibold disabled:opacity-50"
              >
                {discontinuing ? 'Discontinuing...' : 'Confirm Discontinue & Archive'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
