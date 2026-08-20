import React, { useState, useEffect } from 'react';
import { MapPin, Navigation, Compass, AlertCircle, CheckCircle, Search, Sliders, ArrowRight, Save, Building } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

interface TrialSiteMapProps {
  embedded?: boolean;
}

export const TrialSiteMap: React.FC<TrialSiteMapProps> = ({ embedded = false }) => {
  const [userLat, setUserLat] = useState<number>(13.0827); // Default Chennai
  const [userLon, setUserLon] = useState<number>(80.2707);
  const [locationGranted, setLocationGranted] = useState<boolean | null>(null);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [radiusKm, setRadiusKm] = useState<number>(50);
  const [manualCity, setManualCity] = useState<string>('');
  const [sites, setSites] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedSite, setSelectedSite] = useState<any | null>(null);
  const [savedSuccess, setSavedSuccess] = useState<boolean>(false);
  const { user } = useAuth();

  // Trigger native browser Geolocation on initial load
  const requestLiveLocation = () => {
    setLocationError(null);
    if (!navigator.geolocation) {
      setLocationGranted(false);
      setLocationError('Browser Geolocation is not supported in your environment. Please search manually.');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setUserLat(position.coords.latitude);
        setUserLon(position.coords.longitude);
        setLocationGranted(true);
        setLocationError(null);
      },
      (err) => {
        setLocationGranted(false);
        setLocationError('Location access denied - please enter a location manually to find nearby trial sites.');
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  useEffect(() => {
    requestLiveLocation();
  }, []);

  const fetchNearbySites = () => {
    setLoading(true);
    fetch(`/api/v1/location/nearby-sites?lat=${userLat}&lon=${userLon}&radius_km=${radiusKm}`)
      .then((res) => res.json())
      .then((data) => {
        if (data.success && Array.isArray(data.data)) {
          setSites(data.data);
          if (data.data.length > 0) setSelectedSite(data.data[0]);
        }
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchNearbySites();
  }, [userLat, userLon, radiusKm]);

  const handleManualSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualCity.trim()) return;

    // Simple city geocoding mapper for manual fallback entries
    const cityLower = manualCity.trim().toLowerCase();
    const cityCoords: Record<string, [number, number]> = {
      chennai: [13.0827, 80.2707],
      salem: [11.6643, 78.1460],
      coimbatore: [11.0168, 76.9558],
      mumbai: [19.0760, 72.8777],
      delhi: [28.6139, 77.2090],
      bengaluru: [12.9716, 77.5946],
      bangalore: [12.9716, 77.5946],
      boston: [42.3601, -71.0589],
      'new york': [40.7128, -74.0060],
    };

    if (cityCoords[cityLower]) {
      setUserLat(cityCoords[cityLower][0]);
      setUserLon(cityCoords[cityLower][1]);
      setLocationGranted(true);
      setLocationError(null);
    } else {
      // Default to Chennai coordinates if unknown city string entered
      setUserLat(13.0827);
      setUserLon(80.2707);
    }
  };

  const handleSaveLocationToProfile = () => {
    const locText = manualCity || `Lat: ${userLat.toFixed(4)}, Lon: ${userLon.toFixed(4)}`;
    fetch('/api/v1/location/save-patient-location', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ patient_id: user?.email || 'patient-01', address_text: locText }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          setSavedSuccess(true);
          setTimeout(() => setSavedSuccess(false), 3000);
        }
      })
      .catch((err) => console.error(err));
  };

  return (
    <div className={`space-y-6 ${embedded ? '' : 'max-w-6xl mx-auto'}`}>
      {/* Geolocation Status Banner */}
      <div
        className={`p-4 rounded-xl border text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
          locationGranted === true
            ? 'bg-emerald-950/40 border-emerald-500/50 text-emerald-300'
            : locationGranted === false
            ? 'bg-amber-950/40 border-amber-500/50 text-amber-300'
            : 'bg-slate-900 border-slate-800 text-slate-300'
        }`}
      >
        <div className="flex items-center space-x-3">
          <Navigation className="w-5 h-5 flex-shrink-0 text-cyan-400 animate-pulse" />
          <div>
            <p className="font-bold text-sm">
              {locationGranted === true
                ? 'Showing trial sites near your current live location'
                : 'Location Access Notice'}
            </p>
            <p className="text-[11px] opacity-80 mt-0.5">
              {locationGranted === true
                ? `Center: Lat ${userLat.toFixed(4)}, Lon ${userLon.toFixed(4)} — Live Browser GPS active`
                : locationError || 'Requesting live location permission from browser...'}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {locationGranted === false && (
            <button
              onClick={requestLiveLocation}
              className="bg-amber-800 hover:bg-amber-700 text-white px-3 py-1.5 rounded-lg text-xs font-semibold"
            >
              Retry Live GPS
            </button>
          )}

          {locationGranted === true && (
            <button
              onClick={handleSaveLocationToProfile}
              className="bg-slate-800 hover:bg-slate-700 text-cyan-300 px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-700 flex items-center space-x-1"
            >
              <Save className="w-3.5 h-3.5" />
              <span>{savedSuccess ? 'Saved to Profile!' : 'Save as My Location'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Manual Search & Radius Controls */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
          {/* Manual City Input */}
          <form onSubmit={handleManualSearch} className="md:col-span-2 flex items-center space-x-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="text"
                placeholder="Search city manually (e.g. Chennai, Salem, Coimbatore, Mumbai, Delhi)..."
                value={manualCity}
                onChange={(e) => setManualCity(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
              />
            </div>
            <button
              type="submit"
              className="bg-cyan-600 hover:bg-cyan-500 text-white text-xs px-4 py-2 rounded-lg font-semibold shadow transition-colors"
            >
              Search
            </button>
          </form>

          {/* Radius Slider */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs font-mono text-slate-300">
              <span>Filter Radius:</span>
              <span className="text-cyan-400 font-bold">{radiusKm} km</span>
            </div>
            <input
              type="range"
              min="10"
              max="200"
              step="10"
              value={radiusKm}
              onChange={(e) => setRadiusKm(parseInt(e.target.value))}
              className="w-full accent-cyan-500 cursor-pointer"
            />
          </div>
        </div>
      </div>

      {/* Map Interactive Visual & Sites List Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Visual Map Canvas / Radar View */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-bold text-white flex items-center space-x-2">
              <Compass className="w-4 h-4 text-cyan-400" />
              <span>Interactive Site Radar ({sites.length} Sites Nearby)</span>
            </h4>
            <span className="text-xs font-mono text-slate-400">Radius: {radiusKm}km</span>
          </div>

          {/* Canvas Map Radar Simulation */}
          <div className="bg-slate-950 border border-slate-800 rounded-xl h-80 relative flex items-center justify-center overflow-hidden">
            {/* Background Grid Lines */}
            <div className="absolute inset-0 opacity-20 bg-[radial-gradient(#06b6d4_1px,transparent_1px)] [background-size:16px_16px]" />

            {/* Radar Center User Pulse */}
            <div className="absolute w-6 h-6 bg-cyan-500/20 border-2 border-cyan-400 rounded-full flex items-center justify-center animate-ping" />
            <div className="absolute w-3 h-3 bg-cyan-400 rounded-full shadow-lg shadow-cyan-500/50 flex items-center justify-center z-10" />

            {/* Plot Trial Site Pins around center relative to distance/bearing */}
            {sites.map((site, index) => {
              // Distribute pins visually around center based on index & distance
              const angle = (index * (360 / Math.max(sites.length, 1))) * (Math.PI / 180);
              const maxDist = radiusKm || 50;
              const normalizedDist = Math.min(site.distance_km / maxDist, 0.85); // % of radius
              const radiusPixels = 120 * normalizedDist;

              const x = Math.cos(angle) * radiusPixels;
              const y = Math.sin(angle) * radiusPixels;

              const isSelected = selectedSite?.site_id === site.site_id;

              return (
                <button
                  key={site.site_id}
                  onClick={() => setSelectedSite(site)}
                  style={{ transform: `translate(${x}px, ${y}px)` }}
                  className={`absolute p-2 rounded-full border shadow-xl transition-transform hover:scale-125 z-20 ${
                    isSelected
                      ? 'bg-emerald-500 border-white text-slate-950 ring-4 ring-emerald-500/30'
                      : 'bg-slate-900 border-cyan-500 text-cyan-400 hover:bg-cyan-950'
                  }`}
                  title={`${site.site_name} (${site.distance_km} km away)`}
                >
                  <MapPin className="w-4 h-4" />
                </button>
              );
            })}
          </div>

          <p className="text-[11px] text-slate-400 text-center">
            Click any pin on the radar map to view trial protocol details, facility location, and distance.
          </p>
        </div>

        {/* Selected Trial Site Info Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
          <h4 className="text-sm font-bold text-white flex items-center space-x-2">
            <Building className="w-4 h-4 text-cyan-400" />
            <span>Site Details & Distance</span>
          </h4>

          {selectedSite ? (
            <div className="space-y-4">
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
                <div>
                  <span className="text-[10px] font-mono uppercase bg-cyan-950 text-cyan-300 border border-cyan-800 px-2 py-0.5 rounded font-bold">
                    {selectedSite.distance_km} km away
                  </span>
                  <h5 className="text-sm font-bold text-white mt-2">{selectedSite.site_name}</h5>
                  <p className="text-xs text-slate-400">{selectedSite.facility_name || 'Clinical Research Wing'}</p>
                </div>

                <div className="text-xs text-slate-300 space-y-1">
                  <div>City: <span className="font-semibold text-slate-200">{selectedSite.city}, {selectedSite.state || selectedSite.country}</span></div>
                  <div>Status: <span className="font-bold text-emerald-400 uppercase">{selectedSite.recruitment_status}</span></div>
                  <div>Trial: <span className="font-mono text-cyan-300 font-bold">{selectedSite.nct_id}</span></div>
                  <p className="text-[11px] text-slate-400 italic line-clamp-2">{selectedSite.trial_title}</p>
                </div>
              </div>

              <Link
                to={`/trials/${selectedSite.nct_id}`}
                className="w-full bg-cyan-600 hover:bg-cyan-500 text-white text-xs px-4 py-2.5 rounded-lg font-semibold flex items-center justify-center space-x-2 transition-colors shadow-lg"
              >
                <span>View Full Protocol Details</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          ) : (
            <div className="bg-slate-950 border border-slate-800 rounded-xl p-6 text-center text-xs text-slate-400">
              No trial site selected. Click a pin or search a city.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
