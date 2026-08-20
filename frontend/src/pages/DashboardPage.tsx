import React, { useState } from 'react';
import { PageWrapper } from '../components/PageWrapper';
import {
  Activity,
  Users,
  Search,
  CheckSquare,
  ShieldCheck,
  Layers,
  LineChart,
  ArrowRight,
  TrendingUp,
  Clock,
  CheckCircle2,
  XCircle,
  Eye,
  PlusCircle,
  Upload,
  Play,
  FileText,
  Sliders,
  BarChart3,
  HelpCircle,
  AlertTriangle,
  RotateCcw,
  ShieldAlert,
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { MyTrialCohortSection } from '../components/MyTrialCohortSection';

interface ReviewQueueItem {
  id: string;
  patientId: string;
  trialName: string;
  matchScore: number;
  eligibility: string;
  risk: 'Low' | 'Medium' | 'High';
  status: 'Pending Review' | 'Approved' | 'Rejected';
  updated: string;
}

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'overview' | 'cohort'>('overview');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const [queueItems, setQueueItems] = useState<ReviewQueueItem[]>([
    {
      id: '1',
      patientId: 'PT-1024',
      trialName: 'NSCLC Pembrolizumab Phase II',
      matchScore: 94,
      eligibility: 'Likely Eligible',
      risk: 'Low',
      status: 'Pending Review',
      updated: '10 mins ago',
    },
    {
      id: '2',
      patientId: 'PT-1089',
      trialName: 'Metformin Adjunct Therapy',
      matchScore: 88,
      eligibility: 'Eligible',
      risk: 'Low',
      status: 'Pending Review',
      updated: '25 mins ago',
    },
    {
      id: '3',
      patientId: 'PT-2041',
      trialName: 'HER2+ Targeted Oncology',
      matchScore: 76,
      eligibility: 'Criteria Discrepancy',
      risk: 'Medium',
      status: 'Pending Review',
      updated: '1 hour ago',
    },
    {
      id: '4',
      patientId: 'PT-3105',
      trialName: 'Cardiovascular Risk Study',
      matchScore: 91,
      eligibility: 'Likely Eligible',
      risk: 'Low',
      status: 'Pending Review',
      updated: '2 hours ago',
    },
  ]);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleAction = (id: string, action: 'Approved' | 'Rejected') => {
    setQueueItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, status: action } : item))
    );
    showToast(`Patient review updated to ${action}`);
  };

  const kpiCards = [
    {
      title: 'Synthetic Patients',
      value: '24',
      subtitle: 'Active De-identified Records',
      trend: '+12% this month',
      icon: Users,
      color: 'text-sky-600',
      bg: 'bg-sky-50',
      border: 'border-sky-100',
      path: '/patients',
    },
    {
      title: 'Imported Protocols',
      value: '12',
      subtitle: 'ClinicalTrials.gov Studies',
      trend: '+3 new protocols',
      icon: Search,
      color: 'text-blue-600',
      bg: 'bg-blue-50',
      border: 'border-blue-100',
      path: '/trials/search',
    },
    {
      title: 'CRC Review Queue',
      value: '5',
      subtitle: 'Pending Human Sign-off',
      trend: 'Requires Action',
      icon: CheckSquare,
      color: 'text-amber-600',
      bg: 'bg-amber-50',
      border: 'border-amber-100',
      path: '/coordinator-queue',
    },
    {
      title: 'AI Provider Status',
      value: 'Mock Mode',
      subtitle: 'Safe Zero-API Key Default',
      trend: 'System Operational',
      icon: ShieldCheck,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50',
      border: 'border-emerald-100',
      path: '/settings',
    },
  ];

  const modules = [
    { label: 'Patient Management', path: '/patients', desc: 'Manage synthetic patient profiles & clinical records.', icon: Users },
    { label: 'Document Upload', path: '/documents/upload', desc: 'Ingest EHRs, prescriptions & lab reports.', icon: FileText },
    { label: 'Trial Search', path: '/trials/search', desc: 'Import & search ClinicalTrials.gov protocols.', icon: Search },
    { label: 'Coordinator Queue', path: '/coordinator-queue', desc: 'Human-in-the-loop eligibility review.', icon: CheckSquare },
    { label: 'Investigator Review', path: '/investigator-review', desc: 'Physician override & trial sign-off.', icon: Activity },
    { label: 'Disagreement Analytics', path: '/disagreement-analytics', desc: 'Track AI vs Human reviewer variance.', icon: BarChart3 },
    { label: 'What-If Simulator', path: '/what-if', desc: 'Simulate eligibility impact of criterion changes.', icon: HelpCircle },
    { label: 'Conflict Resolver', path: '/conflicts', desc: 'Resolve conflicting EHR facts & trial rules.', icon: AlertTriangle },
    { label: 'Re-screening Queue', path: '/rescreening-queue', desc: 'Automated re-evaluation upon criteria updates.', icon: RotateCcw },
    { label: 'Evaluation Metrics', path: '/evaluation-metrics', desc: 'Precision, recall & model benchmarks.', icon: ShieldCheck },
    { label: 'Audit Logs', path: '/audit-logs', desc: 'Complete HIPAA-compliant decision audit trace.', icon: ShieldAlert },
    { label: 'Provider Health', path: '/settings', desc: 'AI engine, Gemini & Ollama configuration.', icon: Sliders },
  ];

  return (
    <PageWrapper
      title="Research Operations Dashboard"
      subtitle="Clinical trial matching, patient screening, protocol management, and coordinator review."
      moduleName="modules/dashboard"
      icon={Activity}
    >
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-20 right-6 z-50 bg-slate-900 text-white text-xs font-semibold px-4 py-3 rounded-xl shadow-lg border border-slate-800 flex items-center space-x-2 animate-bounce">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200 space-x-6 text-xs font-semibold">
        <button
          onClick={() => setActiveTab('overview')}
          className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
            activeTab === 'overview'
              ? 'border-sky-600 text-sky-700 font-bold'
              : 'border-transparent text-slate-500 hover:text-slate-900'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>System Overview</span>
        </button>

        <button
          onClick={() => setActiveTab('cohort')}
          className={`pb-3 flex items-center space-x-2 border-b-2 transition-colors ${
            activeTab === 'cohort'
              ? 'border-sky-600 text-sky-700 font-bold'
              : 'border-transparent text-slate-500 hover:text-slate-900'
          }`}
        >
          <LineChart className="w-4 h-4" />
          <span>My Trial Cohort & Progress</span>
        </button>
      </div>

      {activeTab === 'overview' ? (
        <div className="space-y-8">
          
          {/* KPI Cards Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {kpiCards.map((kpi) => {
              const Icon = kpi.icon;
              return (
                <div
                  key={kpi.title}
                  onClick={() => navigate(kpi.path)}
                  className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs hover:shadow-md transition-all cursor-pointer group flex flex-col justify-between"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-500">{kpi.title}</span>
                    <div className={`p-2 rounded-xl ${kpi.bg} ${kpi.color} border ${kpi.border}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                  </div>

                  <div className="my-3">
                    <p className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
                      {kpi.value}
                    </p>
                    <p className="text-xs text-slate-500 mt-1 font-medium">{kpi.subtitle}</p>
                  </div>

                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px]">
                    <span className="font-semibold text-slate-600 flex items-center space-x-1">
                      <TrendingUp className="w-3 h-3 text-emerald-500" />
                      <span>{kpi.trend}</span>
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Quick Actions Panel */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
              Quick Operations Actions
            </h3>
            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={() => navigate('/patients')}
                className="flex items-center space-x-2 bg-sky-600 hover:bg-sky-700 text-white font-semibold text-xs px-4 py-2.5 rounded-xl transition-all shadow-xs"
              >
                <PlusCircle className="w-4 h-4" />
                <span>Add Patient</span>
              </button>

              <button
                onClick={() => navigate('/documents/upload')}
                className="flex items-center space-x-2 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 font-semibold text-xs px-4 py-2.5 rounded-xl transition-all"
              >
                <Upload className="w-4 h-4 text-sky-600" />
                <span>Upload Protocol</span>
              </button>

              <button
                onClick={() => navigate('/trials/search')}
                className="flex items-center space-x-2 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 font-semibold text-xs px-4 py-2.5 rounded-xl transition-all"
              >
                <Search className="w-4 h-4 text-blue-600" />
                <span>Search Trials</span>
              </button>

              <button
                onClick={() => navigate('/coordinator-queue')}
                className="flex items-center space-x-2 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 font-semibold text-xs px-4 py-2.5 rounded-xl transition-all"
              >
                <CheckSquare className="w-4 h-4 text-amber-600" />
                <span>Open CRC Queue</span>
              </button>

              <button
                onClick={() => navigate('/matching-engine')}
                className="flex items-center space-x-2 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 font-semibold text-xs px-4 py-2.5 rounded-xl transition-all"
              >
                <Play className="w-4 h-4 text-emerald-600" />
                <span>Run Patient Matching</span>
              </button>
            </div>
          </div>

          {/* Section A: Trial & Patient Overview Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            {/* Patient Matching Overview */}
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs flex flex-col justify-between space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 className="font-bold text-base text-slate-900">Patient Matching Overview</h3>
                <span className="text-xs bg-sky-50 text-sky-700 font-semibold px-2.5 py-1 rounded-full border border-sky-100">
                  66.7% Match Rate
                </span>
              </div>

              <div className="grid grid-cols-4 gap-2 text-center my-2">
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <p className="text-xl font-bold text-slate-900">24</p>
                  <p className="text-[11px] text-slate-500 font-medium mt-0.5">Total</p>
                </div>
                <div className="bg-emerald-50 p-3 rounded-xl border border-emerald-100">
                  <p className="text-xl font-bold text-emerald-700">16</p>
                  <p className="text-[11px] text-emerald-600 font-medium mt-0.5">Matched</p>
                </div>
                <div className="bg-amber-50 p-3 rounded-xl border border-amber-100">
                  <p className="text-xl font-bold text-amber-700">5</p>
                  <p className="text-[11px] text-amber-600 font-medium mt-0.5">Pending</p>
                </div>
                <div className="bg-rose-50 p-3 rounded-xl border border-rose-100">
                  <p className="text-xl font-bold text-rose-700">3</p>
                  <p className="text-[11px] text-rose-600 font-medium mt-0.5">Excluded</p>
                </div>
              </div>

              {/* Progress Visualization Bar */}
              <div className="space-y-1.5 pt-2">
                <div className="flex justify-between text-xs text-slate-600 font-semibold">
                  <span>Match Progress Spectrum</span>
                  <span>16 / 24 Patients</span>
                </div>
                <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden flex">
                  <div className="bg-emerald-500 h-full" style={{ width: '66.7%' }} title="Matched"></div>
                  <div className="bg-amber-400 h-full" style={{ width: '20.8%' }} title="Pending"></div>
                  <div className="bg-rose-400 h-full" style={{ width: '12.5%' }} title="Excluded"></div>
                </div>
              </div>
            </div>

            {/* Trial Progress Overview */}
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs flex flex-col justify-between space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 className="font-bold text-base text-slate-900">Trial Progress & Status</h3>
                <span className="text-xs bg-emerald-50 text-emerald-700 font-semibold px-2.5 py-1 rounded-full border border-emerald-100">
                  12 Active Trials
                </span>
              </div>

              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                    <span>Recruiting Studies (ClinicalTrials.gov)</span>
                    <span className="text-sky-600">8 / 12 Studies</span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                    <div className="bg-sky-600 h-full rounded-full" style={{ width: '66.7%' }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                    <span>Screening Completed</span>
                    <span className="text-emerald-600">18 Patients</span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                    <div className="bg-emerald-500 h-full rounded-full" style={{ width: '75%' }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                    <span>Pending CRC Coordinator Sign-Off</span>
                    <span className="text-amber-600">5 Reviews Pending</span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                    <div className="bg-amber-500 h-full rounded-full" style={{ width: '40%' }}></div>
                  </div>
                </div>
              </div>
            </div>

          </div>

          {/* CRC Review Queue Table Section */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h3 className="font-bold text-lg text-slate-900">Coordinator Review Queue</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  AI-assisted pre-screening recommendations requiring human reviewer sign-off.
                </p>
              </div>
              <Link
                to="/coordinator-queue"
                className="text-xs text-sky-600 hover:text-sky-700 font-semibold flex items-center space-x-1"
              >
                <span>View Full Queue</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-700">
                <thead className="bg-slate-50 text-slate-500 font-semibold border-y border-slate-200">
                  <tr>
                    <th className="py-3 px-4">Patient ID</th>
                    <th className="py-3 px-4">Trial Protocol</th>
                    <th className="py-3 px-4">Match Score</th>
                    <th className="py-3 px-4">Eligibility</th>
                    <th className="py-3 px-4">Risk Level</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Updated</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-medium">
                  {queueItems.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3.5 px-4 font-bold text-slate-900">{item.patientId}</td>
                      <td className="py-3.5 px-4 text-slate-800 font-semibold">{item.trialName}</td>
                      <td className="py-3.5 px-4">
                        <span className="font-bold text-sky-700 bg-sky-50 px-2 py-0.5 rounded border border-sky-100">
                          {item.matchScore}%
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`px-2.5 py-1 rounded-full text-[11px] font-bold ${
                            item.eligibility.includes('Eligible')
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : 'bg-amber-50 text-amber-700 border border-amber-200'
                          }`}
                        >
                          {item.eligibility}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                            item.risk === 'Low'
                              ? 'bg-slate-100 text-slate-700'
                              : 'bg-rose-50 text-rose-700 border border-rose-200'
                          }`}
                        >
                          {item.risk} Risk
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`font-semibold ${
                            item.status === 'Approved'
                              ? 'text-emerald-600'
                              : item.status === 'Rejected'
                              ? 'text-rose-600'
                              : 'text-amber-600'
                          }`}
                        >
                          {item.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-slate-400">{item.updated}</td>
                      <td className="py-3.5 px-4 text-right">
                        {item.status === 'Pending Review' ? (
                          <div className="flex items-center justify-end space-x-1.5">
                            <button
                              onClick={() => navigate(`/patients`)}
                              className="p-1.5 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg"
                              title="View Patient Details"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleAction(item.id, 'Approved')}
                              className="p-1.5 text-emerald-600 hover:bg-emerald-50 rounded-lg"
                              title="Approve Match"
                            >
                              <CheckCircle2 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleAction(item.id, 'Rejected')}
                              className="p-1.5 text-rose-600 hover:bg-rose-50 rounded-lg"
                              title="Reject Match"
                            >
                              <XCircle className="w-4 h-4" />
                            </button>
                          </div>
                        ) : (
                          <span className="text-[11px] text-slate-400 font-semibold italic">Signed Off</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Module Navigation Grid */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
            <h3 className="font-bold text-lg text-slate-900">Clinical Platform Operations Modules</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {modules.map((mod) => {
                const Icon = mod.icon;
                return (
                  <Link
                    key={mod.path}
                    to={mod.path}
                    className="bg-white hover:bg-slate-50/80 border border-slate-200 rounded-xl p-4 transition-all hover:shadow-sm group flex flex-col justify-between space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="p-2 bg-sky-50 text-sky-600 rounded-lg border border-sky-100">
                        <Icon className="w-4 h-4" />
                      </div>
                      <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-sky-600 group-hover:translate-x-1 transition-all" />
                    </div>

                    <div>
                      <h4 className="font-bold text-xs text-slate-900 group-hover:text-sky-600 transition-colors">
                        {mod.label}
                      </h4>
                      <p className="text-[11px] text-slate-500 mt-1 leading-snug">
                        {mod.desc}
                      </p>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>

        </div>
      ) : (
        <MyTrialCohortSection />
      )}
    </PageWrapper>
  );
};
