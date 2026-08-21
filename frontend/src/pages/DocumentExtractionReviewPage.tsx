import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { PageWrapper } from '../components/PageWrapper';
import { FileText, CheckCircle2, AlertTriangle, ShieldCheck, RefreshCw, Clock, Cpu, Tag, History } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { BASE_URL } from '../utils/apiClient';

export const DocumentExtractionReviewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [doc, setDoc] = useState<any>(null);
  const [selectedFactIds, setSelectedFactIds] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [approving, setApproving] = useState<boolean>(false);
  const [retrying, setRetrying] = useState<boolean>(false);
  const navigate = useNavigate();
  const { user } = useAuth();

  const fetchDoc = () => {
    fetch(`${BASE_URL}/api/v1/documents/${id}`, {
      headers: {
        'X-User-Email': user?.email || '',
        'X-User-Role': user?.role || '',
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success && data.data) {
          setDoc(data.data);
          const unverified = data.data.facts.map((f: any) => f.id);
          setSelectedFactIds(unverified);
        } else {
          setError(data.error || 'Failed to load document review.');
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchDoc();
  }, [id, user]);

  const handleRetryExtraction = () => {
    setRetrying(true);
    fetch(`${BASE_URL}/api/v1/documents/${id}/retry`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Email': user?.email || '',
        'X-User-Role': user?.role || '',
      },
      body: JSON.stringify({ forceOcr: true }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          alert('Re-triggered document page parsing with Tesseract OCR fallback.');
          fetchDoc();
        } else {
          alert(`Retry failed: ${data.error || 'Unknown error'}`);
        }
      })
      .catch((err) => alert(`Error: ${err.message}`))
      .finally(() => setRetrying(false));
  };

  const toggleFactSelection = (factId: string) => {
    if (selectedFactIds.includes(factId)) {
      setSelectedFactIds(selectedFactIds.filter((fid) => fid !== factId));
    } else {
      setSelectedFactIds([...selectedFactIds, factId]);
    }
  };

  const handleApproveSelected = () => {
    if (selectedFactIds.length === 0) {
      alert('Please select at least one clinical fact to approve.');
      return;
    }

    setApproving(true);
    fetch(`${BASE_URL}/api/v1/documents/${id}/approve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Email': user?.email || '',
        'X-User-Role': user?.role || '',
      },
      body: JSON.stringify({ approvedFactIds: selectedFactIds }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          alert(`Approved ${data.data.approvedCount} clinical facts! Transferred to canonical patient record.`);
          navigate(`/patients/${doc.patientId}`);
        } else {
          alert(`Approval failed: ${data.error || 'Unknown error'}`);
        }
      })
      .catch((err) => alert(`Error approving facts: ${err.message}`))
      .finally(() => setApproving(false));
  };

  if (loading) return <div className="text-center py-12 text-xs text-slate-400 animate-pulse">Loading document & extracting pages...</div>;
  if (error || !doc) return <div className="bg-red-950/50 border border-red-800 text-red-300 p-4 rounded-xl text-xs">{error || 'Document missing'}</div>;

  return (
    <PageWrapper
      title={`Document Evidence: ${doc.fileName}`}
      subtitle="Dual-pane document preview, page-level evidence text spans, extraction status, version history, and approval."
      moduleName="modules/documents"
      icon={FileText}
    >
      <div className="space-y-6">
        {/* Document Header Bar */}
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <FileText className="w-7 h-7 text-cyan-400 flex-shrink-0" />
            <div>
              <div className="flex items-center space-x-2 flex-wrap gap-1">
                <h2 className="text-sm font-bold text-slate-100">{doc.fileName}</h2>
                <span className="bg-slate-800 text-slate-200 px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold">
                  {doc.documentCategory.replace('_', ' ')}
                </span>
                <span className="bg-cyan-950 text-cyan-300 border border-cyan-800 px-2 py-0.5 rounded text-[10px] font-mono">
                  v{doc.version}
                </span>
                <span className="bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded text-[10px] font-mono uppercase">
                  {doc.processingStatus}
                </span>
                {doc.ocrApplied && (
                  <span className="bg-purple-950 text-purple-300 border border-purple-800 px-2 py-0.5 rounded text-[10px] font-mono flex items-center space-x-1">
                    <Cpu className="w-3 h-3 text-purple-400" />
                    <span>OCR Fallback</span>
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-400 font-mono mt-1">
                Doc ID: {doc.id} • Size: {(doc.fileSizeBytes / 1024).toFixed(1)} KB • Pages: {doc.pageCount} • Storage: {doc.storagePath}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handleRetryExtraction}
              disabled={retrying}
              className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3 py-2 rounded-lg border border-slate-700 flex items-center space-x-1.5 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-purple-400 ${retrying ? 'animate-spin' : ''}`} />
              <span>{retrying ? 'Retrying...' : 'Retry OCR Extraction'}</span>
            </button>

            <button
              onClick={handleApproveSelected}
              disabled={approving || selectedFactIds.length === 0}
              className="bg-cyan-600 hover:bg-cyan-500 text-white text-xs px-4 py-2 rounded-lg font-semibold flex items-center space-x-1.5 transition-colors disabled:opacity-50"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>{approving ? 'Saving...' : `Approve ${selectedFactIds.length} Selected Facts`}</span>
            </button>
          </div>
        </div>

        {/* Dual-Pane View */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Pane: Page-Level Evidence Spans Preview */}
          <div className="lg:col-span-6 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <h3 className="text-xs font-bold text-slate-200 uppercase font-mono tracking-wider">Document Page Preview & Spans</h3>
              <span className="text-[10px] text-cyan-400 font-mono">PyMuPDF Text Engine</span>
            </div>

            <div className="space-y-4 max-h-[600px] overflow-y-auto pr-1">
              {doc.pages.map((p: any) => (
                <div key={p.id || p.pageNumber} className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-800/80 pb-1">
                    <span className="text-[11px] font-mono font-bold text-cyan-400">
                      Page {p.pageNumber} ({p.charCount} chars)
                    </span>
                    {p.ocrApplied && (
                      <span className="text-[10px] text-purple-400 font-mono">Scanned (OCR)</span>
                    )}
                  </div>

                  <p className="text-xs font-mono text-slate-300 leading-relaxed whitespace-pre-wrap">
                    {p.pageText}
                  </p>

                  {p.sourceSpans && p.sourceSpans.length > 0 && (
                    <div className="pt-2 border-t border-slate-900">
                      <span className="text-[10px] text-slate-500 font-mono block mb-1">Source Character Spans Bounding Boxes:</span>
                      <div className="flex flex-wrap gap-1">
                        {p.sourceSpans.map((sp: any, sIdx: number) => (
                          <span key={sIdx} className="bg-slate-900 text-slate-400 border border-slate-800 px-1.5 py-0.5 rounded text-[9px] font-mono">
                            "{sp.text}"
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Right Pane: Extracted Facts & Document Versioning */}
          <div className="lg:col-span-6 space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <div className="flex items-center space-x-2">
                  <h3 className="text-xs font-bold text-slate-200 uppercase font-mono tracking-wider">Extracted Clinical Entities ({doc.facts.length})</h3>
                  <span className="bg-cyan-950 text-cyan-300 border border-cyan-800 px-2 py-0.5 rounded text-[10px] font-mono">
                    Raw vs Normalized
                  </span>
                </div>

                <button
                  onClick={() => setSelectedFactIds(selectedFactIds.length === doc.facts.length ? [] : doc.facts.map((f: any) => f.id))}
                  className="text-[11px] text-cyan-400 hover:underline font-mono"
                >
                  {selectedFactIds.length === doc.facts.length ? 'Deselect All' : 'Select All'}
                </button>
              </div>

              <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
                {doc.facts.map((fact: any) => {
                  const isSelected = selectedFactIds.includes(fact.id);
                  return (
                    <div
                      key={fact.id}
                      onClick={() => toggleFactSelection(fact.id)}
                      className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                        isSelected
                          ? 'bg-slate-950 border-cyan-500/80'
                          : 'bg-slate-950/60 border-slate-800 opacity-70 hover:opacity-100'
                      }`}
                    >
                      <div className="flex items-start space-x-3">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => {}}
                          className="mt-1 w-4 h-4 accent-cyan-500 rounded cursor-pointer"
                        />

                        <div className="space-y-1 w-full">
                          <div className="flex items-center justify-between">
                            <span className="bg-slate-800 text-slate-200 px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold">
                              {fact.factType}
                            </span>
                            <span className="text-[10px] text-slate-400 font-mono">
                              Page {fact.pageNumber}
                            </span>
                          </div>

                          <p className="text-xs font-bold text-cyan-300 font-mono">
                            {fact.normalizedValue}
                          </p>

                          <p className="text-[11px] text-slate-400 font-mono">
                            Raw Text: <span className="text-slate-300 italic">"{fact.rawValue}"</span>
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Document Versioning Timeline */}
            {doc.versions && doc.versions.length > 0 && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
                <div className="flex items-center space-x-2 border-b border-slate-800 pb-2">
                  <History className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-xs font-bold text-slate-200 uppercase font-mono tracking-wider">Document Re-upload Version History</h3>
                </div>

                <div className="space-y-2 text-xs font-mono">
                  {doc.versions.map((v: any) => (
                    <div key={v.id} className="bg-slate-950 p-2.5 rounded border border-slate-800 flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <span className="bg-cyan-950 text-cyan-300 px-2 py-0.5 rounded text-[10px] font-bold">v{v.versionNumber}</span>
                        <span className="text-slate-300">{v.fileName}</span>
                      </div>
                      <span className="text-[10px] text-slate-500">{v.uploadedAt}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </PageWrapper>
  );
};


