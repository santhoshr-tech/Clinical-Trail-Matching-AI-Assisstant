import React, { useState, useEffect } from 'react';
import { PageWrapper } from '../components/PageWrapper';
import {
  FlaskConical,
  Play,
  Copy,
  Archive,
  Plus,
  ArrowRight,
  ShieldCheck,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Layers
} from 'lucide-react';
import { apiGet, apiPost } from '../utils/apiClient';

interface Modification {
  field_category: string;
  field_name: string;
  hypothetical_value: string;
  raw_unit?: string;
  is_negated?: boolean;
}

interface Scenario {
  scenario_id: string;
  patient_id: string;
  trial_id: string;
  scenario_name: string;
  status: string;
  modifications: Modification[];
}

interface CriterionDelta {
  criterion_id: string;
  criterion_text: string;
  old_state: string;
  new_state: string;
  delta_explanation: string;
  cause_field: string;
}

interface SimulationResult {
  scenario_id: string;
  patient_id: string;
  trial_id: string;
  original_overall_status: string;
  simulated_overall_status: string;
  original_score: number;
  simulated_score: number;
  criteria_deltas: CriterionDelta[];
  audit_event_id: string;
}

export const WhatIfSimulatorPage: React.FC = () => {
  const [patientId, setPatientId] = useState<string>('22222222-2222-2222-2222-222222222222');
  const [trialId, setTrialId] = useState<string>('t-nct04500000');
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(null);

  // Modification Form State
  const [scenarioName, setScenarioName] = useState<string>('Hypothetical ANC Lab Addition');
  const [fieldCategory, setFieldCategory] = useState<string>('lab');
  const [fieldName, setFieldName] = useState<string>('Absolute Neutrophil Count');
  const [hypoValue, setHypoValue] = useState<string>('2.8');
  const [rawUnit, setRawUnit] = useState<string>('10*3/uL');
  const [isNegated, setIsNegated] = useState<boolean>(false);

  const [simulationResult, setSimulationResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchScenarios = async () => {
    try {
      const res = await apiGet<Scenario[]>(`/what-if/scenarios/patient/${patientId}`);
      if (res.data) {
        setScenarios(res.data);
        if (res.data.length > 0 && !selectedScenarioId) {
          setSelectedScenarioId(res.data[0].scenario_id);
        }
      }
    } catch (err) {
      console.error('Failed to load scenarios', err);
    }
  };

  useEffect(() => {
    fetchScenarios();
  }, [patientId]);

  const handleCreateAndSimulate = async () => {
    setLoading(true);
    setError(null);
    try {
      const scenarioPayload = {
        patient_id: patientId,
        trial_id: trialId,
        scenario_name: scenarioName,
        status: 'active',
        modifications: [
          {
            field_category: fieldCategory,
            field_name: fieldName,
            hypothetical_value: hypoValue,
            raw_unit: rawUnit,
            is_negated: isNegated
          }
        ]
      };

      const createRes = await apiPost<Scenario>('/what-if/scenario', scenarioPayload);
      if (createRes.data) {
        const scenId = createRes.data.scenario_id;
        setSelectedScenarioId(scenId);
        
        const simRes = await apiPost<SimulationResult>(`/what-if/simulate/${scenId}`);
        if (simRes.data) {
          setSimulationResult(simRes.data);
        }
        fetchScenarios();
      }
    } catch (err: any) {
      setError(err.message || 'Simulation execution failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDuplicate = async () => {
    if (!selectedScenarioId) return;
    try {
      const res = await apiPost<Scenario>(`/what-if/scenario/${selectedScenarioId}/duplicate`);
      if (res.data) {
        fetchScenarios();
        setSelectedScenarioId(res.data.scenario_id);
      }
    } catch (err) {
      console.error('Failed to duplicate scenario', err);
    }
  };

  const handleArchive = async () => {
    if (!selectedScenarioId) return;
    try {
      await apiPost(`/what-if/scenario/${selectedScenarioId}/archive`);
      fetchScenarios();
    } catch (err) {
      console.error('Failed to archive scenario', err);
    }
  };

  return (
    <PageWrapper
      title="Eligibility What-If Simulator"
      subtitle="Test hypothetical patient data changes in an isolated sandbox without altering canonical records."
      moduleName="modules/what-if"
      icon={FlaskConical}
    >
      <div className="space-y-6">
        {/* Sandbox Security Guarantee Banner */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between shadow">
          <div className="flex items-center space-x-3 text-xs">
            <ShieldCheck className="h-5 w-5 text-emerald-400 flex-shrink-0" />
            <span className="text-slate-300">
              <strong className="text-slate-100">Sandbox Isolation Enforced:</strong> All hypothetical modifications are evaluated strictly in-memory. Canonical patient EHR records remain 100% read-only and unmodified.
            </span>
          </div>

          <span className="text-[10px] uppercase font-bold bg-emerald-950 text-emerald-300 border border-emerald-800 px-2.5 py-1 rounded">
            CANONICAL DATA SAFE
          </span>
        </div>

        {/* Patient & Scenario Selection Bar */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center space-x-2">
              <label className="text-xs font-semibold text-slate-400 uppercase">Target Patient:</label>
              <select
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
                className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2"
              >
                <option value="22222222-2222-2222-2222-222222222222">MRN-1002 (Low ANC Baseline)</option>
                <option value="11111111-1111-1111-1111-111111111111">MRN-1001 (NSCLC Stage IV)</option>
              </select>
            </div>

            {scenarios.length > 0 && (
              <div className="flex items-center space-x-2">
                <label className="text-xs font-semibold text-slate-400 uppercase">Saved Scenarios:</label>
                <select
                  value={selectedScenarioId || ''}
                  onChange={(e) => setSelectedScenarioId(e.target.value)}
                  className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2"
                >
                  {scenarios.map((s) => (
                    <option key={s.scenario_id} value={s.scenario_id}>
                      {s.scenario_name} ({s.status})
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div className="flex items-center space-x-2">
            {selectedScenarioId && (
              <>
                <button
                  onClick={handleDuplicate}
                  className="flex items-center space-x-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs px-3 py-2 rounded-lg transition"
                >
                  <Copy className="h-3.5 w-3.5" />
                  <span>Duplicate</span>
                </button>
                <button
                  onClick={handleArchive}
                  className="flex items-center space-x-1.5 bg-slate-800 hover:bg-slate-700 text-rose-300 font-semibold text-xs px-3 py-2 rounded-lg transition"
                >
                  <Archive className="h-3.5 w-3.5" />
                  <span>Archive</span>
                </button>
              </>
            )}
          </div>
        </div>

        {/* Hypothetical Modification Builder Form */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
          <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wide border-b border-slate-800 pb-3">
            Hypothetical Modification Builder
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div className="sm:col-span-3">
              <label className="text-slate-400 block mb-1">Scenario Name:</label>
              <input
                type="text"
                value={scenarioName}
                onChange={(e) => setScenarioName(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2.5"
              />
            </div>

            <div>
              <label className="text-slate-400 block mb-1">Category:</label>
              <select
                value={fieldCategory}
                onChange={(e) => setFieldCategory(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2.5"
              >
                <option value="lab">Lab Value</option>
                <option value="biomarker">Biomarker</option>
                <option value="disease_stage">Disease Stage</option>
                <option value="medication">Medication</option>
                <option value="prior_treatment">Prior Treatment</option>
                <option value="event_date">Event Date</option>
              </select>
            </div>

            <div>
              <label className="text-slate-400 block mb-1">Field Name:</label>
              <input
                type="text"
                value={fieldName}
                onChange={(e) => setFieldName(e.target.value)}
                placeholder="e.g. Absolute Neutrophil Count"
                className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2.5"
              />
            </div>

            <div>
              <label className="text-slate-400 block mb-1">Hypothetical Value:</label>
              <input
                type="text"
                value={hypoValue}
                onChange={(e) => setHypoValue(e.target.value)}
                placeholder="e.g. 2.8"
                className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg p-2.5"
              />
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center space-x-2 text-xs">
              <input
                type="checkbox"
                id="isNegated"
                checked={isNegated}
                onChange={(e) => setIsNegated(e.target.checked)}
                className="rounded border-slate-700 bg-slate-950 text-sky-500"
              />
              <label htmlFor="isNegated" className="text-slate-300">Set as Negated / Negative</label>
            </div>

            <button
              onClick={handleCreateAndSimulate}
              disabled={loading}
              className="flex items-center space-x-2 bg-sky-500 hover:bg-sky-400 text-white font-bold text-xs px-6 py-2.5 rounded-lg transition"
            >
              <Play className="h-4 w-4" />
              <span>{loading ? 'Running Simulation...' : 'Run Simulation'}</span>
            </button>
          </div>
        </div>

        {/* Side-by-Side Simulation Comparison */}
        {simulationResult && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wide">Simulation Comparison Result</h3>
              <span className="text-xs font-mono text-slate-500">Audit ID: {simulationResult.audit_event_id}</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Baseline Result Card */}
              <div className="bg-slate-950 p-5 rounded-xl border border-slate-800 space-y-3">
                <span className="text-xs font-bold text-slate-400 uppercase">Baseline EHR Result</span>
                <div className="flex items-center justify-between">
                  <span className="text-lg font-black text-rose-400">{simulationResult.original_overall_status}</span>
                  <span className="text-xs font-mono text-slate-400">Score: {(simulationResult.original_score * 100).toFixed(0)}%</span>
                </div>
              </div>

              {/* Simulated Result Card */}
              <div className="bg-slate-950 p-5 rounded-xl border border-emerald-800/80 space-y-3">
                <span className="text-xs font-bold text-emerald-400 uppercase">Simulated Scenario Result</span>
                <div className="flex items-center justify-between">
                  <span className="text-lg font-black text-emerald-300">{simulationResult.simulated_overall_status}</span>
                  <span className="text-xs font-mono text-emerald-400 font-bold">Score: {(simulationResult.simulated_score * 100).toFixed(0)}%</span>
                </div>
              </div>
            </div>

            {/* Changed Criteria Deltas Table */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Criteria State Changes (Deltas)</h4>

              {simulationResult.criteria_deltas.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No criterion state changes resulted from this scenario.</p>
              ) : (
                <div className="space-y-3">
                  {simulationResult.criteria_deltas.map((delta) => (
                    <div key={delta.criterion_id} className="bg-slate-950 border border-slate-800 p-4 rounded-xl space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-200">{delta.criterion_text}</span>
                        <div className="flex items-center space-x-2 font-mono">
                          <span className="bg-slate-900 border border-slate-700 text-slate-400 px-2 py-0.5 rounded">{delta.old_state}</span>
                          <ArrowRight className="h-3.5 w-3.5 text-slate-500" />
                          <span className="bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded font-bold">{delta.new_state}</span>
                        </div>
                      </div>

                      <p className="text-slate-400 italic">{delta.delta_explanation}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </PageWrapper>
  );
};
