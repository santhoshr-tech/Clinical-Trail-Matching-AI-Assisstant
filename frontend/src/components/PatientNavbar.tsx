import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { BASE_URL } from '../utils/apiClient';
import {
  FileText,
  Pill,
  Apple,
  Globe,
  ShoppingBag,
  LogOut,
  Search,
  ChevronDown,
  Menu,
  X,
} from 'lucide-react';
import { PatientPurchaseModal } from './PatientPurchaseModal';

const MAJOR_LANGUAGES = [
  'English', 'Hindi', 'Tamil', 'Telugu', 'Kannada', 'Malayalam', 'Bengali',
  'Marathi', 'Gujarati', 'Punjabi', 'Spanish', 'French', 'Arabic', 'Chinese',
  'German', 'Japanese', 'Russian', 'Portuguese', 'Korean', 'Italian', 'Turkish',
  'Vietnamese', 'Persian', 'Swahili', 'Urdu',
];

interface PatientNavbarProps {
  currentLanguage: string;
  onLanguageChange: (lang: string) => void;
}

export const PatientNavbar: React.FC<PatientNavbarProps> = ({
  currentLanguage,
  onLanguageChange,
}) => {
  const location = useLocation();
  const { user, logout } = useAuth();
  const [langDropdownOpen, setLangDropdownOpen] = useState(false);
  const [searchFilter, setSearchFilter] = useState('');
  const [purchaseModalOpen, setPurchaseModalOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const filteredLanguages = MAJOR_LANGUAGES.filter((l) =>
    l.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const handleSelectLanguage = async (lang: string) => {
    onLanguageChange(lang);
    setLangDropdownOpen(false);
    try {
      await fetch(`${BASE_URL}/api/v1/patient-portal/preferences`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Email': user?.email || '',
          'X-User-Role': user?.role || 'patient',
        },
        body: JSON.stringify({ preferredLanguage: lang }),
      });
    } catch (e) {
      console.error('Save language preference error:', e);
    }
  };

  const navLinks = [
    { path: '/patient-portal/prescription', label: 'My Prescription', icon: FileText },
    { path: '/patient-portal/medicines', label: 'Medicine Info', icon: Pill },
    { path: '/patient-portal/food', label: 'Food Guide', icon: Apple },
  ];

  return (
    <>
      <header className="sticky top-0 z-50 bg-white border-b border-slate-200 shadow-sm saas-navbar">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-6">
            <Link
              to="/patient-portal/prescription"
              className="flex items-center space-x-2 text-emerald-600 font-bold text-lg"
            >
              <div className="p-2 bg-emerald-50 text-emerald-600 rounded-xl border border-emerald-100">
                <Pill className="w-5 h-5" />
              </div>
              <span className="font-bold text-slate-900 tracking-tight">
                Patient <span className="text-emerald-600">Portal</span>
              </span>
            </Link>

            <nav className="hidden md:flex items-center space-x-1">
              {navLinks.map((link) => {
                const Icon = link.icon;
                const isActive = location.pathname === link.path;
                return (
                  <Link
                    key={link.path}
                    to={link.path}
                    className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                      isActive
                        ? 'bg-emerald-50 text-emerald-700 font-semibold border-b-2 border-emerald-600'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                    }`}
                  >
                    <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-600' : 'text-slate-400'}`} />
                    <span>{link.label}</span>
                  </Link>
                );
              })}
            </nav>
          </div>

          <div className="flex items-center space-x-2 sm:space-x-3">
            {/* Purchase Button */}
            <button
              onClick={() => setPurchaseModalOpen(true)}
              className="flex items-center space-x-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs px-3 py-2 sm:px-3.5 rounded-lg shadow-xs transition-colors min-h-[40px]"
            >
              <ShoppingBag className="w-4 h-4" />
              <span className="hidden sm:inline">Purchase</span>
            </button>

            {/* Language Selector */}
            <div className="relative">
              <button
                onClick={() => setLangDropdownOpen(!langDropdownOpen)}
                className="flex items-center space-x-1 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 px-2.5 py-2 sm:px-3 rounded-lg text-xs font-medium transition-colors min-h-[40px]"
              >
                <Globe className="w-4 h-4 text-emerald-600" />
                <span className="max-w-[70px] sm:max-w-none truncate">{currentLanguage}</span>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
              </button>

              {langDropdownOpen && (
                <div className="absolute right-0 mt-2 w-64 bg-white border border-slate-200 rounded-xl shadow-lg p-2 z-50 space-y-2">
                  <div className="relative">
                    <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                    <input
                      type="text"
                      value={searchFilter}
                      onChange={(e) => setSearchFilter(e.target.value)}
                      placeholder="Search languages..."
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-800 focus:outline-none focus:border-emerald-500"
                    />
                  </div>

                  <div className="max-h-48 overflow-y-auto space-y-1 scrollbar-thin">
                    {filteredLanguages.map((lang) => (
                      <button
                        key={lang}
                        onClick={() => handleSelectLanguage(lang)}
                        className={`w-full text-left px-3 py-1.5 rounded-md text-xs transition-colors flex items-center justify-between ${
                          currentLanguage === lang
                            ? 'bg-emerald-50 text-emerald-700 font-semibold'
                            : 'text-slate-600 hover:bg-slate-50'
                        }`}
                      >
                        <span>{lang}</span>
                        {currentLanguage === lang && (
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Logout */}
            {user && (
              <button
                onClick={() => logout()}
                className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors min-h-[40px] min-w-[40px] flex items-center justify-center"
                title="Logout"
              >
                <LogOut className="w-4 h-4" />
              </button>
            )}

            {/* Mobile Menu Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg hover:bg-slate-100 text-slate-600 transition-colors min-h-[40px] min-w-[40px] flex items-center justify-center"
              title="Toggle Menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Dropdown Drawer */}
        {mobileMenuOpen && (
          <div className="md:hidden bg-white border-b border-slate-200 px-4 py-3 space-y-1">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive = location.pathname === link.path;
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center space-x-2.5 px-3 py-2.5 rounded-lg text-xs font-medium transition-colors ${
                    isActive
                      ? 'bg-emerald-50 text-emerald-700 font-semibold border-l-4 border-emerald-600'
                      : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <Icon className="w-4 h-4 text-emerald-600" />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </div>
        )}
      </header>

      <PatientPurchaseModal
        isOpen={purchaseModalOpen}
        onClose={() => setPurchaseModalOpen(false)}
      />
    </>
  );
};
