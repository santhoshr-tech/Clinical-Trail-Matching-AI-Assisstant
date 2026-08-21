import React, { useEffect, useState } from 'react';
import { PageWrapper } from '../components/PageWrapper';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, ArrowRight, ShieldCheck, Cpu, Target, UserCheck, XCircle } from 'lucide-react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { BASE_URL } from '../utils/apiClient';

export const DocumentUploadPage: React.FC = () => {
  const [patients, setPatients] = useState<any[]>([]);
  const [trials, setTrials] = useState<any[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string>('');
  const [selectedTrialId, setSelectedTrialId] = useState<string>('');
  const [documentCategory, setDocumentCategory] = useState<string>('pathology_report');
  const [file, setFile] = useState<File | null>(null);
  const [applyOcr, setApplyOcr] = useState<boolean>(false);
  const [baselineMetricValue, setBaselineMetricValue] = useState<string>('');
  const [uploading, setUploading] = useState<boolean>(false);
  const [screening, setScreening] = useState<boolean>(false);
  const [screeningResult, setScreeningResult] = useState<any | null>(null);
  const [enrollmentResult, setEnrollmentResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { user } = useAuth();

  useEffect(() => {
    // Fetch synthetic patients
    fetch(`${BASE_URL}/api/v1/patients`, {
      headers: {
        'X-User-Email': user?.email || '',
        'X-User-Role': user?.role || '',
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success && Array.isArray(data.data)) {
          setPatients(data.data);
          if (data.data.length > 0) setSelectedPatientId(data.data[0].id);
        }
      })
      .catch((err) => console.error(err));

    // Fetch clinical trials for disease-agnostic selection
    fetch(`${BASE_URL}/api/v1/trials/search`, {
      headers: {
        'X-User-Email': user?.email || '',
        'X-User-Role': user?.role || '',
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success && Array.isArray(data.data)) {
          setTrials(data.data);
        }
      })
      .catch((err) => console.error(err));
  }, [user]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    setScreeningResult(null);
    setEnrollmentResult(null);
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      const ext = selected.name.substring(selected.name.lastIndexOf('.')).toLowerCase();
      if (!['.pdf', '.txt'].includes(ext)) {
        setError(`Unsupported file extension '${ext}'. Only synthetic .pdf and .txt files are allowed.`);
        setFile(null);
        return;
      }
      if (selected.size > 10 * 1024 * 1024) {
        setError(`File size exceeds maximum limit of 10MB.`);
        setFile(null);
        return;
      }
      setFile(selected);
    }
  };

  const handleUploadSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPatientId) {
      setError('Please select a target patient profile.');
      return;
    }
    if (!file) {
      setError('Please choose a valid medical record document (.pdf or .txt) to upload.');
      return;
    }

    setUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('patient_id', selectedPatientId);
    formData.append('document_category', documentCategory);
    formData.append('apply_ocr', applyOcr ? 'true' : 'false');

    fetch(`${BASE_URL}/api/v1/documents/upload`, {
      method: 'POST',
      headers: {
        'X-User-Email': user?.email || '',
        'X-User-Role': user?.role || '',
      },
      body: formData,
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success && data.data) {
          // If a specific trial was selected, run eligibility screening immediately
          if (selectedTrialId) {
            runTrialScreening(selectedPatientId, selectedTrialId, data.data.documentId);
          } else {
            navigate(`/documents/${data.data.documentId}/review`);
          }
        } else {
          setError(data.error || 'Failed to upload document.');
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setUploading(false));
  };

  const runTrialScreening = (patientId: string, trialId: string, docId?: string) => {
    setScreening(true);
    setScreeningResult(null);
    setEnrollmentResult(null);

    fetch(`${BASE_URL}/api/v1/enrollment/screen`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Email': user?.email || '',
        'X-User-Role': user?.role || '',
      },
      body: JSON.stringify({ patient_id: patientId, trial_id: trialId }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success && data.data) {
          setScreeningResult({ ...data.data, documentId: docId });
        } else {
          setError(data.error || 'Trial screening failed.');
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setScreening(false));
  };

  const handleConfirmEnrollment = () => {
    if (!screeningResult || !selectedPatientId || !selectedTrialId) return;

    fetch(`${BASE_URL}/api/v1/enrollment/confirm`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Email': user?.email || '',
        'X-User-Role': user?.role || '',
      },
      body: JSON.stringify({
        patient_id: selectedPatientId,
        trial_id: selectedTrialId,
        baseline_report_id: screeningResult.documentId,
        baseline_metric_value: baselineMetricValue ? parseFloat(baselineMetricValue) : 7.8,
      }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success && data.data) {
          setEnrollmentResult(data.data);
        } else {
          setError(data.error || 'Enrollment confirmation failed.');
        }
      })
      .catch((err) => setError(err.message));
  };

  return (
    <PageWrapper
      title="Document Upload & Trial Eligibility Screening"
      subtitle="Upload synthetic clinical documents, screen against selected trials, generate unique enrollment IDs, and establish baseline treatment metrics."
      moduleName="modules/documents"
      icon={UploadCloud}
    >
      <div className="max-w-3xl mx-auto space-y-6">
        <form onSubmit={handleUploadSubmit} className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
          {error && (
            <div className="bg-red-950/60 border border-red-800 text-red-300 p-4 rounded-lg text-xs flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Patient Selection & Document Category Row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="block text-xs font-mono text-slate-300">Target Synthetic Patient *</label>
              <select
                value={selectedPatientId}
                onChange={(e) => setSelectedPatientId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
              >
                {patients.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.mrnSynthetic} — {p.primaryDiagnosis} ({p.gender}, Age {p.age})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="block text-xs font-mono text-slate-300">Document Type / Category *</label>
              <select
                value={documentCategory}
                onChange={(e) => setDocumentCategory(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono capitalize"
              >
                <option value="pathology_report">Pathology Report</option>
                <option value="lab_report">Lab Report</option>
                <option value="radiology_report">Radiology Report</option>
                <option value="clinical_note">Clinical Note</option>
                <option value="patient_report">Patient Report</option>
                <option value="protocol">Protocol Document</option>
              </select>
            </div>
          </div>

          {/* Target Trial Selection for Disease-Agnostic Screening */}
          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-3">
            <div className="flex items-center space-x-2 text-cyan-400">
              <Target className="w-4 h-4" />
              <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Trial Eligibility Screening & Enrollment (Disease-Agnostic)
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Select a clinical trial to automatically evaluate the patient report against trial criteria upon upload.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-mono text-slate-400 mb-1">Target Trial / Protocol</label>
                <select
                  value={selectedTrialId}
                  onChange={(e) => setSelectedTrialId(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="">-- Optional: Select Trial to Screen & Enroll --</option>
                  {trials.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.nctId} - {t.title} ({t.conditions || 'General'})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-slate-400 mb-1">Baseline Metric Value (Optional)</label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="e.g. 7.8 (HbA1c / tumor size)"
                  value={baselineMetricValue}
                  onChange={(e) => setBaselineMetricValue(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>
          </div>

          {/* Drag and Drop Zone */}
          <div className="border-2 border-dashed border-slate-800 hover:border-cyan-500/50 bg-slate-950 rounded-xl p-8 text-center space-y-3 transition-colors">
            <UploadCloud className="w-10 h-10 text-cyan-400 mx-auto" />
            <div className="space-y-1">
              <p className="text-xs font-semibold text-slate-200">Click to browse or drop medical report file here</p>
              <p className="text-[11px] text-slate-400">Strictly validates file extension (.pdf, .txt) and file size (&le; 10MB)</p>
            </div>
            <input
              type="file"
              accept=".pdf,.txt"
              onChange={handleFileChange}
              className="hidden"
              id="file-upload-input"
            />
            <label
              htmlFor="file-upload-input"
              className="inline-block bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-4 py-2 rounded-lg font-medium cursor-pointer border border-slate-700 transition-colors"
            >
              Choose File (.pdf, .txt)
            </label>
            {file && (
              <div className="pt-2 flex items-center justify-center space-x-2 text-xs font-mono text-cyan-300">
                <FileText className="w-4 h-4 text-cyan-400" />
                <span>Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
              </div>
            )}
          </div>

          {/* Processing Options */}
          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Cpu className="w-5 h-5 text-purple-400" />
              <div>
                <span className="text-xs font-bold text-slate-200 block">Force Tesseract OCR Fallback</span>
                <span className="text-[11px] text-slate-400 block">Trigger OCR processing for scanned PDF images or low-character documents.</span>
              </div>
            </div>
            <input
              type="checkbox"
              checked={applyOcr}
              onChange={(e) => setApplyOcr(e.target.checked)}
              className="w-4 h-4 accent-cyan-500 rounded cursor-pointer"
            />
          </div>

          {/* Submit */}
          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={uploading || screening}
              className="bg-cyan-600 hover:bg-cyan-500 text-white text-xs px-6 py-2.5 rounded-lg font-semibold flex items-center space-x-2 transition-colors disabled:opacity-50"
            >
              <span>
                {uploading
                  ? 'Uploading & Extracting Evidence...'
                  : screening
                  ? 'Screening Against Trial Criteria...'
                  : 'Upload & Screen Eligibility'}
              </span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </form>

        {/* Screening Result Alert Banner */}
        {screeningResult && (
          <div
            className={`border rounded-xl p-6 space-y-4 ${
              screeningResult.is_eligible
                ? 'bg-emerald-950/40 border-emerald-500/50 text-emerald-200'
                : 'bg-amber-950/40 border-amber-500/50 text-amber-200'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-3">
                {screeningResult.is_eligible ? (
                  <CheckCircle2 className="w-6 h-6 text-emerald-400 flex-shrink-0" />
                ) : (
                  <XCircle className="w-6 h-6 text-amber-400 flex-shrink-0" />
                )}
                <div>
                  <h4 className="text-sm font-bold">
                    {screeningResult.is_eligible
                      ? `Eligible - Patient can be enrolled in [${screeningResult.trial_title}]`
                      : `Not Eligible for [${screeningResult.trial_title}] - Please add/select next patient`}
                  </h4>
                  <p className="text-xs text-slate-300 mt-1">
                    Matching Score: {(screeningResult.match_score * 100).toFixed(0)}% — Overall Status: {screeningResult.overall_status}
                  </p>
                </div>
              </div>

              {screeningResult.is_eligible && !enrollmentResult && (
                <button
                  type="button"
                  onClick={handleConfirmEnrollment}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs px-4 py-2 rounded-lg font-semibold flex items-center space-x-2 transition-colors shadow-lg"
                >
                  <UserCheck className="w-4 h-4" />
                  <span>Enroll Patient & Generate Unique ID</span>
                </button>
              )}
            </div>

            {/* Confirmed Enrollment Result */}
            {enrollmentResult && (
              <div className="bg-slate-900 border border-emerald-500 p-4 rounded-lg text-xs space-y-2 mt-2">
                <div className="flex items-center space-x-2 text-emerald-400 font-bold">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Trial Enrollment Confirmed!</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-slate-300">
                  <div>Unique Enrollment ID: <span className="font-mono text-cyan-300 font-bold">{enrollmentResult.enrollment_id}</span></div>
                  <div>Enrolled Status: <span className="uppercase text-emerald-400 font-bold">{enrollmentResult.status}</span></div>
                  <div>Enrolled Date: <span className="font-mono">{enrollmentResult.enrolled_date}</span></div>
                  <div>Next Expected Report Due: <span className="font-mono text-amber-400">{enrollmentResult.next_expected_report_date}</span></div>
                </div>
                <div className="pt-2 flex justify-end">
                  <Link
                    to="/dashboard"
                    className="text-cyan-400 hover:underline text-xs flex items-center space-x-1"
                  >
                    <span>View in My Trial Cohort Dashboard</span>
                    <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </PageWrapper>
  );
};
