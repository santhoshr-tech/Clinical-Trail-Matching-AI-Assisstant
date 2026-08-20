import React from 'react';
import { ShieldCheck, UserCheck, Activity } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-white border-t border-slate-200 text-slate-500 py-3 px-6 text-xs mt-auto">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2.5">
        
        <div className="flex items-center space-x-2">
          <Activity className="w-3.5 h-3.5 text-sky-600" />
          <span className="font-bold text-slate-800 tracking-tight">Clinical Trial AI</span>
          <span className="text-slate-400">•</span>
          <span className="text-slate-500 font-medium">Enterprise Research Operations v2.0</span>
        </div>

        <div className="flex items-center space-x-4 text-[11px] font-medium text-slate-600">
          <div className="flex items-center space-x-1.5 text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-100">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>Synthetic Data Protection Active</span>
          </div>

          <span className="text-slate-300 hidden sm:inline">•</span>

          <div className="flex items-center space-x-1.5 text-amber-700 bg-amber-50 px-2.5 py-0.5 rounded-full border border-amber-100">
            <UserCheck className="w-3.5 h-3.5 text-amber-600" />
            <span>Qualified Human Review Required</span>
          </div>
        </div>

      </div>
    </footer>
  );
};
