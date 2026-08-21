import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { BASE_URL } from '../utils/apiClient';
import { Apple, AlertTriangle, ShieldCheck, CheckCircle2, XCircle, Zap, RefreshCw } from 'lucide-react';
import { FoodGuidanceItem } from '../types';

interface PatientFoodPageProps {
  currentLanguage: string;
}

export const PatientFoodPage: React.FC<PatientFoodPageProps> = ({ currentLanguage }) => {
  const { user } = useAuth();
  const [items, setItems] = useState<FoodGuidanceItem[]>([]);
  const [disclaimer, setDisclaimer] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);

  const fetchFoodGuidance = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${BASE_URL}/api/v1/patient-portal/food-guidance`, {
        headers: {
          'X-User-Email': user?.email || '',
          'X-User-Role': user?.role || 'patient',
        },
      });
      const data = await res.json();
      if (data.success && data.data) {
        setItems(data.data.items || []);
        setDisclaimer(data.data.disclaimer || '');
      }
    } catch (err) {
      console.error('Fetch food guidance error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFoodGuidance();
  }, []);

  const foodsToEat = items.filter((i) => i.category === 'foods_to_eat');
  const foodsToAvoid = items.filter((i) => i.category === 'foods_to_avoid');
  const drugInteractions = items.filter((i) => i.category === 'drug_food_interaction');

  return (
    <div className="space-y-6">
      {/* Title Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center space-x-2">
            <Apple className="w-7 h-7 text-emerald-400" />
            <span>Food & Dietary Guidance</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            General dietary advice and food-drug interaction warnings sourced from MedlinePlus & FDA interaction databases.
          </p>
        </div>
      </div>

      {/* MANDATORY DIETARY DISCLAIMER */}
      <div className="bg-amber-950/60 border border-amber-800/80 rounded-2xl p-4 flex items-start space-x-3 text-amber-200 shadow-lg">
        <AlertTriangle className="w-6 h-6 text-amber-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-1 text-xs">
          <strong className="text-amber-300 font-bold uppercase tracking-wider block">
            Mandatory Dietary Disclaimer:
          </strong>
          <p className="leading-relaxed">
            {disclaimer ||
              'This is general dietary guidance. Please consult your doctor or a registered dietitian for advice specific to your condition.'}
          </p>
        </div>
      </div>

      {loading && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-emerald-400 animate-spin mx-auto" />
          <p className="text-sm font-semibold text-slate-200">Loading Dietary & Food Interaction Data...</p>
        </div>
      )}

      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Foods to Eat */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
            <div className="flex items-center space-x-2 text-emerald-400 font-bold text-base border-b border-slate-800 pb-3">
              <CheckCircle2 className="w-5 h-5" />
              <span>Recommended Foods</span>
            </div>

            <div className="space-y-3">
              {foodsToEat.map((item, idx) => (
                <div key={idx} className="bg-slate-950 p-4 rounded-xl border border-emerald-950/80 space-y-2">
                  <h4 className="text-sm font-bold text-emerald-300">{item.title}</h4>
                  <p className="text-xs text-slate-300 leading-relaxed">{item.details}</p>
                  <div className="text-[10px] text-slate-400 font-mono pt-1 border-t border-slate-800">
                    Source: {item.sourceCitation}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Foods to Avoid */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
            <div className="flex items-center space-x-2 text-red-400 font-bold text-base border-b border-slate-800 pb-3">
              <XCircle className="w-5 h-5" />
              <span>Foods & Beverages to Avoid</span>
            </div>

            <div className="space-y-3">
              {foodsToAvoid.map((item, idx) => (
                <div key={idx} className="bg-slate-950 p-4 rounded-xl border border-red-950/80 space-y-2">
                  <h4 className="text-sm font-bold text-red-300">{item.title}</h4>
                  <p className="text-xs text-slate-300 leading-relaxed">{item.details}</p>
                  <div className="text-[10px] text-slate-400 font-mono pt-1 border-t border-slate-800">
                    Source: {item.sourceCitation}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Drug-Food Interactions */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
            <div className="flex items-center space-x-2 text-amber-400 font-bold text-base border-b border-slate-800 pb-3">
              <Zap className="w-5 h-5" />
              <span>Food-Drug Interactions</span>
            </div>

            <div className="space-y-3">
              {drugInteractions.map((item, idx) => (
                <div key={idx} className="bg-slate-950 p-4 rounded-xl border border-amber-950/80 space-y-2">
                  <h4 className="text-sm font-bold text-amber-300">{item.title}</h4>
                  <p className="text-xs text-slate-300 leading-relaxed">{item.details}</p>
                  <div className="text-[10px] text-slate-400 font-mono pt-1 border-t border-slate-800">
                    Source: {item.sourceCitation}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
