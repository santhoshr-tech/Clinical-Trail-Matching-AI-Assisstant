import React, { useEffect, useState } from 'react';
import { PageWrapper } from '../components/PageWrapper';
import { Search, Filter, Database, ExternalLink, Sparkles, CheckCircle2, ArrowRight, ShieldCheck, RefreshCw, MapPin, List } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { BASE_URL } from '../utils/apiClient';
import { TrialSiteMap } from '../components/TrialSiteMap';

export const TrialSearchPage: React.FC = () => {
  const [trials, setTrials] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchMode, setSearchMode] = useState<'lexical' | 'semantic'>('lexical');
  const [viewMode, setViewMode] = useState<'list' | 'map'>('list');

  // Filters State
  const [condition, setCondition] = useState<string>('');
  const [phase, setPhase] = useState<string>('');
  const [status, setStatus] = useState<string>('');
  const [location, setLocation] = useState<string>('');
  const [biomarker, setBiomarker] = useState<string>('');

  // Import State
  const [nctToImport, setNctToImport] = useState<string>('');
  const [importing, setImporting] = useState<boolean>(false);

  const { user } = useAuth();

  const fetchTrials = () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (searchQuery) params.append('query', searchQuery);
    if (condition) params.append('condition', condition);
    if (phase) params.append('phase', phase);
    if (status) params.append('recruitment_status', status);
    if (location) params.append('location', location);
    if (biomarker) params.append('biomarker', biomarker);
    params.append('search_mode', searchMode);

    fetch(`${BASE_URL}/api/v1/trials/search?${params.toString()}`, {
      headers: {
        'X-User-Email': user?.email || '',
        'X-User-Role': user?.role || '',
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success && Array.isArray(data.data)) {
          setTrials(data.data);
        } else {
          setError(data.error || 'Failed to fetch trial protocols');
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchTrials();
  }, [searchMode]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchTrials();
  };

  const handleImportTrial = (e: React.FormEvent) => {
    e.preventDefault();
    if (!nctToImport.trim()) return;

    setImporting(true);
    fetch(`${BASE_URL}/api/v1/trials/import/${encodeURIComponent(nctToImport.trim())}`, {
      method: 'POST',
      headers: {
        'X-User-Email': user?.email || '',
        'X-User-Role': user?.role || '',
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          setNctToImport('');
          fetchTrials();
          alert(`Successfully cached trial ${data.data.nctId}!`);
        } else {
          alert(`Import failed: ${data.error || 'Unknown error'}`);
        }
      })
      .catch((err) => alert(`Error importing trial: ${err.message}`))
      .finally(() => setImporting(false));
  };

  return (
    <PageWrapper
      title="ClinicalTrials.gov Protocol Search"
      subtitle="Lexical & placeholder semantic search, multi-factor ranking, protocol caching, and versioning."
      moduleName="modules/trials"
      icon={Search}
    >
      <div className="space-y-6">
        {/* Import Bar */}
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <Database className="w-5 h-5 text-cyan-400" />
            <div>
              <h3 className="text-xs font-bold text-slate-100">Import / Cache Protocol</h3>
              <p className="text-[11px] text-slate-400">Fetch live protocol criteria from ClinicalTrials.gov by NCT ID.</p>
            </div>
          </div>
          <form onSubmit={handleImportTrial} className="flex items-center space-x-2 w-full sm:w-auto">
            <input
              type="text"
              placeholder="e.g. NCT04500000"
              value={nctToImport}
              onChange={(e) => setNctToImport(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs font-mono text-cyan-300 w-36 focus:outline-none focus:border-cyan-500"
            />
            <button
              type="submit"
              disabled={importing}
              className="bg-cyan-600 hover:bg-cyan-500 text-white text-xs px-3 py-1.5 rounded-lg font-semibold transition-colors disabled:opacity-50"
            >
              {importing ? 'Importing...' : 'Cache Trial'}
            </button>
          </form>
        </div>

        {/* Search Mode Toggle & Filter Bar */}
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
            {/* Search Input */}
            <form onSubmit={handleSearchSubmit} className="flex items-center space-x-2 flex-1 max-w-xl">
              <div className="relative w-full">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search title, NCT ID, condition, or intervention..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>
              <button type="submit" className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-4 py-2 rounded-lg font-medium border border-slate-700">
                Search
              </button>
            </form>

            {/* View Mode Toggle (List View | Map View) & Search Mode */}
            <div className="flex items-center space-x-3">
              <div className="bg-slate-950 p-1 rounded-lg border border-slate-800 flex items-center space-x-1 text-xs">
                <button
                  onClick={() => setViewMode('list')}
                  className={`px-3 py-1.5 rounded-md font-semibold flex items-center space-x-1.5 transition-colors ${
                    viewMode === 'list' ? 'bg-cyan-600 text-white' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <List className="w-3.5 h-3.5" />
                  <span>List View</span>
                </button>

                <button
                  onClick={() => setViewMode('map')}
                  className={`px-3 py-1.5 rounded-md font-semibold flex items-center space-x-1.5 transition-colors ${
                    viewMode === 'map' ? 'bg-cyan-600 text-white' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <MapPin className="w-3.5 h-3.5" />
                  <span>Map View (Live GPS)</span>
                </button>
              </div>
            </div>
            
            {/* Mode Switcher */}
            <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 self-start md:self-auto">
              <button
                onClick={() => setSearchMode('lexical')}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  searchMode === 'lexical' ? 'bg-cyan-950 text-cyan-300 border border-cyan-800' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Lexical Exact
              </button>
              <button
                onClick={() => setSearchMode('semantic')}
                className={`px-3 py-1 rounded text-xs font-medium flex items-center space-x-1 transition-colors ${
                  searchMode === 'semantic' ? 'bg-purple-950 text-purple-300 border border-purple-800' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Sparkles className="w-3 h-3 text-purple-400" />
                <span>Semantic (Embedding Placeholder)</span>
              </button>
            </div>
          </div>

          {/* Filters Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 text-xs">
            <div>
              <label className="block text-[10px] text-slate-400 font-mono mb-1">Condition</label>
              <input
                type="text"
                placeholder="NSCLC, Lung Cancer"
                value={condition}
                onChange={(e) => setCondition(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded p-1.5 text-slate-200"
              />
            </div>
            <div>
              <label className="block text-[10px] text-slate-400 font-mono mb-1">Phase</label>
              <select
                value={phase}
                onChange={(e) => setPhase(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded p-1.5 text-slate-200"
              >
                <option value="">All Phases</option>
                <option value="Phase 1">Phase 1</option>
                <option value="Phase 2">Phase 2</option>
                <option value="Phase 3">Phase 3</option>
                <option value="Phase 4">Phase 4</option>
              </select>
            </div>
            <div>
              <label className="block text-[10px] text-slate-400 font-mono mb-1">Recruitment Status</label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded p-1.5 text-slate-200"
              >
                <option value="">All Statuses</option>
                <option value="RECRUITING">RECRUITING</option>
                <option value="ACTIVE_NOT_RECRUITING">ACTIVE_NOT_RECRUITING</option>
                <option value="COMPLETED">COMPLETED</option>
              </select>
            </div>
            <div>
              <label className="block text-[10px] text-slate-400 font-mono mb-1">Location Fit</label>
              <input
                type="text"
                placeholder="Site 01"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded p-1.5 text-slate-200"
              />
            </div>
            <div>
              <label className="block text-[10px] text-slate-400 font-mono mb-1">Biomarker Target</label>
              <input
                type="text"
                placeholder="EGFR, PD-L1"
                value={biomarker}
                onChange={(e) => setBiomarker(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded p-1.5 text-slate-200"
              />
            </div>
          </div>
        </div>

        {/* Results View: Map vs List */}
        {viewMode === 'map' ? (
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center space-x-2">
              <MapPin className="w-4 h-4 text-cyan-400" />
              <span>Nearby Trial Sites Map View</span>
            </h3>
            <TrialSiteMap embedded={true} />
          </div>
        ) : loading ? (
          <div className="text-center py-12 text-xs text-slate-400 animate-pulse">Searching and ranking clinical trial protocols...</div>
        ) : error ? (
          <div className="bg-red-950/50 border border-red-800 text-red-300 p-4 rounded-xl text-xs">{error}</div>
        ) : trials.length === 0 ? (
          <div className="bg-slate-900 border border-slate-800 p-8 rounded-xl text-center text-xs text-slate-400">
            No matching clinical trial protocols found for specified filters.
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
              <span>Showing {trials.length} Ranked Trials</span>
              <span className="hidden sm:inline">Search Engine: {searchMode === 'semantic' ? 'Semantic Vector Embedding' : 'Lexical BM25'}</span>
            </div>

            {trials.map((t) => (
              <div
                key={t.id}
                className="bg-slate-900 border border-slate-800 hover:border-cyan-500/60 rounded-xl p-4 sm:p-5 space-y-3 transition-all cursor-pointer group"
                onClick={() => (window.location.href = `/trials/${t.nctId}`)}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm font-bold text-cyan-400 group-hover:text-cyan-300 transition-colors">{t.nctId}</span>
                    <span className="bg-slate-800 text-slate-300 px-2 py-0.5 rounded text-[11px] font-mono">
                      {t.phase}
                    </span>
                    <span className="bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded text-[10px] font-mono">
                      {t.recruitmentStatus}
                    </span>
                    <span className="bg-slate-950 text-slate-400 px-2 py-0.5 rounded text-[10px] font-mono">
                      v{t.version}
                    </span>
                  </div>

                  {/* Multi-Factor Ranking Score Badge */}
                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] text-slate-400 font-mono">Rank Score:</span>
                    <span className="bg-gradient-to-r from-cyan-950 to-blue-950 text-cyan-300 border border-cyan-800 px-2.5 py-0.5 rounded text-xs font-mono font-bold">
                      {t.rankingScore.toFixed(1)} / 100
                    </span>
                  </div>
                </div>

                <div className="space-y-1">
                  <h3 className="text-sm font-bold text-slate-100">{t.title}</h3>
                  <p className="text-xs text-slate-400 line-clamp-2">{t.briefSummary}</p>
                </div>

                {/* Tags */}
                <div className="flex flex-wrap gap-2 text-[11px]">
                  <span className="bg-slate-950 text-slate-300 px-2 py-1 rounded border border-slate-800">
                    Conditions: <strong className="text-cyan-300">{t.conditions}</strong>
                  </span>
                  <span className="bg-slate-950 text-slate-300 px-2 py-1 rounded border border-slate-800">
                    Biomarkers: <strong className="text-purple-300">{t.biomarkers || 'None specified'}</strong>
                  </span>
                  <span className="bg-slate-950 text-slate-300 px-2 py-1 rounded border border-slate-800">
                    Locations: <strong className="text-emerald-300">{t.locations}</strong>
                  </span>
                </div>

                {/* Footer Link & Actions */}
                <div className="pt-2 border-t border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs" onClick={(e) => e.stopPropagation()}>
                  <a
                    href={t.sourceUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-slate-400 hover:text-cyan-400 flex items-center space-x-1 text-[11px]"
                  >
                    <span>View on ClinicalTrials.gov</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>

                  <div className="flex items-center space-x-3 w-full sm:w-auto justify-between sm:justify-start">
                    <Link
                      to={`/trials/${t.nctId}/versions`}
                      className="text-slate-400 hover:text-cyan-300 text-[11px] font-mono"
                    >
                      Version Log
                    </Link>
                    <Link
                      to={`/trials/${t.nctId}`}
                      className="bg-cyan-950/60 hover:bg-cyan-900 text-cyan-300 border border-cyan-800 px-3 py-1.5 rounded-md text-[11px] font-medium flex items-center space-x-1 min-h-[36px]"
                    >
                      <span>Protocol Details &amp; Match</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </PageWrapper>
  );
};

