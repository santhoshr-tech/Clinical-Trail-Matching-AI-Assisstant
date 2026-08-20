import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Activity,
  Users,
  FileText,
  Search,
  CheckSquare,
  BarChart3,
  Sliders,
  Bell,
  ShieldCheck,
  UserCheck,
  LogOut,
  Menu,
  X,
  User,
} from 'lucide-react';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const { user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { path: '/', label: 'Dashboard', icon: Activity },
    { path: '/patients', label: 'Patients', icon: Users },
    { path: '/documents/upload', label: 'Upload Doc', icon: FileText },
    { path: '/trials/search', label: 'Trials', icon: Search },
    { path: '/coordinator-queue', label: 'CRC Queue', icon: CheckSquare },
    { path: '/investigator-review', label: 'Investigator', icon: UserCheck },
    { path: '/disagreement-analytics', label: 'Analytics', icon: BarChart3 },
    { path: '/evaluation-metrics', label: 'Evaluation', icon: ShieldCheck },
    { path: '/settings', label: 'Settings', icon: Sliders },
  ];

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-slate-200 shadow-sm saas-navbar">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Left Branding */}
        <div className="flex items-center space-x-6">
          <Link to="/" className="flex items-center space-x-2.5 group">
            <div className="p-2 bg-sky-50 text-sky-600 rounded-xl border border-sky-100 group-hover:bg-sky-100 transition-colors">
              <Activity className="w-5 h-5" />
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-base text-slate-900 tracking-tight leading-none">
                Clinical Trial <span className="text-sky-600">AI</span>
              </span>
              <span className="text-[10px] text-slate-500 font-medium tracking-wider uppercase mt-0.5">
                Research Operations
              </span>
            </div>
          </Link>

          {/* Desktop Center Navigation */}
          <nav className="hidden lg:flex items-center space-x-1">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive = location.pathname === link.path;
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-xs font-bold transition-all ${
                    isActive
                      ? 'bg-sky-50 text-sky-700 font-bold border-b-2 border-sky-600 shadow-2xs'
                      : 'text-[#172033] hover:text-[#0891b2] hover:bg-slate-50'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-sky-600' : 'text-[#4B5B73]'}`} />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right Section: Notifications, Profile, Actions */}
        <div className="flex items-center space-x-3">
          <Link
            to="/notifications"
            className="p-2 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg relative transition-colors"
            title="Notifications"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-sky-500 rounded-full ring-2 ring-white"></span>
          </Link>

          {user ? (
            <div className="flex items-center space-x-2">
              <div className="hidden sm:flex items-center space-x-2 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-full text-xs text-slate-700">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                <span className="font-bold text-slate-800 tracking-wide uppercase text-[11px]">
                  {user.role === 'research_coordinator' ? 'RESEARCH COORDINATOR' : user.role.replace('_', ' ')}
                </span>
              </div>
              <button
                onClick={() => logout()}
                className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                title="Logout"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="text-xs bg-sky-600 hover:bg-sky-700 text-white font-semibold px-4 py-2 rounded-lg transition-colors shadow-sm"
            >
              Sign In
            </Link>
          )}

          {/* Mobile Menu Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden p-2 rounded-lg hover:bg-slate-100 text-slate-600 transition-colors"
            title="Toggle Menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Navigation Dropdown */}
      {mobileMenuOpen && (
        <div className="lg:hidden bg-white border-b border-slate-200 px-4 py-3 space-y-1">
          {navLinks.map((link) => {
            const Icon = link.icon;
            const isActive = location.pathname === link.path;
            return (
              <Link
                key={link.path}
                to={link.path}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                  isActive
                    ? 'bg-sky-50 text-sky-700 font-semibold border-l-4 border-sky-600'
                    : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                <Icon className="w-4 h-4 text-slate-400" />
                <span>{link.label}</span>
              </Link>
            );
          })}
        </div>
      )}
    </header>
  );
};
