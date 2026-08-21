import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { BASE_URL } from '../utils/apiClient';
import {
  Upload, FileText, CheckCircle, AlertTriangle, Eye, Sparkles, RefreshCw,
  Brain, Stethoscope, Pill, Info, X, ImageIcon, ClipboardList
} from 'lucide-react';
import { PatientPrescription } from '../types';

interface PatientPrescriptionPageProps {
  currentLanguage: string;
}

// Parse the structured clinical sections from Gemini Vision output
const SECTION_ICONS: Record<string, { icon: JSX.Element; color: string; bg: string; border: string }> = {
  'Doctor': { icon: <Stethoscope className="w-4 h-4" />, color: 'text-sky-300', bg: 'bg-sky-950/40', border: 'border-sky-700/40' },
  'Patient': { icon: <Info className="w-4 h-4" />, color: 'text-purple-300', bg: 'bg-purple-950/40', border: 'border-purple-700/40' },
  'Clinical': { icon: <ClipboardList className="w-4 h-4" />, color: 'text-amber-300', bg: 'bg-amber-950/40', border: 'border-amber-700/40' },
  'Prescribed': { icon: <Pill className="w-4 h-4" />, color: 'text-emerald-300', bg: 'bg-emerald-950/40', border: 'border-emerald-700/40' },
  'Advice': { icon: <CheckCircle className="w-4 h-4" />, color: 'text-cyan-300', bg: 'bg-cyan-950/40', border: 'border-cyan-700/40' },
};

function getSectionStyle(header: string) {
  for (const [key, style] of Object.entries(SECTION_ICONS)) {
    if (header.toLowerCase().includes(key.toLowerCase())) return style;
  }
  return { icon: <FileText className="w-4 h-4" />, color: 'text-slate-300', bg: 'bg-slate-800/60', border: 'border-slate-700/40' };
}

interface Section {
  header: string;
  lines: string[];
}

function parseStructuredOutput(text: string): Section[] {
  const sections: Section[] = [];
  let currentSection: Section | null = null;

  for (const rawLine of text.split('\n')) {
    const line = rawLine.trim();
    if (!line) continue;

    // Detect section headers (emoji + title pattern, markdown headers like ##, or clinical key words in English/translated languages)
    const isHeader =
      /^#+\s/.test(line) ||
      /^[👨‍⚕️👤🩺💊📝🏥📄⚕️🩺📋💡]/.test(line) ||
      /^(Doctor|Patient|Clinical|Prescribed|Advice|Rx|Medication|Vitals|Complaint|Instructions|மருத்துவர்|நோயாளி|மருந்துகள்|அறிவுரை|डॉक्टर|मरीज़|दवाइयां|सलाह)/i.test(line);

    if (isHeader) {
      if (currentSection) sections.push(currentSection);
      const cleanHeader = line.replace(/^#+\s*/, '');
      currentSection = { header: cleanHeader, lines: [] };
    } else {
      if (!currentSection) currentSection = { header: '📄 Prescription Details', lines: [] };
      currentSection.lines.push(line);
    }
  }
  if (currentSection) sections.push(currentSection);
  return sections;
}

function RxLine({ line }: { line: string }) {
  const isIllegible = line.toLowerCase().includes('[illegible');
  const isMedication = /^(T\.|Tab|Cap|Syp|S\.|Inj|Syr|Oint|Tab\.|I\.|C\.|\d+\)|\-)/i.test(line);

  if (isIllegible) {
    return (
      <div className="bg-amber-950/40 border border-amber-700/50 rounded-lg px-3 py-2 text-xs text-amber-300 flex items-start space-x-2 my-1">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
        <span>{line}</span>
      </div>
    );
  }
  if (isMedication) {
    return (
      <div className="flex items-start space-x-2 py-0.5">
        <span className="text-emerald-400 mt-0.5">•</span>
        <span className="text-sm text-slate-200 font-medium">{line}</span>
      </div>
    );
  }
  return <p className="text-sm text-slate-300 py-0.5 leading-relaxed">{line}</p>;
}

export const PatientPrescriptionPage: React.FC<PatientPrescriptionPageProps> = ({ currentLanguage }) => {
  const { user } = useAuth();
  const [prescription, setPrescription] = useState<PatientPrescription | null>(null);
  const [missedAlerts, setMissedAlerts] = useState<any[]>([]);
  const [weeklyMetricInput, setWeeklyMetricInput] = useState<string>('');
  const [submittingWeeklyMetric, setSubmittingWeeklyMetric] = useState<boolean>(false);
  const [weeklyFeedback, setWeeklyFeedback] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [translationError, setTranslationError] = useState<string | null>(null);
  const [translatedText, setTranslatedText] = useState<string>('');
  const [translating, setTranslating] = useState<boolean>(false);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [uploadStep, setUploadStep] = useState<string>('');
  const translationCache = useRef<Record<string, string>>({});

  const fileInputRefHeader = useRef<HTMLInputElement>(null);
  const fileInputRefDropzone = useRef<HTMLInputElement>(null);

  const fetchPrescription = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${BASE_URL}/api/v1/patient-portal/prescription`, {
        headers: {
          'X-User-Email': user?.email || 'patient@clinicaltrial.ai',
          'X-User-Role': user?.role || 'patient',
        },
      });
      const data = await res.json();
      if (data.success && data.data) {
        setPrescription(data.data);
        setTranslatedText(data.data.transcribedText);
      }
    } catch (err) {
      console.error('Fetch prescription error:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchMissedAlerts = async () => {
    try {
      const res = await fetch(`${BASE_URL}/api/v1/notifications`);
      const data = await res.json();
      if (data.success && Array.isArray(data.data)) {
        const missed = data.data.filter((n: any) => n.title && n.title.toLowerCase().includes('missed'));
        setMissedAlerts(missed);
      }
    } catch (err) {
      console.error('Fetch missed alerts error:', err);
    }
  };

  useEffect(() => {
    fetchPrescription();
    fetchMissedAlerts();
  }, []);

  // Reset cache when prescription changes (new upload)
  useEffect(() => {
    translationCache.current = {};
    if (prescription?.transcribedText) {
      translationCache.current['English'] = prescription.transcribedText;
      setTranslatedText(prescription.transcribedText);
      setTranslationError(null);
    }
  }, [prescription?.id]);

  // Translation effect: fires whenever language OR prescription changes
  useEffect(() => {
    if (!prescription?.transcribedText) return;

    // English: just restore original, no API call needed
    if (currentLanguage === 'English') {
      console.log('[TRANSLATION FRONTEND] Language is English. Restoring original transcribed text.');
      setTranslatedText(prescription.transcribedText);
      setTranslationError(null);
      return;
    }

    // If we have a cached result for this language, use it immediately
    if (translationCache.current[currentLanguage]) {
      console.log(`[TRANSLATION FRONTEND] Found cached translation for ${currentLanguage}:`, translationCache.current[currentLanguage]);
      setTranslatedText(translationCache.current[currentLanguage]);
      setTranslationError(null);
      return;
    }

    const translate = async () => {
      setTranslating(true);
      setTranslationError(null);
      console.log(`[TRANSLATION FRONTEND] Initiating API call to translate text to '${currentLanguage}'... Original text length:`, prescription.transcribedText.length);
      try {
        const res = await fetch(`${BASE_URL}/api/v1/patient-portal/translate`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-User-Email': user?.email || 'patient@clinicaltrial.ai',
            'X-User-Role': user?.role || 'patient',
          },
          body: JSON.stringify({
            text: prescription.transcribedText,
            targetLanguage: currentLanguage,
          }),
        });

        const data = await res.json();
        console.log('[TRANSLATION FRONTEND] Raw API Response:', data);

        if (data.success && data.data?.translatedText) {
          const translated = data.data.translatedText;
          console.log('[TRANSLATION FRONTEND] Processed Translated Text:', translated);
          if (translated && translated.length > 5) {
            translationCache.current[currentLanguage] = translated;
            setTranslatedText(translated);
          } else {
            console.warn('[TRANSLATION FRONTEND] Returned translation text was too short/empty.');
            setTranslationError(`Translation to ${currentLanguage} returned no content. Showing English original.`);
            setTranslatedText(prescription.transcribedText);
          }
        } else {
          console.error('[TRANSLATION FRONTEND] API returned unsuccessful response or missing translatedText field:', data);
          setTranslationError(`Translation to ${currentLanguage} failed. Showing English original.`);
          setTranslatedText(prescription.transcribedText);
        }
      } catch (err: any) {
        console.error('[TRANSLATION FRONTEND] Fetch exception error:', err);
        setTranslationError(`Translation error: ${err.message || 'Network issue'}. Showing English original.`);
        setTranslatedText(prescription.transcribedText);
      } finally {
        setTranslating(false);
      }
    };

    translate();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentLanguage, prescription?.id]);

  const handleFileUpload = async (file: File) => {
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    setPrescription(null);

    const steps = [
      'Uploading image to server...',
      'Running Gemini Vision AI — Clinical Handwriting Expert...',
      'Decoding doctor handwriting with medical shorthand knowledge...',
      'Structuring clinical sections & medications...',
      'Finalizing report...',
    ];

    let stepIdx = 0;
    setUploadStep(steps[stepIdx]);
    const stepInterval = setInterval(() => {
      stepIdx = Math.min(stepIdx + 1, steps.length - 1);
      setUploadStep(steps[stepIdx]);
    }, 2800);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${BASE_URL}/api/v1/patient-portal/upload-prescription`, {
        method: 'POST',
        headers: {
          'X-User-Email': user?.email || 'patient@clinicaltrial.ai',
          'X-User-Role': user?.role || 'patient',
        },
        body: formData,
      });
      const data = await res.json();
      if (data.success && data.data) {
        setPrescription(data.data);
        setTranslatedText(data.data.transcribedText);
      } else {
        setUploadError(data.detail || data.error || 'Upload failed. Please try again with a clearer image.');
      }
    } catch (err: any) {
      setUploadError(err.message || 'Network error during upload.');
    } finally {
      clearInterval(stepInterval);
      setUploading(false);
      setUploadStep('');
    }
  };

  const onFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) handleFileUpload(e.target.files[0]);
    e.target.value = '';
  };

  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); setDragActive(true); };
  const handleDragLeave = () => setDragActive(false);
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) handleFileUpload(e.dataTransfer.files[0]);
  };

  const parsedSections = translatedText ? parseStructuredOutput(translatedText) : [];

  return (
    <div className="space-y-6">
      {/* Hidden File Inputs */}
      <input type="file" ref={fileInputRefHeader} accept="image/*,.pdf,.jpg,.jpeg,.png,.webp,.jfif,.bmp,.heic" onChange={onFileInputChange} style={{ display: 'none' }} />
      <input type="file" ref={fileInputRefDropzone} accept="image/*,.pdf,.jpg,.jpeg,.png,.webp,.jfif,.bmp,.heic" onChange={onFileInputChange} style={{ display: 'none' }} />

      {/* Header */}
      <div className="ai-prescription-header bg-gradient-to-r from-slate-900 via-slate-900 to-slate-800 border border-slate-700/60 rounded-2xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold !text-white flex items-center space-x-2">
            <Brain className="w-7 h-7 text-emerald-400" />
            <span className="!text-white">AI Prescription Reader</span>
          </h1>
          <p className="text-xs !text-white opacity-90 mt-1">
            Decodes any doctor handwriting — including cursive scripts, abbreviations, and multilingual notes — using Gemini Vision AI with clinical medical knowledge.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {prescription && (
            <button
              onClick={() => { setPrescription(null); setTranslatedText(''); setUploadError(null); }}
              className="inline-flex items-center space-x-1.5 bg-slate-700 hover:bg-slate-600 !text-white text-xs font-medium px-4 py-2.5 rounded-xl transition-all"
            >
              <X className="w-3.5 h-3.5 !text-white" />
              <span className="!text-white">Clear & Upload New</span>
            </button>
          )}
          <button
            onClick={() => fileInputRefHeader.current?.click()}
            disabled={uploading}
            className="inline-flex items-center justify-center space-x-2 bg-emerald-600 hover:bg-emerald-500 !text-white font-semibold text-xs px-5 py-2.5 rounded-xl shadow-lg transition-all disabled:opacity-50"
          >
            {uploading ? <RefreshCw className="w-4 h-4 animate-spin !text-white" /> : <Upload className="w-4 h-4 !text-white" />}
            <span className="!text-white">{uploading ? 'Analyzing...' : 'Upload Prescription'}</span>
          </button>
        </div>
      </div>

      {/* Missed Weekly Progress Report Alert Banner */}
      {missedAlerts.length > 0 && (
        <div className="bg-amber-950/60 border border-amber-500 rounded-2xl p-5 shadow-xl space-y-2 text-amber-200">
          <div className="flex items-center space-x-2 text-amber-400 font-bold text-sm">
            <AlertTriangle className="w-5 h-5 flex-shrink-0 animate-bounce" />
            <span>URGENT ALERT: Missed Weekly Progress Report</span>
          </div>
          {missedAlerts.map((n: any) => (
            <p key={n.id} className="text-xs text-amber-100 leading-relaxed">
              {n.message}
            </p>
          ))}
          <div className="pt-2 text-xs font-mono text-cyan-300">
            Please inform your clinical research coordinator or submit your updated weekly metric to avoid trial status discontinuation.
          </div>
        </div>
      )}

      {/* Upload Error Banner */}
      {uploadError && (
        <div className="bg-red-950/60 border border-red-800/80 rounded-2xl p-4 flex items-start space-x-3 text-red-300 text-xs">
          <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Upload Error</p>
            <p className="mt-0.5 opacity-80">{uploadError}</p>
          </div>
        </div>
      )}

      {/* Translation Error Banner */}
      {translationError && (
        <div className="bg-amber-950/50 border border-amber-700/60 rounded-2xl p-3.5 flex items-start space-x-3 text-amber-300 text-xs">
          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Translation Notice</p>
            <p className="mt-0.5 opacity-80">{translationError}</p>
          </div>
          <button
            onClick={() => setTranslationError(null)}
            className="ml-auto text-amber-500 hover:text-amber-300 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Drag & Drop Upload Zone */}
      {!prescription && !loading && !uploading && (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-2xl p-14 text-center transition-all cursor-pointer ${
            dragActive ? 'border-emerald-500 bg-emerald-500/10' : 'border-slate-700 bg-slate-900/60 hover:border-slate-500 hover:bg-slate-900'
          }`}
          onClick={() => fileInputRefDropzone.current?.click()}
        >
          <div className="max-w-md mx-auto space-y-5">
            <div className="relative inline-block">
              <div className="p-5 bg-slate-800/80 rounded-2xl border border-slate-700 text-emerald-400">
                <ImageIcon className="w-12 h-12" />
              </div>
              <div className="absolute -bottom-1 -right-1 bg-emerald-500 rounded-full p-1">
                <Brain className="w-3.5 h-3.5 text-white" />
              </div>
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">Drop Your Prescription Here</h3>
              <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
                Handwritten notes, printed prescriptions, clinic reports — any image or PDF.<br />
                Our AI is trained on medical shorthand (C/o, K/c/o, BD, TDS, 1-0-1…) across multiple languages.
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2">
              {['JPG', 'PNG', 'WEBP', 'HEIC', 'PDF', 'JFIF', 'BMP'].map(fmt => (
                <span key={fmt} className="bg-slate-800 text-slate-400 text-[10px] font-mono px-2.5 py-1 rounded-md border border-slate-700">{fmt}</span>
              ))}
            </div>
            <button className="inline-flex items-center space-x-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm px-6 py-2.5 rounded-xl cursor-pointer shadow-lg transition-all">
              <Sparkles className="w-4 h-4" />
              <span>Choose File / Take Photo</span>
            </button>
          </div>
        </div>
      )}

      {/* Loading State */}
      {(loading || uploading) && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center space-y-5">
          <div className="relative inline-block">
            <div className="w-16 h-16 rounded-full border-4 border-slate-700 border-t-emerald-500 animate-spin mx-auto" />
            <Brain className="w-6 h-6 text-emerald-400 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-200">
              {uploading ? 'AI Clinical Handwriting Analysis in Progress' : 'Loading Prescription Records...'}
            </p>
            {uploadStep && (
              <p className="text-xs text-emerald-400 mt-2 animate-pulse">{uploadStep}</p>
            )}
            {uploading && (
              <p className="text-xs text-slate-500 mt-3 max-w-xs mx-auto">
                Gemini Vision AI is reading the handwriting using medical shorthand knowledge, dosage patterns, and drug name recognition.
              </p>
            )}
          </div>
          {/* Progress steps */}
          {uploading && (
            <div className="flex justify-center gap-1.5 mt-2">
              {[0,1,2,3,4].map(i => (
                <div key={i} className={`h-1.5 rounded-full transition-all duration-500 ${i <= [0,1,2,3,4].indexOf(uploadStep ? [
                  'Uploading image to server...',
                  'Running Gemini Vision AI — Clinical Handwriting Expert...',
                  'Decoding doctor handwriting with medical shorthand knowledge...',
                  'Structuring clinical sections & medications...',
                  'Finalizing report...',
                ].indexOf(uploadStep) : 0) ? 'bg-emerald-500 w-8' : 'bg-slate-700 w-4'}`} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Side-by-Side Result View */}
      {prescription && !loading && !uploading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">

          {/* LEFT: Original Image */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4 sticky top-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2 text-slate-200 font-bold text-sm">
                <Eye className="w-4 h-4 text-cyan-400" />
                <span>Original Document</span>
              </div>
              <span className="text-xs font-mono bg-slate-800 px-2.5 py-1 rounded-md text-slate-400 max-w-[140px] truncate">
                {prescription.fileName}
              </span>
            </div>

            <div className="bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-center min-h-[380px] max-h-[560px] overflow-auto p-2">
              {prescription.imageUrl ? (
                prescription.fileType === 'pdf' ? (
                  <iframe src={prescription.imageUrl} title="Prescription PDF" className="w-full h-[520px] rounded-lg border-0" />
                ) : (
                  <img
                    src={prescription.imageUrl}
                    alt="Uploaded Prescription"
                    className="max-h-[520px] max-w-full object-contain rounded-lg shadow-md"
                  />
                )
              ) : (
                <div className="text-xs text-slate-500 text-center">Preview unavailable</div>
              )}
            </div>

            <div className="flex items-center justify-between text-xs text-slate-500 pt-1">
              <span>Uploaded: {new Date(prescription.uploadedAt).toLocaleString()}</span>
              <span>{(prescription.fileSizeBytes / 1024).toFixed(1)} KB</span>
            </div>

            {/* OCR method badge */}
            <div className="flex items-center space-x-2 text-[11px] flex-wrap gap-2">
              <span className={`px-2.5 py-1 rounded-md font-medium border ${
                prescription.ocrMethod.includes('Gemini Vision')
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : 'bg-slate-800 text-slate-400 border-slate-700'
              }`}>
                {prescription.ocrMethod}
              </span>
              <span className="bg-slate-800 text-slate-400 border border-slate-700 px-2.5 py-1 rounded-md">
                Confidence: {(prescription.ocrConfidence * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          {/* RIGHT: Structured AI Transcription */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2 text-slate-200 font-bold text-sm">
                <Sparkles className="w-4 h-4 text-emerald-400" />
                <span>AI Clinical Transcription</span>
                {currentLanguage !== 'English' && (
                  <span className="text-[10px] bg-cyan-950 text-cyan-300 border border-cyan-800/60 px-2 py-0.5 rounded-full font-normal">
                    {currentLanguage}
                  </span>
                )}
              </div>
              <button
                onClick={() => fileInputRefHeader.current?.click()}
                className="text-[11px] flex items-center space-x-1 text-slate-400 hover:text-emerald-400 transition-colors"
              >
                <RefreshCw className="w-3 h-3" />
                <span>Re-scan</span>
              </button>
            </div>

            {translating && (
              <div className="flex items-center space-x-2 text-xs text-cyan-400 bg-cyan-950/40 p-2.5 rounded-lg border border-cyan-800/40">
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Translating into {currentLanguage}...</span>
              </div>
            )}

            {/* Structured Section Rendering */}
            <div className="space-y-3 max-h-[620px] overflow-y-auto pr-1 custom-scrollbar">
              {parsedSections.length > 0 ? (
                parsedSections.map((section, i) => {
                  const style = getSectionStyle(section.header);
                  return (
                    <div key={i} className={`rounded-xl border p-4 space-y-2 ${style.bg} ${style.border}`}>
                      <div className={`flex items-center space-x-2 font-semibold text-sm ${style.color}`}>
                        {style.icon}
                        <span>{section.header}</span>
                      </div>
                      <div className="space-y-0.5 pl-1">
                        {section.lines.map((line, j) => (
                          <RxLine key={j} line={line} />
                        ))}
                      </div>
                    </div>
                  );
                })
              ) : (
                // Fallback: plain text with line-by-line rendering
                <div className="bg-slate-950 rounded-xl p-5 border border-slate-800 text-sm text-slate-200 leading-relaxed space-y-1">
                  {translatedText.split('\n').map((line, idx) => (
                    <RxLine key={idx} line={line} />
                  ))}
                </div>
              )}
            </div>

            {prescription.hasIllegibleText && (
              <div className="bg-amber-950/40 border border-amber-800/40 rounded-xl p-3 text-xs text-amber-300 flex items-start space-x-2">
                <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                <span>
                  Some words in this prescription are marked as <strong>[illegible]</strong>. Please confirm these with your doctor or pharmacist.
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
