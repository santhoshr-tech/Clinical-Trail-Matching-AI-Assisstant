import React, { useState, useEffect } from 'react';
import { PageWrapper } from '../components/PageWrapper';
import {
  CheckSquare,
  Sparkles,
  CheckCircle,
  XCircle,
  Clock,
  Edit3,
  Plus,
  Layers,
  Filter,
  ShieldCheck,
  AlertTriangle
} from 'lucide-react';
import { apiGet, apiPost, apiPut } from '../utils/apiClient';

interface CriterionNode {
  id: string;
  trial_id: string;
  criterion_type: 'inclusion' | 'exclusion';
  category: string;
  operator: string;
  value_primary?: string;
  value_secondary?: string;
  unit?: string;
  temporal_window?: string;
  is_negated: boolean;
  logic_group: string;
  raw_text: string;
  classification_confidence: number;
  approval_status: 'pending' | 'approved' | 'rejected';
  version: number;
}

export const CriteriaExtractionReviewPage: React.FC = () => {
  const [selectedTrialId, setSelectedTrialId] = useState<string>('t-nct04500000');
  const [criteria, setCriteria] = useState<CriterionNode[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'all' | 'inclusion' | 'exclusion'>('all');
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('all');
  const [editingCriterion, setEditingCriterion] = useState<CriterionNode | null>(null);
  const [manualFormOpen, setManualFormOpen] = useState<boolean>(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchCriteria = async () => {
    setLoading(true);
    try {
      const res = await apiGet<CriterionNode[]>(`/criteria/trial/${selectedTrialId}`);
      if (res.data) {
        setCriteria(res.data);
      }
    } catch (err) {
      console.error("Error fetching criteria:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCriteria();
  }, [selectedTrialId]);

  const handleParseProtocol = async () => {
    setLoading(true);
    try {
      const res = await apiPost<CriterionNode[]>(`/criteria/parse/${selectedTrialId}`);
      if (res.data) {
        setCriteria(res.data);
        setSuccessMsg(`Successfully parsed ${res.data.length} structured rule nodes!`);
        setTimeout(() => setSuccessMsg(null), 4000);
      }
    } catch (err) {
      console.error("Parse error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      const res = await apiPost<CriterionNode>(`/criteria/${id}/approve`);
      if (res.data) {
        setCriteria(prev => prev.map(c => c.id === id ? { ...c, approval_status: 'approved' } : c));
      }
    } catch (err) {
      console.error("Approve error:", err);
    }
  };

  const handleReject = async (id: string) => {
    try {
      const res = await apiPost<CriterionNode>(`/criteria/${id}/reject`);
      if (res.data) {
        setCriteria(prev => prev.map(c => c.id === id ? { ...c, approval_status: 'rejected' } : c));
      }
    } catch (err) {
      console.error("Reject error:", err);
    }
  };

  const handleSaveEdit = async () => {
    if (!editingCriterion) return;
    try {
      const res = await apiPut<CriterionNode>(`/criteria/${editingCriterion.id}`, {
        category: editingCriterion.category,
        operator: editingCriterion.operator,
        value_primary: editingCriterion.value_primary,
        unit: editingCriterion.unit,
        temporal_window: editingCriterion.temporal_window,
        is_negated: editingCriterion.is_negated,
        change_summary: "Updated via UI review editor"
      });
      if (res.data) {
        setCriteria(prev => prev.map(c => c.id === editingCriterion.id ? res.data! : c));
        setEditingCriterion(null);
      }
    } catch (err) {
      console.error("Save edit error:", err);
    }
  };

  const filteredCriteria = criteria.filter(c => {
    if (activeTab !== 'all' && c.criterion_type !== activeTab) return false;
    if (statusFilter !== 'all' && c.approval_status !== statusFilter) return false;
    return true;
  });

  return (
    <PageWrapper
      title="Criteria Logic Node Review & Rule Structuring"
      subtitle="Classify eligibility text into 11 domain categories, 12 operator types, and enforce approval gatekeeping."
      moduleName="modules/criteria"
      icon={CheckSquare}
    >
      <div className="space-y-6">
        {/* Header Controls */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <Layers className="h-6 w-6 text-sky-400" />
            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Target Trial Protocol</label>
              <select
                value={selectedTrialId}
                onChange={(e) => setSelectedTrialId(e.target.value)}
                className="mt-1 bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-1.5 focus:ring-2 focus:ring-sky-500 focus:outline-none"
              >
                <option value="t-nct04500000">NCT04500000 (Pembrolizumab Phase 3 NSCLC)</option>
                <option value="t-nct04611111">NCT04611111 (Osimertinib Targeted Evaluation)</option>
                <option value="t-nct04722222">NCT04722222 (Immunotherapy Safety Trial)</option>
              </select>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={handleParseProtocol}
              disabled={loading}
              className="flex items-center space-x-2 bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white font-medium text-sm px-4 py-2 rounded-lg transition shadow-md disabled:opacity-50"
            >
              <Sparkles className="h-4 w-4" />
              <span>{loading ? 'Structuring Criteria...' : 'Parse & Structure Protocol'}</span>
            </button>
          </div>
        </div>

        {successMsg && (
          <div className="p-4 bg-emerald-950/60 border border-emerald-500/40 rounded-xl text-emerald-300 text-sm flex items-center space-x-2">
            <CheckCircle className="h-5 w-5 text-emerald-400 flex-shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Filter Controls */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="flex space-x-2">
            {(['all', 'inclusion', 'exclusion'] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                  activeTab === tab
                    ? 'bg-sky-600/20 text-sky-400 border border-sky-500/30'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                }`}
              >
                {tab.toUpperCase()} ({criteria.filter(c => tab === 'all' || c.criterion_type === tab).length})
              </button>
            ))}
          </div>

          <div className="flex items-center space-x-2">
            <Filter className="h-4 w-4 text-slate-400" />
            <span className="text-xs text-slate-400">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              className="bg-slate-800 border border-slate-700 text-slate-300 text-xs rounded-lg px-2.5 py-1 focus:outline-none"
            >
              <option value="all">All Statuses</option>
              <option value="pending">Pending Review</option>
              <option value="approved">Approved (Screening Ready)</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>
        </div>

        {/* Criteria Node Grid */}
        {filteredCriteria.length === 0 ? (
          <div className="text-center py-12 bg-slate-900/50 border border-slate-800 rounded-xl">
            <AlertTriangle className="h-10 w-10 text-slate-500 mx-auto mb-3" />
            <p className="text-slate-400 text-sm">No criteria logic nodes found for the selected filters.</p>
            <p className="text-slate-500 text-xs mt-1">Click "Parse & Structure Protocol" above to extract rules automatically.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredCriteria.map(node => (
              <div
                key={node.id}
                className={`p-5 rounded-xl border transition flex flex-col justify-between ${
                  node.approval_status === 'approved'
                    ? 'bg-emerald-950/15 border-emerald-500/30'
                    : node.approval_status === 'rejected'
                    ? 'bg-rose-950/15 border-rose-500/30'
                    : 'bg-slate-900 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold uppercase ${
                      node.criterion_type === 'inclusion' ? 'bg-sky-950 text-sky-400 border border-sky-500/30' : 'bg-amber-950 text-amber-400 border border-amber-500/30'
                    }`}>
                      {node.criterion_type}
                    </span>

                    <span className={`text-xs px-2.5 py-0.5 rounded-full font-semibold flex items-center space-x-1 ${
                      node.approval_status === 'approved'
                        ? 'bg-emerald-900/50 text-emerald-400 border border-emerald-500/40'
                        : node.approval_status === 'rejected'
                        ? 'bg-rose-900/50 text-rose-400 border border-rose-500/40'
                        : 'bg-amber-900/50 text-amber-300 border border-amber-500/40'
                    }`}>
                      {node.approval_status === 'approved' && <ShieldCheck className="h-3 w-3 mr-1" />}
                      {node.approval_status === 'pending' && <Clock className="h-3 w-3 mr-1" />}
                      <span>{node.approval_status.toUpperCase()}</span>
                    </span>
                  </div>

                  <p className="text-slate-200 text-sm font-medium mb-3 leading-relaxed">
                    "{node.raw_text}"
                  </p>

                  {/* Structuring Details */}
                  <div className="grid grid-cols-2 gap-2 text-xs mb-4">
                    <div className="bg-slate-950/60 p-2 rounded border border-slate-800">
                      <span className="text-slate-500 block text-[10px] uppercase">Category</span>
                      <span className="text-sky-300 font-semibold">{node.category}</span>
                    </div>

                    <div className="bg-slate-950/60 p-2 rounded border border-slate-800">
                      <span className="text-slate-500 block text-[10px] uppercase">Operator & Value</span>
                      <span className="text-indigo-300 font-semibold">
                        {node.operator} {node.value_primary || ''} {node.unit || ''}
                      </span>
                    </div>

                    {node.temporal_window && (
                      <div className="bg-slate-950/60 p-2 rounded border border-slate-800 col-span-2">
                        <span className="text-slate-500 block text-[10px] uppercase">Temporal Window</span>
                        <span className="text-amber-300 font-semibold">{node.temporal_window}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Footer Controls */}
                <div className="flex items-center justify-between pt-3 border-t border-slate-800/80 text-xs">
                  <span className="text-slate-500">
                    Confidence: {(node.classification_confidence * 100).toFixed(0)}% (v{node.version})
                  </span>

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setEditingCriterion(node)}
                      className="p-1.5 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                      title="Edit Rule"
                    >
                      <Edit3 className="h-4 w-4" />
                    </button>

                    {node.approval_status !== 'approved' && (
                      <button
                        onClick={() => handleApprove(node.id)}
                        className="flex items-center space-x-1 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/40 px-2.5 py-1 rounded transition"
                      >
                        <CheckCircle className="h-3.5 w-3.5" />
                        <span>Approve</span>
                      </button>
                    )}

                    {node.approval_status !== 'rejected' && (
                      <button
                        onClick={() => handleReject(node.id)}
                        className="flex items-center space-x-1 bg-rose-600/20 hover:bg-rose-600/30 text-rose-400 border border-rose-500/40 px-2.5 py-1 rounded transition"
                      >
                        <XCircle className="h-3.5 w-3.5" />
                        <span>Reject</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Edit Modal */}
        {editingCriterion && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4">
              <h3 className="text-lg font-bold text-slate-100 flex items-center space-x-2">
                <Edit3 className="h-5 w-5 text-sky-400" />
                <span>Edit Structured Rule Node (v{editingCriterion.version})</span>
              </h3>

              <div>
                <label className="text-xs text-slate-400 font-semibold block mb-1">Criterion Raw Text</label>
                <input
                  type="text"
                  value={editingCriterion.raw_text}
                  onChange={(e) => setEditingCriterion({ ...editingCriterion, raw_text: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg p-2.5"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-slate-400 font-semibold block mb-1">Category</label>
                  <select
                    value={editingCriterion.category}
                    onChange={(e) => setEditingCriterion({ ...editingCriterion, category: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg p-2.5"
                  >
                    <option value="demographic">demographic</option>
                    <option value="diagnosis">diagnosis</option>
                    <option value="stage">stage</option>
                    <option value="laboratory">laboratory</option>
                    <option value="biomarker">biomarker</option>
                    <option value="medication">medication</option>
                    <option value="prior_treatment">prior_treatment</option>
                    <option value="comorbidity">comorbidity</option>
                    <option value="temporal">temporal</option>
                    <option value="procedural">procedural</option>
                    <option value="administrative">administrative</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs text-slate-400 font-semibold block mb-1">Operator</label>
                  <select
                    value={editingCriterion.operator}
                    onChange={(e) => setEditingCriterion({ ...editingCriterion, operator: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg p-2.5"
                  >
                    <option value="greater_than_or_equal">greater_than_or_equal</option>
                    <option value="less_than_or_equal">less_than_or_equal</option>
                    <option value="equals">equals</option>
                    <option value="between">between</option>
                    <option value="exists">exists</option>
                    <option value="absent">absent</option>
                    <option value="contains">contains</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-slate-400 font-semibold block mb-1">Primary Value</label>
                  <input
                    type="text"
                    value={editingCriterion.value_primary || ''}
                    onChange={(e) => setEditingCriterion({ ...editingCriterion, value_primary: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg p-2.5"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-400 font-semibold block mb-1">Unit</label>
                  <input
                    type="text"
                    value={editingCriterion.unit || ''}
                    onChange={(e) => setEditingCriterion({ ...editingCriterion, unit: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg p-2.5"
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-3 pt-4 border-t border-slate-800">
                <button
                  onClick={() => setEditingCriterion(null)}
                  className="px-4 py-2 rounded-lg text-sm text-slate-400 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveEdit}
                  className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-sm font-medium"
                >
                  Save Changes & Increment Version
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </PageWrapper>
  );
};
