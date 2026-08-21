import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { BASE_URL } from '../utils/apiClient';
import { Pill, ShieldCheck, AlertTriangle, ShoppingBag, ExternalLink, Activity, RefreshCw } from 'lucide-react';
import { PatientMedicine, PatientConditionInfo } from '../types';
import { PatientPurchaseModal } from '../components/PatientPurchaseModal';

interface PatientMedicinePageProps {
  currentLanguage: string;
}

export const PatientMedicinePage: React.FC<PatientMedicinePageProps> = ({ currentLanguage }) => {
  const { user } = useAuth();
  const [medicines, setMedicines] = useState<PatientMedicine[]>([]);
  const [conditions, setConditions] = useState<PatientConditionInfo[]>([]);
  const [disclaimer, setDisclaimer] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [purchaseModalOpen, setPurchaseModalOpen] = useState<boolean>(false);
  const [selectedMedForPurchase, setSelectedMedForPurchase] = useState<string>('');

  const fetchMedicineData = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${BASE_URL}/api/v1/patient-portal/medicines`, {
        headers: {
          'X-User-Email': user?.email || '',
          'X-User-Role': user?.role || 'patient',
        },
      });
      const data = await res.json();
      if (data.success && data.data) {
        setMedicines(data.data.medicines || []);
        setConditions(data.data.conditions || []);
        setDisclaimer(data.data.disclaimer || '');
      }
    } catch (err) {
      console.error('Fetch medicines error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMedicineData();
  }, []);

  const handleOpenPurchase = (medName: string) => {
    setSelectedMedForPurchase(medName);
    setPurchaseModalOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Title Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center space-x-2">
            <Pill className="w-7 h-7 text-cyan-400" />
            <span>Prescribed Medicine & Reference Information</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Verified medicine data powered by RxNorm (NIH), FDA National Drug Code Directory, and MedlinePlus.
          </p>
        </div>
      </div>

      {/* MANDATORY PROMINENT DISCLAIMER */}
      <div className="bg-amber-950/60 border border-amber-800/80 rounded-2xl p-4 flex items-start space-x-3 text-amber-200 shadow-lg">
        <AlertTriangle className="w-6 h-6 text-amber-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-1 text-xs">
          <strong className="text-amber-300 font-bold uppercase tracking-wider block">
            Mandatory Medical Disclaimer:
          </strong>
          <p className="leading-relaxed">
            {disclaimer ||
              'This information is for reference only and is not a substitute for professional medical advice. Always follow your doctor’s prescribed dosage and instructions.'}
          </p>
        </div>
      </div>

      {loading && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin mx-auto" />
          <p className="text-sm font-semibold text-slate-200">Querying RxNorm & MedlinePlus Reference APIs...</p>
        </div>
      )}

      {!loading && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Column: Prescribed Medicines */}
          <div className="lg:col-span-2 space-y-4">
            <h2 className="text-lg font-bold text-white flex items-center space-x-2">
              <Pill className="w-5 h-5 text-emerald-400" />
              <span>Extracted & Verified Medicines</span>
            </h2>

            {medicines.length === 0 ? (
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center text-slate-400 text-xs">
                No medicines found in your uploaded prescription yet. Please upload a prescription on the 'My Prescription' tab.
              </div>
            ) : (
              medicines.map((med) => (
                <div
                  key={med.id}
                  className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 shadow-xl space-y-4 transition-all"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                    <div>
                      <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                        <span>{med.name}</span>
                        {med.prescriptionRequired && (
                          <span className="text-[10px] bg-red-950 text-red-300 border border-red-800/60 px-2 py-0.5 rounded-md font-semibold">
                            Rx Required
                          </span>
                        )}
                      </h3>
                      <p className="text-xs text-emerald-400 font-medium mt-0.5">
                        Dosage: {med.dosage} • Frequency: {med.frequency}
                      </p>
                    </div>

                    <button
                      onClick={() => handleOpenPurchase(med.name)}
                      className="inline-flex items-center space-x-1.5 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs px-3.5 py-2 rounded-xl transition-all shadow-md self-start sm:self-auto"
                    >
                      <ShoppingBag className="w-3.5 h-3.5" />
                      <span>Verify & Purchase</span>
                    </button>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed">
                    {med.generalDescription}
                  </p>

                  <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 flex items-center justify-between text-xs text-slate-400">
                    <div className="flex items-center space-x-1.5">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                      <span>Source Citation:</span>
                    </div>
                    <span className="font-mono text-[11px] text-cyan-300">{med.sourceCitation}</span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Right Column: Conditions & Health Topics */}
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-white flex items-center space-x-2">
              <Activity className="w-5 h-5 text-cyan-400" />
              <span>Identified Health Conditions</span>
            </h2>

            {conditions.length === 0 ? (
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 text-center text-slate-400 text-xs">
                No specific conditions identified in prescription.
              </div>
            ) : (
              conditions.map((cond, idx) => (
                <div
                  key={idx}
                  className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-3"
                >
                  <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                    <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
                    <span>{cond.conditionName}</span>
                  </h3>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {cond.summary}
                  </p>
                  <div className="text-[11px] text-slate-400 pt-2 border-t border-slate-800 flex items-center justify-between">
                    <span>Reference:</span>
                    <span className="text-cyan-400 font-mono">{cond.sourceCitation}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      <PatientPurchaseModal
        isOpen={purchaseModalOpen}
        onClose={() => setPurchaseModalOpen(false)}
        defaultMedicineName={selectedMedForPurchase}
      />
    </div>
  );
};
