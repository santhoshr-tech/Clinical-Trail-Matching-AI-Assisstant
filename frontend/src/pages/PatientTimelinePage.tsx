import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { PageWrapper } from '../components/PageWrapper';
import { Clock, Calendar, CheckCircle2, ArrowLeft, Activity, Tag, FileText } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { BASE_URL } from '../utils/apiClient';

export const PatientTimelinePage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [timeline, setTimeline] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuth();

  useEffect(() => {
    fetch(`${BASE_URL}/api/v1/patients/${id}/timeline`, {
      headers: {
        'X-User-Email': user?.email || '',
        'X-User-Role': user?.role || '',
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success && Array.isArray(data.data)) {
          setTimeline(data.data);
        } else {
          setError(data.error || 'Failed to load timeline events');
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id, user]);

  const getEventBadge = (type: string) => {
    switch (type.toUpperCase()) {
      case 'DIAGNOSIS':
        return <span className="bg-red-950/80 text-red-300 border border-red-800 px-2 py-0.5 rounded text-[10px] font-mono">DIAGNOSIS</span>;
      case 'LAB_RESULT':
      case 'LAB':
        return <span className="bg-cyan-950/80 text-cyan-300 border border-cyan-800 px-2 py-0.5 rounded text-[10px] font-mono">LAB RESULT</span>;
      case 'BIOMARKER':
      case 'BIOMARKER_TEST':
        return <span className="bg-purple-950/80 text-purple-300 border border-purple-800 px-2 py-0.5 rounded text-[10px] font-mono">BIOMARKER</span>;
      case 'MEDICATION':
      case 'MEDICATION_STARTED':
        return <span className="bg-emerald-950/80 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded text-[10px] font-mono">MEDICATION</span>;
      default:
        return <span className="bg-slate-800 text-slate-300 border border-slate-700 px-2 py-0.5 rounded text-[10px] font-mono">{type}</span>;
    }
  };

  return (
    <PageWrapper
      title="Clinical Longitudinal Timeline"
      subtitle="Sequential chronology of diagnoses, lab specimens, biomarker assays, and medical events."
      moduleName="modules/patients"
      icon={Clock}
    >
      <div className="space-y-6 max-w-4xl mx-auto">
        <div className="flex items-center justify-between">
          <Link
            to={`/patients/${id}`}
            className="inline-flex items-center space-x-1.5 text-xs text-slate-400 hover:text-cyan-400 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Patient Profile</span>
          </Link>
          <div className="text-xs text-slate-400 font-mono">
            {timeline.length} Chronological Events
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12 text-xs text-slate-400 animate-pulse">Loading longitudinal timeline...</div>
        ) : error ? (
          <div className="bg-red-950/50 border border-red-800 text-red-300 p-4 rounded-xl text-xs">{error}</div>
        ) : timeline.length === 0 ? (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-xs text-slate-400 space-y-2">
            <Clock className="w-8 h-8 mx-auto text-slate-600 mb-2" />
            <p>No longitudinal events registered for this patient profile yet.</p>
          </div>
        ) : (
          <div className="relative border-l-2 border-slate-800 ml-4 space-y-6 py-2">
            {timeline.map((evt, idx) => (
              <div key={evt.id || idx} className="relative pl-6">
                <div className="absolute -left-[9px] top-1.5 w-4 h-4 rounded-full bg-slate-900 border-2 border-cyan-400"></div>
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2 hover:border-cyan-500/30 transition-all">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      {getEventBadge(evt.eventType)}
                      <span className="font-mono text-xs text-slate-400 flex items-center space-x-1">
                        <Calendar className="w-3 h-3 text-slate-500" />
                        <span>{evt.eventDate}</span>
                      </span>
                    </div>
                    <span className="text-[10px] text-emerald-400 bg-emerald-950 px-2 py-0.5 rounded font-mono border border-emerald-800">
                      {evt.verificationStatus || 'verified'}
                    </span>
                  </div>

                  <p className="text-sm font-semibold text-slate-100">{evt.summary}</p>

                  {evt.rawSnippet && (
                    <div className="bg-slate-950 p-2.5 rounded border border-slate-800 text-xs font-mono text-slate-300 flex items-start space-x-2 mt-2">
                      <FileText className="w-4 h-4 text-slate-500 flex-shrink-0 mt-0.5" />
                      <span>{evt.rawSnippet}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </PageWrapper>
  );
};
