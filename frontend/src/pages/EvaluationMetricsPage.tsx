import React, { useEffect, useState } from 'react';
import { PageWrapper } from '../components/PageWrapper';
import { ShieldCheck, Play, Activity } from 'lucide-react';
import { ApiResponse } from '../types';

export const EvaluationMetricsPage: React.FC = () => {
  const [evalStatus, setEvalStatus] = useState<string>('Ready to benchmark');

  return (
    <PageWrapper
      title="System Evaluation Metrics Dashboard"
      subtitle="Repeatable evaluation module reporting empirical metrics against gold-standard synthetic datasets."
      moduleName="modules/evaluation"
      icon={ShieldCheck}
    >
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <h3 className="text-lg font-semibold text-white">Gold Standard Synthetic Benchmark Suite</h3>
            <p className="text-xs text-slate-400">
              Evaluates criterion classification, negation, temporal reasoning, missing data, and evidence grounding.
            </p>
          </div>
          <button
            onClick={() => setEvalStatus('Benchmark harness ready (Phase 1 mock trigger)')}
            className="flex items-center space-x-2 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold py-2 px-4 rounded-lg transition-colors shadow-md"
          >
            <Play className="w-4 h-4" />
            <span>Run Benchmark Harness</span>
          </button>
        </div>

        <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 flex items-center justify-between text-xs">
          <div className="flex items-center space-x-2 text-cyan-400">
            <Activity className="w-4 h-4" />
            <span>Harness Status: <strong>{evalStatus}</strong></span>
          </div>
          <span className="text-slate-400">Dataset Version: <code>v1.0.0-synthetic-gold</code></span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
          {[
            { metric: 'Criterion Classification', target: '≥ 93%', status: 'Target Set (Pending Run)' },
            { metric: 'Eligibility Extraction', target: '≥ 92%', status: 'Target Set (Pending Run)' },
            { metric: 'Medical Normalization', target: '≥ 90%', status: 'Target Set (Pending Run)' },
            { metric: 'Negation Detection', target: '≥ 98%', status: 'Target Set (Pending Run)' },
            { metric: 'Temporal Validation', target: '≥ 95%', status: 'Target Set (Pending Run)' },
            { metric: 'Missing-Data Detection', target: '≥ 95%', status: 'Target Set (Pending Run)' },
            { metric: 'Conflict Detection', target: '≥ 90%', status: 'Target Set (Pending Run)' },
            { metric: 'Evidence Grounding', target: '≥ 93%', status: 'Target Set (Pending Run)' },
            { metric: 'Overall Matching', target: '≥ 93%', status: 'Target Set (Pending Run)' },
            { metric: 'Decision Traceability', target: '100%', status: '100% Mandatory Check' },
          ].map((item) => (
            <div key={item.metric} className="bg-white border border-slate-200 p-4 rounded-xl space-y-1.5 shadow-2xs">
              <div className="flex justify-between font-bold text-[#243247] text-sm">
                <span>{item.metric}</span>
                <span className="text-sky-600 font-mono font-extrabold">{item.target}</span>
              </div>
              <p className="text-xs text-[#64748B] font-medium">{item.status}</p>
            </div>
          ))}
        </div>
      </div>
    </PageWrapper>
  );
};
