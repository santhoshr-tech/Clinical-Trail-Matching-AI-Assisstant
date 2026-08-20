import React, { useState } from 'react';
import { ShoppingBag, AlertTriangle, CheckCircle, ExternalLink, X, ShieldAlert } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface PatientPurchaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultMedicineName?: string;
}

export const PatientPurchaseModal: React.FC<PatientPurchaseModalProps> = ({
  isOpen,
  onClose,
  defaultMedicineName = '',
}) => {
  const { user } = useAuth();
  const [medicineName, setMedicineName] = useState(defaultMedicineName);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  if (!isOpen) return null;

  const handleVerifyAndPurchase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!medicineName.trim()) return;

    setLoading(true);
    setResult(null);

    try {
      const res = await fetch('/api/v1/patient-portal/verify-purchase', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Email': user?.email || '',
          'X-User-Role': user?.role || 'patient',
        },
        body: JSON.stringify({ medicineName: medicineName.trim() }),
      });
      const data = await res.json();
      if (data.success) {
        setResult(data.data);
      }
    } catch (err) {
      console.error('Purchase verification error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 text-cyan-400">
          <ShoppingBag className="w-6 h-6" />
          <h2 className="text-xl font-bold text-white">Purchase Medicine Verification</h2>
        </div>

        <form onSubmit={handleVerifyAndPurchase} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Medicine Name to Purchase
            </label>
            <input
              type="text"
              value={medicineName}
              onChange={(e) => setMedicineName(e.target.value)}
              placeholder="e.g. Amoxicillin, Paracetamol"
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-cyan-500"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-semibold py-2.5 px-4 rounded-xl transition-all flex items-center justify-center space-x-2"
          >
            <ShoppingBag className="w-4 h-4" />
            <span>{loading ? 'Checking Rx Verification...' : 'Verify & Proceed to Purchase'}</span>
          </button>
        </form>

        {result && (
          <div className="space-y-4 pt-2">
            {!result.allowed ? (
              <div className="bg-red-950/60 border border-red-800/80 rounded-xl p-4 space-y-2">
                <div className="flex items-center space-x-2 text-red-400 font-bold text-sm">
                  <ShieldAlert className="w-5 h-5 flex-shrink-0" />
                  <span>Purchase Blocked — Prescription Required</span>
                </div>
                <p className="text-xs text-red-200 leading-relaxed">
                  {result.message}
                </p>
                <div className="text-[11px] text-red-300/80 pt-1 font-mono">
                  Legal Compliance Notice: Verification powered by RxNorm & FDA Schedule Standards.
                </div>
              </div>
            ) : (
              <div className="bg-emerald-950/50 border border-emerald-800/70 rounded-xl p-4 space-y-3">
                <div className="flex items-center space-x-2 text-emerald-400 font-bold text-sm">
                  <CheckCircle className="w-5 h-5 flex-shrink-0" />
                  <span>Prescription Validated</span>
                </div>
                <p className="text-xs text-slate-300">
                  {result.message}
                </p>

                <div className="space-y-2 pt-1">
                  <label className="block text-[11px] font-semibold text-emerald-300 uppercase tracking-wider">
                    Licensed Online Pharmacies (External Order):
                  </label>
                  <div className="grid grid-cols-1 gap-2">
                    {result.pharmacies.map((pharm: any, idx: number) => (
                      <a
                        key={idx}
                        href={pharm.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center justify-between bg-slate-950 border border-emerald-900/60 hover:border-emerald-500 px-3.5 py-2 rounded-lg text-xs font-medium text-cyan-300 hover:text-cyan-200 transition-colors"
                      >
                        <span>{pharm.name}</span>
                        <ExternalLink className="w-3.5 h-3.5 text-emerald-400" />
                      </a>
                    ))}
                  </div>
                </div>

                <p className="text-[10px] text-slate-400 italic pt-1 border-t border-emerald-900/40">
                  {result.disclaimer}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
