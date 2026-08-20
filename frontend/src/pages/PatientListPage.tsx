import React, { useEffect, useState } from 'react';
import { PageWrapper } from '../components/PageWrapper';
import { Users, Search, Plus, Calendar, MapPin, AlertCircle, ShieldAlert, CheckCircle2, Filter, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const PatientListPage: React.FC = () => {
  const [patients, setPatients] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);

  // New Patient Form State
  const [newPatient, setNewPatient] = useState({
    mrnSynthetic: `SYNTH-${Math.floor(100000 + Math.random() * 900000)}`,
    age: 55,
    gender: 'Female',
    location: 'Site 01 - Oncology Wing',
    primaryDiagnosis: 'Stage IV Non-Small Cell Lung Cancer',
    diseaseStage: 'Stage IV',
    comorbidities: 'None',
    allergies: 'Penicillin'
  });

  const { user, hasRole } = useAuth();

  const fetchPatients = (query: string = '') => {
    setLoading(true);
    const url = query ? `/api/v1/patients?query=${encodeURIComponent(query)}` : '/api/v1/patients';
    fetch(url, {
      headers: {
        'X-User-Email': user?.email || '',
        'X-User-Role': user?.role || '',
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success && Array.isArray(data.data)) {
          setPatients(data.data);
        } else {
          setError(data.error || 'Failed to fetch patient records');
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchPatients('');
  }, [user]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchPatients(searchQuery);
  };

  const handleScenarioFilter = (scenarioKey: string) => {
    if (selectedScenario === scenarioKey) {
      setSelectedScenario(null);
      setSearchQuery('');
      fetchPatients('');
    } else {
      setSelectedScenario(scenarioKey);
      setSearchQuery(scenarioKey);
      fetchPatients(scenarioKey);
    }
  };

  const handleCreatePatient = (e: React.FormEvent) => {
    e.preventDefault();
    fetch('/api/v1/patients', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Email': user?.email || '',
        'X-User-Role': user?.role || '',
      },
      body: JSON.stringify(newPatient)
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          setShowAddModal(false);
          fetchPatients('');
        } else {
          alert(`Failed to create patient: ${data.error || 'Unknown error'}`);
        }
      })
      .catch((err) => alert(`Error: ${err.message}`));
  };

  const getScenarioBadge = (mrn: string) => {
    switch (mrn) {
      case 'SYNTH-SCENARIO-A':
        return <span className="bg-emerald-950/80 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded text-[10px] font-mono">Fully Eligible</span>;
      case 'SYNTH-SCENARIO-B':
        return <span className="bg-amber-950/80 text-amber-300 border border-amber-800 px-2 py-0.5 rounded text-[10px] font-mono">Missing Lab</span>;
      case 'SYNTH-SCENARIO-C':
        return <span className="bg-red-950/80 text-red-300 border border-red-800 px-2 py-0.5 rounded text-[10px] font-mono">Conflicting Biomarker</span>;
      case 'SYNTH-SCENARIO-D':
        return <span className="bg-purple-950/80 text-purple-300 border border-purple-800 px-2 py-0.5 rounded text-[10px] font-mono">Stale Lab (&gt;90d)</span>;
      case 'SYNTH-SCENARIO-E':
        return <span className="bg-rose-950/80 text-rose-300 border border-rose-800 px-2 py-0.5 rounded text-[10px] font-mono">Treatment Exclusion</span>;
      default:
        return <span className="bg-cyan-950/80 text-cyan-300 border border-cyan-800 px-2 py-0.5 rounded text-[10px] font-mono">Synthetic Record</span>;
    }
  };

  return (
    <PageWrapper
      title="Synthetic Patient Profiles"
      subtitle="Search, filter, and review de-identified patient cohorts, clinical facts, and data recency indicators."
      moduleName="modules/patients"
      icon={Users}
    >
      <div className="space-y-6">
        {/* Synthetic Seed Scenario Selector Quick-Filters */}
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-3">
          <div className="flex items-center space-x-2 text-xs font-semibold text-slate-300">
            <Filter className="w-4 h-4 text-cyan-400" />
            <span>Synthetic Seed Scenarios (Phase 3 Benchmark Sets)</span>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <button
              onClick={() => handleScenarioFilter('SYNTH-SCENARIO-A')}
              className={`px-3 py-1.5 rounded-lg border transition-all ${
                selectedScenario === 'SYNTH-SCENARIO-A'
                  ? 'bg-emerald-900/80 border-emerald-500 text-emerald-200'
                  : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
              }`}
            >
              🎯 Scenario A (Fully Eligible)
            </button>
            <button
              onClick={() => handleScenarioFilter('SYNTH-SCENARIO-B')}
              className={`px-3 py-1.5 rounded-lg border transition-all ${
                selectedScenario === 'SYNTH-SCENARIO-B'
                  ? 'bg-amber-900/80 border-amber-500 text-amber-200'
                  : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
              }`}
            >
              ⚠️ Scenario B (Missing Lab)
            </button>
            <button
              onClick={() => handleScenarioFilter('SYNTH-SCENARIO-C')}
              className={`px-3 py-1.5 rounded-lg border transition-all ${
                selectedScenario === 'SYNTH-SCENARIO-C'
                  ? 'bg-red-900/80 border-red-500 text-red-200'
                  : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
              }`}
            >
              💥 Scenario C (Conflicting Biomarker)
            </button>
            <button
              onClick={() => handleScenarioFilter('SYNTH-SCENARIO-D')}
              className={`px-3 py-1.5 rounded-lg border transition-all ${
                selectedScenario === 'SYNTH-SCENARIO-D'
                  ? 'bg-purple-900/80 border-purple-500 text-purple-200'
                  : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
              }`}
            >
              ⏳ Scenario D (Stale Lab &gt; 90d)
            </button>
            <button
              onClick={() => handleScenarioFilter('SYNTH-SCENARIO-E')}
              className={`px-3 py-1.5 rounded-lg border transition-all ${
                selectedScenario === 'SYNTH-SCENARIO-E'
                  ? 'bg-rose-900/80 border-rose-500 text-rose-200'
                  : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
              }`}
            >
              🚫 Scenario E (Prior Treatment Exclusion)
            </button>
          </div>
        </div>

        {/* Search & Actions Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <form onSubmit={handleSearchSubmit} className="flex items-center space-x-2 w-full sm:w-auto flex-1 max-w-lg">
            <div className="relative w-full">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search MRN, diagnosis, or site location..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
            <button type="submit" className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3 py-2 rounded-lg font-medium border border-slate-700">
              Filter
            </button>
          </form>

          {hasRole(['admin', 'research_coordinator', 'investigator']) && (
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center space-x-1.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs px-3.5 py-2 rounded-lg font-semibold shadow-md shadow-cyan-950"
            >
              <Plus className="w-4 h-4" />
              <span>New Patient Profile</span>
            </button>
          )}
        </div>

        {loading ? (
          <div className="text-center py-12 text-xs text-slate-400 animate-pulse">Loading synthetic patient registry...</div>
        ) : error ? (
          <div className="bg-red-950/50 border border-red-800 text-red-300 p-4 rounded-xl text-xs">{error}</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {patients.map((pat) => (
              <div key={pat.id} className="bg-slate-900 border border-slate-800 hover:border-cyan-500/40 rounded-xl p-5 space-y-4 transition-all">
                <div className="flex items-center justify-between border-b border-slate-200 pb-3">
                  <div>
                    <span className="font-bold text-base text-[#172033] tracking-tight">{pat.mrnSynthetic}</span>
                    <div className="text-xs text-[#4B5B73] font-medium flex items-center space-x-2 mt-0.5">
                      <span>{pat.age} yrs • {pat.gender}</span>
                      <span>•</span>
                      <span className="font-semibold text-[#243247]">{pat.diseaseStage}</span>
                    </div>
                  </div>
                  {getScenarioBadge(pat.mrnSynthetic)}
                </div>

                <div className="space-y-1.5 text-xs">
                  <div className="font-bold text-sm text-[#243247] line-clamp-2 leading-snug">{pat.primaryDiagnosis}</div>
                  <div className="flex items-center space-x-1.5 text-[#52647C] text-xs font-medium">
                    <MapPin className="w-3.5 h-3.5 text-[#64748B] shrink-0" />
                    <span className="truncate">{pat.location}</span>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-200 flex items-center justify-between text-xs">
                  <div className="text-xs text-[#64748B] font-mono font-medium">v{pat.version} • Synthetic Record</div>
                  <div className="flex items-center space-x-2">
                    <Link
                      to={`/patients/${pat.id}/timeline`}
                      className="text-[#4B5B73] hover:text-[#172033] text-xs font-semibold transition-colors"
                    >
                      Timeline
                    </Link>
                    <Link
                      to={`/patients/${pat.id}`}
                      className="bg-sky-600 hover:bg-sky-700 text-white px-3 py-1.5 rounded-lg text-xs font-bold transition-all shadow-xs"
                    >
                      Details & Facts
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Add Patient Modal */}
        {showAddModal && (
          <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-sm font-bold text-slate-100">Add Synthetic Patient Profile</h3>
                <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-slate-200">
                  <X className="w-4 h-4" />
                </button>
              </div>

              <form onSubmit={handleCreatePatient} className="space-y-3 text-xs">
                <div>
                  <label className="block text-slate-400 mb-1 font-mono">Synthetic MRN</label>
                  <input
                    type="text"
                    required
                    value={newPatient.mrnSynthetic}
                    onChange={(e) => setNewPatient({ ...newPatient, mrnSynthetic: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-400 mb-1 font-mono">Age</label>
                    <input
                      type="number"
                      required
                      value={newPatient.age}
                      onChange={(e) => setNewPatient({ ...newPatient, age: parseInt(e.target.value) || 0 })}
                      className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 mb-1 font-mono">Gender</label>
                    <select
                      value={newPatient.gender}
                      onChange={(e) => setNewPatient({ ...newPatient, gender: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200"
                    >
                      <option value="Female">Female</option>
                      <option value="Male">Male</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-slate-400 mb-1 font-mono">Diagnosis</label>
                  <input
                    type="text"
                    required
                    value={newPatient.primaryDiagnosis}
                    onChange={(e) => setNewPatient({ ...newPatient, primaryDiagnosis: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-400 mb-1 font-mono">Disease Stage</label>
                    <input
                      type="text"
                      value={newPatient.diseaseStage}
                      onChange={(e) => setNewPatient({ ...newPatient, diseaseStage: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 mb-1 font-mono">Location</label>
                    <input
                      type="text"
                      value={newPatient.location}
                      onChange={(e) => setNewPatient({ ...newPatient, location: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-slate-400 mb-1 font-mono">Comorbidities</label>
                  <input
                    type="text"
                    value={newPatient.comorbidities}
                    onChange={(e) => setNewPatient({ ...newPatient, comorbidities: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1 font-mono">Allergies</label>
                  <input
                    type="text"
                    value={newPatient.allergies}
                    onChange={(e) => setNewPatient({ ...newPatient, allergies: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200"
                  />
                </div>

                <div className="pt-3 flex justify-end space-x-2">
                  <button
                    type="button"
                    onClick={() => setShowAddModal(false)}
                    className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded font-medium"
                  >
                    Save Profile
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

