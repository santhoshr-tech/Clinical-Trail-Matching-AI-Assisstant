import React, { useState } from 'react';
import { Lock, ShieldCheck, UserCheck } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, user } = useAuth();
  
  const [selectedRole, setSelectedRole] = useState<UserRole>('research_coordinator');
  const [email, setEmail] = useState<string>('coordinator@clinicaltrial.ai');
  const [loading, setLoading] = useState<boolean>(false);

  const roleEmails: Record<UserRole, string> = {
    admin: 'admin@clinicaltrial.ai',
    research_coordinator: 'coordinator@clinicaltrial.ai',
    investigator: 'investigator@clinicaltrial.ai',
    reviewer: 'reviewer@clinicaltrial.ai',
    viewer: 'viewer@clinicaltrial.ai',
    patient: 'patient@clinicaltrial.ai',
  };

  const handleRoleChange = (role: UserRole) => {
    setSelectedRole(role);
    setEmail(roleEmails[role]);
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    await login(email, selectedRole);
    setLoading(false);
    const defaultTarget = selectedRole === 'patient' ? '/patient-portal/prescription' : '/';
    const from = (location.state as any)?.from?.pathname;
    const target = (from && from !== '/login') ? from : defaultTarget;
    navigate(target, { replace: true });
  };

  return (
    <div className="min-h-[80vh] flex flex-col items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 max-w-md w-full shadow-2xl space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 rounded-xl bg-cyan-500/10 text-cyan-400 mb-2 border border-cyan-500/20">
            <ShieldCheck className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold text-white">Clinical Research Portal</h1>
          <p className="text-xs text-slate-400">
            Supabase Auth & RBAC Security Foundation (Phase 2)
          </p>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Select Role Context</label>
            <select
              value={selectedRole}
              onChange={(e) => handleRoleChange(e.target.value as UserRole)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="patient">Patient (Restricted Portal)</option>
              <option value="research_coordinator">Research Coordinator (CRC)</option>
              <option value="investigator">Principal Investigator (PI)</option>
              <option value="reviewer">Reviewer</option>
              <option value="admin">System Admin</option>
              <option value="viewer">Read-Only Viewer</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Synthetic Identity Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center space-x-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold py-2.5 px-4 rounded-lg transition-all shadow-lg shadow-cyan-950 disabled:opacity-50"
          >
            <Lock className="w-4 h-4" />
            <span>{loading ? 'Authenticating...' : 'Sign In & Log Session'}</span>
          </button>
        </form>

        {user && (
          <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs text-slate-300 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <UserCheck className="w-4 h-4 text-emerald-400" />
              <span>Active Session: <strong>{user.role}</strong></span>
            </div>
            <span className="text-cyan-400 font-mono">{user.email}</span>
          </div>
        )}

        <div className="bg-amber-950/40 border border-amber-800/40 rounded-lg p-3 text-xs text-amber-300">
          <strong>Security Note:</strong> All authentication logins create immutable record entries in the audit trail.
        </div>
      </div>
    </div>
  );
};
