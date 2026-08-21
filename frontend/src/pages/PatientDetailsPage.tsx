import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { PageWrapper } from '../components/PageWrapper';
import { User, Activity, Clock, AlertTriangle, ShieldCheck, FileSpreadsheet, Plus, AlertCircle, Calendar } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { BASE_URL } from '../utils/apiClient';

export const PatientDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'labs' | 'biomarkers' | 'conditions' | 'medications'>('labs');
  const [showFactModal, setShowFactModal] = useState<boolean>(false);
  const [newFact, setNewFact] = useState({
    factType: 'lab',
    rawValue: '',
    normalizedValue: '',
    code: '',
    numericValue: '',
    unit: '',
    factDate: new Date().toISOString().split('T')[0]
  });
  const { user } = useAuth();

  useEffect(() => {
    fetch(`${BASE_URL}/api/v1/patients/${id}`, {
      headers: {
        'X-User-Email': user?.email || '',
        'X-User-Role': user?.role || '',
      },
    })
      .then((res) => res.json())
      .then((resData) => {
        if (resData.success && resData.data) {
          setData(resData.data);
        } else {
          setError(resData.error || 'Patient profile not found');
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id, user]);

  if (loading) return <div className="text-center py-12 text-xs text-slate-400 animate-pulse">Loading synthetic patient profile...</div>;
  if (error || !data) return <div className="bg-red-950/50 border border-red-800 text-red-300 p-4 rounded-xl text-xs">{error || 'Patient data missing'}</div>;

  const { profile, conditions, medications, labs, biomarkers } = data;

  const handleAddFact = (e: React.FormEvent) => {
    e.preventDefault();
    fetch(`${BASE_URL}/api/v1/patients/${id}/facts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Email': user?.email || '',
        'X-User-Role': user?.role || '',
      },
      body: JSON.stringify({
        ...newFact,
        numericValue: newFact.numericValue ? parseFloat(newFact.numericValue) : null
      })
    })
      .then((res) => res.json())
      .then((resData) => {
        if (resData.success) {
          setShowFactModal(false);
          // Reload patient data
          window.location.reload();
        } else {
          alert(`Failed to add clinical fact: ${resData.error || 'Unknown error'}`);
        }
      })
      .catch((err) => alert(`Error: ${err.message}`));
  };

  return (
    <PageWrapper
      title={`Patient Record: ${profile.mrnSynthetic}`}
      subtitle="Comprehensive clinical profile, preserved raw vs normalized facts, recency indicators, and data versioning."
      moduleName="modules/patients"
      icon={User}
    >
      <div className="space-y-6">
        {/* Header Profile Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div>
              <div className="flex items-center space-x-3">
                <h2 className="text-xl font-bold font-mono text-cyan-400">{profile.mrnSynthetic}</h2>
                <span className="bg-slate-800 text-slate-300 px-2.5 py-0.5 rounded text-xs font-mono">
                  Version {profile.version}
                </span>
                <span className="bg-cyan-950 text-cyan-300 border border-cyan-800 px-2 py-0.5 rounded text-[10px]">
                  100% Synthetic Prototype
                </span>
              </div>
              <p className="text-sm font-semibold text-slate-200 mt-1">{profile.primaryDiagnosis}</p>
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={() => setShowFactModal(true)}
                className="flex items-center space-x-1.5 bg-cyan-600 hover:bg-cyan-500 text-white text-xs px-3 py-2 rounded-lg font-semibold shadow-md shadow-cyan-950 transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span>Add Clinical Fact</span>
              </button>
              <Link
                to={`/patients/${profile.id}/timeline`}
                className="flex items-center space-x-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3 py-2 rounded-lg border border-slate-700 transition-colors"
              >
                <Clock className="w-4 h-4 text-cyan-400" />
                <span>View Timeline</span>
              </Link>
            </div>
          </div>

          {/* Profile Details Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
              <span className="text-slate-400 block text-[10px] uppercase font-mono">Demographics</span>
              <span className="text-slate-200 font-medium">{profile.age} yrs • {profile.gender}</span>
            </div>
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
              <span className="text-slate-400 block text-[10px] uppercase font-mono">Disease Stage</span>
              <span className="text-slate-200 font-medium">{profile.diseaseStage}</span>
            </div>
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
              <span className="text-slate-400 block text-[10px] uppercase font-mono">Comorbidities</span>
              <span className="text-slate-200 font-medium">{profile.comorbidities || 'None'}</span>
            </div>
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
              <span className="text-slate-400 block text-[10px] uppercase font-mono">Allergies</span>
              <span className="text-slate-200 font-medium">{profile.allergies || 'None'}</span>
            </div>
          </div>
        </div>

        {/* Clinical Facts Sub-tabs */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
          <div className="flex border-b border-slate-800 space-x-4">
            <button
              onClick={() => setActiveTab('labs')}
              className={`pb-2.5 text-xs font-semibold border-b-2 transition-colors ${
                activeTab === 'labs'
                  ? 'border-cyan-400 text-cyan-300'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              Lab Results ({labs.length})
            </button>
            <button
              onClick={() => setActiveTab('biomarkers')}
              className={`pb-2.5 text-xs font-semibold border-b-2 transition-colors ${
                activeTab === 'biomarkers'
                  ? 'border-cyan-400 text-cyan-300'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              Biomarkers ({biomarkers.length})
            </button>
            <button
              onClick={() => setActiveTab('conditions')}
              className={`pb-2.5 text-xs font-semibold border-b-2 transition-colors ${
                activeTab === 'conditions'
                  ? 'border-cyan-400 text-cyan-300'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              Conditions ({conditions.length})
            </button>
            <button
              onClick={() => setActiveTab('medications')}
              className={`pb-2.5 text-xs font-semibold border-b-2 transition-colors ${
                activeTab === 'medications'
                  ? 'border-cyan-400 text-cyan-300'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              Medications ({medications.length})
            </button>
          </div>

          {/* Tab 1: Labs */}
          {activeTab === 'labs' && (
            <div className="space-y-4">
              <div className="text-xs text-slate-400">
                Preserves raw extraction value alongside normalized LOINC test coding and data recency indicators.
              </div>
              {labs.length === 0 ? (
                <div className="bg-slate-950 p-6 rounded-lg border border-slate-800 text-center text-xs text-amber-400 flex items-center justify-center space-x-2">
                  <AlertTriangle className="w-4 h-4" />
                  <span>No lab records present for this patient profile.</span>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950 text-slate-400 font-mono uppercase border-b border-slate-800">
                      <tr>
                        <th className="p-3">Raw Extracted Value</th>
                        <th className="p-3">Normalized LOINC Value</th>
                        <th className="p-3">Lab Date</th>
                        <th className="p-3">Recency / Stale Status</th>
                        <th className="p-3">Verification</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {labs.map((lab: any) => (
                        <tr key={lab.id} className="hover:bg-slate-850">
                          <td className="p-3 font-mono text-slate-300">{lab.raw_value}</td>
                          <td className="p-3 font-medium text-cyan-300">{lab.normalized_value}</td>
                          <td className="p-3 font-mono text-slate-400">{lab.lab_date}</td>
                          <td className="p-3">
                            {lab.is_stale ? (
                              <span className="bg-purple-950 text-purple-300 border border-purple-800 px-2 py-0.5 rounded text-[10px] font-mono flex items-center w-max space-x-1">
                                <AlertTriangle className="w-3 h-3" />
                                <span>STALE (&gt;90 days)</span>
                              </span>
                            ) : (
                              <span className="bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded text-[10px] font-mono flex items-center w-max space-x-1">
                                <ShieldCheck className="w-3 h-3" />
                                <span>RECENT</span>
                              </span>
                            )}
                          </td>
                          <td className="p-3 capitalize font-mono text-[11px] text-slate-400">{lab.verification_status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Biomarkers */}
          {activeTab === 'biomarkers' && (
            <div className="space-y-4">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950 text-slate-400 font-mono uppercase border-b border-slate-800">
                    <tr>
                      <th className="p-3">Biomarker</th>
                      <th className="p-3">Raw Extracted Value</th>
                      <th className="p-3">Normalized Value</th>
                      <th className="p-3">Test Date</th>
                      <th className="p-3">Status Flag</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {biomarkers.map((b: any) => (
                      <tr key={b.id} className="hover:bg-slate-850">
                        <td className="p-3 font-bold text-slate-200">{b.biomarker_name}</td>
                        <td className="p-3 font-mono text-slate-300">{b.raw_value}</td>
                        <td className="p-3 font-medium text-cyan-300">{b.normalized_value}</td>
                        <td className="p-3 font-mono text-slate-400">{b.test_date || 'N/A'}</td>
                        <td className="p-3">
                          {b.verification_status === 'flagged' ? (
                            <span className="bg-red-950 text-red-300 border border-red-800 px-2 py-0.5 rounded text-[10px] font-mono">
                              CONFLICT FLAGGED
                            </span>
                          ) : (
                            <span className="bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded text-[10px] font-mono">
                              VERIFIED
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Tab 3: Conditions */}
          {activeTab === 'conditions' && (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950 text-slate-400 font-mono uppercase border-b border-slate-800">
                  <tr>
                    <th className="p-3">Raw Value</th>
                    <th className="p-3">Normalized Value</th>
                    <th className="p-3">Coding System</th>
                    <th className="p-3">Stage</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {conditions.map((c: any) => (
                    <tr key={c.id} className="hover:bg-slate-850">
                      <td className="p-3 font-mono text-slate-300">{c.raw_value}</td>
                      <td className="p-3 font-medium text-cyan-300">{c.normalized_value}</td>
                      <td className="p-3 font-mono text-slate-400">{c.coding_system}</td>
                      <td className="p-3 text-slate-300">{c.stage || 'N/A'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Tab 4: Medications */}
          {activeTab === 'medications' && (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950 text-slate-400 font-mono uppercase border-b border-slate-800">
                  <tr>
                    <th className="p-3">Raw Value</th>
                    <th className="p-3">Normalized RxNorm</th>
                    <th className="p-3">Dosage</th>
                    <th className="p-3">Start Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {medications.map((m: any) => (
                    <tr key={m.id} className="hover:bg-slate-850">
                      <td className="p-3 font-mono text-slate-300">{m.raw_value}</td>
                      <td className="p-3 font-medium text-cyan-300">{m.normalized_value}</td>
                      <td className="p-3 text-slate-300">{m.dosage || 'N/A'}</td>
                      <td className="p-3 font-mono text-slate-400">{m.start_date || 'N/A'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Add Clinical Fact Modal */}
        {showFactModal && (
          <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-sm font-bold text-slate-100">Add Preserved Clinical Fact</h3>
                <button onClick={() => setShowFactModal(false)} className="text-slate-400 hover:text-slate-200">
                  ✕
                </button>
              </div>

              <form onSubmit={handleAddFact} className="space-y-3 text-xs">
                <div>
                  <label className="block text-slate-400 mb-1 font-mono">Fact Category</label>
                  <select
                    value={newFact.factType}
                    onChange={(e) => setNewFact({ ...newFact, factType: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200"
                  >
                    <option value="lab">Lab Result</option>
                    <option value="biomarker">Biomarker Assay</option>
                    <option value="condition">Diagnosis / Condition</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-400 mb-1 font-mono">Raw Extracted Value</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. ANC lab 2.5 10*3/uL"
                    value={newFact.rawValue}
                    onChange={(e) => setNewFact({ ...newFact, rawValue: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1 font-mono">Normalized Standard Value</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Absolute Neutrophil Count: 2.5 10*3/uL"
                    value={newFact.normalizedValue}
                    onChange={(e) => setNewFact({ ...newFact, normalizedValue: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-400 mb-1 font-mono">Fact Date</label>
                    <input
                      type="date"
                      value={newFact.factDate}
                      onChange={(e) => setNewFact({ ...newFact, factDate: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 mb-1 font-mono">Code / LOINC</label>
                    <input
                      type="text"
                      placeholder="e.g. 26499-4"
                      value={newFact.code}
                      onChange={(e) => setNewFact({ ...newFact, code: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200"
                    />
                  </div>
                </div>

                <div className="pt-3 flex justify-end space-x-2">
                  <button
                    type="button"
                    onClick={() => setShowFactModal(false)}
                    className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded font-medium"
                  >
                    Add Fact & Update Timeline
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </PageWrapper>
  );
};
