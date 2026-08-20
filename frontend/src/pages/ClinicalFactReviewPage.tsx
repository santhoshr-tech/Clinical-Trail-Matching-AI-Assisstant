import React, { useState, useEffect } from 'react';
import { PageWrapper } from '../components/PageWrapper';
import {
  FileText,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Layers,
  Edit,
  Filter,
  CheckSquare,
  RefreshCw,
  Search
} from 'lucide-react';
import { apiGet, apiPost } from '../utils/apiClient';

interface ExtractedFact {
  id: string;
  patient_id: string;
  category: string;
  raw_text: string;
  canonical_label: string;
  mapping_method: string;
  mapping_confidence: number;
  is_negated: boolean;
  temporal_expression?: string;
  data_date?: string;
  is_stale: boolean;
  numeric_value?: number;
  raw_unit?: string;
  normalized_unit?: string;
  source_page: number;
  start_char: number;
  end_char: number;
  review_status: 'pending' | 'approved' | 'edited' | 'rejected';
  has_conflict: boolean;
  conflict_details?: string;
}

export const ClinicalFactReviewPage: React.FC = () => {
  const [patientId, setPatientId] = useState<string>('11111111-1111-1111-1111-111111111111');
  const [facts, setFacts] = useState<ExtractedFact[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [editingFactId, setEditingFactId] = useState<string | null>(null);
  const [editLabelText, setEditLabelText] = useState<string>('');

  const fetchFacts = async () => {
    setLoading(true);
    try {
      const res = await apiGet<ExtractedFact[]>(`/extraction/facts/patient/${patientId}`);
      if (res.data) {
        setFacts(res.data);
      }
    } catch (err) {
      console.error('Failed to load extracted facts', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRunExtraction = async () => {
    setLoading(true);
    try {
      const sampleText = `
        Pathology & Clinical History:
        Patient diagnosed with Stage IV Non-Small Cell Lung Cancer.
        No history of hypertension.
        Laboratory Results: Absolute Neutrophil Count (ANC) 2.8 10*3/uL.
        Biomarker Panel: EGFR Mutation POSITIVE (Exon 19 Deletion). PD-L1 TPS 60%.
        Current Medication: Pembrolizumab 200mg IV.
      `;
      await apiPost('/extraction/extract', {
        patient_id: patientId,
        document_id: `doc-${patientId.slice(0, 8)}`,
        document_text: sampleText
      });
      await fetchFacts();
    } catch (err) {
      console.error('Extraction failed', err);
    } finally {
      setLoading(false);
    }
  };

  const handleReviewAction = async (factId: string, status: 'approved' | 'rejected' | 'edited', newLabel?: string) => {
    try {
      await apiPost('/extraction/review', {
        fact_id: factId,
        review_status: status,
        edited_canonical_label: newLabel
      });
      setEditingFactId(null);
      fetchFacts();
    } catch (err) {
      console.error('Review action failed', err);
    }
  };

  useEffect(() => {
    fetchFacts();
  }, [patientId]);

  const filteredFacts = facts.filter(f => selectedCategory === 'all' || f.category === selectedCategory);

  return (
    <PageWrapper
      title="Clinical Fact Extraction & Human Review"
      subtitle="Structured 8-stage NLP pipeline for clinical facts, negation, temporal recency, and conflict review."
      moduleName="modules/extraction"
      icon={Layers}
    >
      <div className="space-y-6">
        {/* Header bar */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-3 w-full sm:w-auto">
            <label className="text-xs font-semibold text-slate-400 uppercase">Target Patient:</label>
            <select
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-sky-500 focus:outline-none"
            >
              <option value="11111111-1111-1111-1111-111111111111">Patient Scenario A (Stage IV NSCLC)</option>
              <option value="22222222-2222-2222-2222-222222222222">Patient Scenario B (Low ANC Lab)</option>
              <option value="33333333-3333-3333-3333-333333333333">Patient Scenario C (Conflicting Biomarker)</option>
            </select>
          </div>

          <div className="flex items-center space-x-3 w-full sm:w-auto">
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2"
            >
              <option value="all">All Categories</option>
              <option value="diagnosis">Diagnosis</option>
              <option value="lab">Laboratory</option>
              <option value="biomarker">Biomarker</option>
              <option value="medication">Medication</option>
              <option value="comorbidity">Comorbidity</option>
            </select>

            <button
              onClick={handleRunExtraction}
              disabled={loading}
              className="flex items-center space-x-2 bg-sky-500 hover:bg-sky-400 text-white font-semibold text-xs px-4 py-2.5 rounded-lg transition"
            >
              <RefreshCw className="h-4 w-4" />
              <span>Run Pipeline</span>
            </button>
          </div>
        </div>

        {/* Facts List Grid */}
        <div className="space-y-4">
          {filteredFacts.length === 0 ? (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-8 text-center text-slate-400 text-sm">
              No extracted facts found for this patient. Click "Run Pipeline" to extract clinical concepts from source documents.
            </div>
          ) : (
            filteredFacts.map((fact) => (
              <div key={fact.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-md flex flex-col md:flex-row justify-between gap-4">
                <div className="space-y-2 flex-1">
                  <div className="flex items-center space-x-3">
                    <span className="text-[10px] font-bold uppercase tracking-wider bg-slate-800 text-sky-400 px-2.5 py-1 rounded">
                      {fact.category}
                    </span>

                    {fact.is_negated && (
                      <span className="text-[10px] font-bold uppercase bg-rose-950/80 text-rose-300 border border-rose-800/80 px-2 py-0.5 rounded">
                        NEGATED
                      </span>
                    )}

                    {fact.is_stale && (
                      <span className="text-[10px] font-bold uppercase bg-amber-950/80 text-amber-300 border border-amber-800/80 px-2 py-0.5 rounded">
                        STALE DATA
                      </span>
                    )}

                    {fact.has_conflict && (
                      <span className="text-[10px] font-bold uppercase bg-purple-950/80 text-purple-300 border border-purple-800/80 px-2 py-0.5 rounded flex items-center space-x-1">
                        <AlertTriangle className="h-3 w-3 text-purple-400" />
                        <span>CONFLICT</span>
                      </span>
                    )}
                  </div>

                  <div className="space-y-1">
                    {editingFactId === fact.id ? (
                      <div className="flex items-center space-x-2 pt-1">
                        <input
                          type="text"
                          value={editLabelText}
                          onChange={(e) => setEditLabelText(e.target.value)}
                          className="bg-slate-950 border border-slate-700 text-slate-100 text-xs px-3 py-1.5 rounded flex-1"
                        />
                        <button
                          onClick={() => handleReviewAction(fact.id, 'edited', editLabelText)}
                          className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs px-3 py-1.5 rounded font-semibold"
                        >
                          Save
                        </button>
                      </div>
                    ) : (
                      <h4 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                        <span>{fact.canonical_label}</span>
                        <button
                          onClick={() => { setEditingFactId(fact.id); setEditLabelText(fact.canonical_label); }}
                          className="text-slate-500 hover:text-sky-400"
                        >
                          <Edit className="h-3.5 w-3.5" />
                        </button>
                      </h4>
                    )}

                    <p className="text-xs text-slate-400 italic">Raw: "{fact.raw_text}"</p>
                  </div>

                  <div className="flex flex-wrap items-center gap-4 text-[11px] text-slate-500 pt-2 font-mono">
                    <span>Mapping: {fact.mapping_method}</span>
                    <span>Confidence: {(fact.mapping_confidence * 100).toFixed(0)}%</span>
                    <span>Page {fact.source_page} (Span {fact.start_char}-{fact.end_char})</span>
                  </div>
                </div>

                {/* Review status & actions */}
                <div className="flex flex-row md:flex-col items-center md:items-end justify-between border-t md:border-t-0 md:border-l border-slate-800 pt-3 md:pt-0 md:pl-5 space-y-2">
                  <span className={`text-[10px] font-bold uppercase px-2.5 py-1 rounded border ${
                    fact.review_status === 'approved' ? 'bg-emerald-950 text-emerald-300 border-emerald-500/40' :
                    fact.review_status === 'rejected' ? 'bg-rose-950 text-rose-300 border-rose-500/40' :
                    'bg-amber-950 text-amber-300 border-amber-500/40'
                  }`}>
                    {fact.review_status}
                  </span>

                  <div className="flex space-x-2">
                    <button
                      onClick={() => handleReviewAction(fact.id, 'approved')}
                      className="bg-emerald-950 hover:bg-emerald-900 text-emerald-300 border border-emerald-500/40 p-2 rounded-lg"
                      title="Approve Fact"
                    >
                      <CheckCircle className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleReviewAction(fact.id, 'rejected')}
                      className="bg-rose-950 hover:bg-rose-900 text-rose-300 border border-rose-500/40 p-2 rounded-lg"
                      title="Reject Fact"
                    >
                      <XCircle className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </PageWrapper>
  );
};
