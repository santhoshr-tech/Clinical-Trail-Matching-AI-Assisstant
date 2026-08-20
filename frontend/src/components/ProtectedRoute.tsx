import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: UserRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { isAuthenticated, user, hasRole } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Block PATIENT role from accessing coordinator/researcher routes
  const isPatientRoute = location.pathname.startsWith('/patient-portal');
  if (user?.role === 'patient' && !isPatientRoute) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center space-y-4 max-w-lg mx-auto my-12 shadow-2xl">
        <h3 className="text-xl font-bold text-emerald-400">Patient Portal Restricted Area</h3>
        <p className="text-xs text-slate-300">
          Your patient account does not have access to clinical research coordinator pages.
        </p>
        <div className="pt-2">
          <a
            href="/patient-portal/prescription"
            className="inline-flex items-center space-x-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-all shadow-lg"
          >
            <span>Go to My Patient Portal</span>
          </a>
        </div>
      </div>
    );
  }

  if (allowedRoles && allowedRoles.length > 0 && !hasRole(allowedRoles)) {
    return (
      <div className="bg-red-950/60 border border-red-800 rounded-xl p-8 text-center space-y-4 max-w-lg mx-auto my-12">
        <h3 className="text-xl font-bold text-red-300">Access Restricted (RBAC)</h3>
        <p className="text-xs text-slate-300">
          Your active role (<strong className="text-red-400 font-mono uppercase">{user?.role}</strong>) does not have authorization to view this module.
        </p>
        <p className="text-xs text-slate-400">
          Required Roles: <code className="text-cyan-300 font-mono">{allowedRoles.join(', ')}</code>
        </p>
      </div>
    );
  }

  return <>{children}</>;
};
