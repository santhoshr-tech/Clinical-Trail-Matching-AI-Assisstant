import React from 'react';
import { LucideIcon, ChevronRight } from 'lucide-react';

interface PageWrapperProps {
  title: string;
  subtitle: string;
  moduleName: string;
  icon: LucideIcon;
  children?: React.ReactNode;
}

export const PageWrapper: React.FC<PageWrapperProps> = ({
  title,
  subtitle,
  moduleName,
  icon: Icon,
  children,
}) => {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      
      {/* SaaS Hero Header Container */}
      <div className="bg-white rounded-2xl p-5 sm:p-6 border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        
        <div className="flex items-start space-x-4">
          <div className="p-3 bg-sky-50 text-sky-600 rounded-xl border border-sky-100 shrink-0 mt-0.5 shadow-2xs">
            <Icon className="w-6 h-6" />
          </div>

          <div className="space-y-1">
            {/* Breadcrumb navigation */}
            <div className="flex items-center space-x-1.5 text-xs text-slate-500 font-medium">
              <span>Dashboard</span>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-sky-600 font-semibold">{title}</span>
            </div>

            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
              {title}
            </h1>
            
            <p className="text-xs sm:text-sm text-slate-600 max-w-2xl leading-relaxed">
              {subtitle}
            </p>
          </div>
        </div>

        {/* System Status Operational Badge */}
        <div className="flex items-center space-x-2 text-xs bg-slate-50 border border-slate-200 px-3.5 py-2 rounded-xl text-slate-700 font-medium shrink-0 self-start md:self-auto">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
          </span>
          <span className="font-semibold text-slate-800">System Status:</span>
          <span className="text-emerald-700 font-bold">Operational</span>
        </div>

      </div>

      {children ? (
        children
      ) : (
        <div className="bg-white border border-slate-200 rounded-2xl p-8 sm:p-12 text-center space-y-4 shadow-xs">
          <div className="inline-flex p-3 bg-sky-50 text-sky-600 rounded-2xl border border-sky-100 mb-1">
            <Icon className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-bold text-slate-900">{title} Workspace</h3>
          <p className="text-xs sm:text-sm text-slate-600 max-w-md mx-auto leading-relaxed">
            This operational module is fully configured and ready for clinical data streams.
          </p>
          <div className="pt-2">
            <span className="inline-block text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 px-3.5 py-1.5 rounded-full">
              System Active & Synchronized
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
