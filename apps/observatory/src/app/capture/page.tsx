"use client";

import { useState, Suspense, useEffect } from "react";
import { ArrowLeft, Save } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { saveToOutbox, syncOutbox } from "../../lib/outbox";

function CaptureForm() {
  const searchParams = useSearchParams();
  const order_id = searchParams?.get('order_id') || '';

  useEffect(() => {
    window.addEventListener('online', syncOutbox);
    syncOutbox();
    return () => window.removeEventListener('online', syncOutbox);
  }, []);

  const [formData, setFormData] = useState({
    etaLow: "",
    etaHigh: "",
    optionCount: "",
    availability: "AVAILABLE",
    substitutionStatus: "EXACT_MATCH",
    basketPrice: "",
    deliveryFee: "",
    platformFee: "",
    otherFee: ""
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [outboxMessage, setOutboxMessage] = useState('');

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.etaLow || isNaN(Number(formData.etaLow))) newErrors.etaLow = "Required valid number";
    if (!formData.etaHigh || isNaN(Number(formData.etaHigh))) newErrors.etaHigh = "Required valid number";
    if (Number(formData.etaLow) > Number(formData.etaHigh)) newErrors.etaHigh = "High ETA must be >= Low ETA";
    if (!formData.optionCount || isNaN(Number(formData.optionCount))) newErrors.optionCount = "Required valid number";
    
    if (formData.availability === "AVAILABLE") {
      if (!formData.basketPrice || isNaN(Number(formData.basketPrice))) newErrors.basketPrice = "Required valid amount";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validate()) {
      const payloadData = {
         ...formData,
         observationTimestamp: new Date().toISOString(),
         timeQuality: "PRECISE"
      };

      const eventPayload = {
         order_id: order_id,
         event_type: "PROBE",
         occurred_at: new Date().toISOString(),
         provenance: "OBSERVED",
         payload: payloadData
      };

      saveToOutbox(eventPayload).then(() => { 
          setOutboxMessage('Observation queued in outbox for sync!');
          syncOutbox(); 
      }); 
    }
  };

  return (
      <form onSubmit={handleSubmit} className="p-4 space-y-6">
        <div className="bg-white rounded-xl shadow-sm border p-4">
          <h2 className="font-semibold mb-4 text-gray-800">Reference Basket</h2>
          <div className="p-3 bg-blue-50 text-blue-900 rounded-lg text-sm mb-4">
            Items: 1x Biryani, 1x Coke (500ml)
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Availability</label>
              <select 
                className="w-full rounded-lg border-gray-300 shadow-sm p-2.5 bg-gray-50 border"
                value={formData.availability}
                onChange={e => setFormData({...formData, availability: e.target.value})}
              >
                <option value="AVAILABLE">Available</option>
                <option value="UNAVAILABLE">Unavailable</option>
              </select>
            </div>
          </div>
        </div>

        {formData.availability === "AVAILABLE" && (
          <>
            <div className="bg-white rounded-xl shadow-sm border p-4">
              <h2 className="font-semibold mb-4 text-gray-800">Delivery Logistics</h2>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">ETA Low (min)</label>
                  <input 
                    type="number"
                    className={`w-full rounded-lg border p-2.5 ${errors.etaLow ? 'border-red-500' : 'border-gray-300'}`}
                    value={formData.etaLow}
                    onChange={e => setFormData({...formData, etaLow: e.target.value})}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">ETA High (min)</label>
                  <input 
                    type="number"
                    className={`w-full rounded-lg border p-2.5 ${errors.etaHigh ? 'border-red-500' : 'border-gray-300'}`}
                    value={formData.etaHigh}
                    onChange={e => setFormData({...formData, etaHigh: e.target.value})}
                  />
                </div>
              </div>
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Option Count</label>
                <input 
                  type="number"
                  className={`w-full rounded-lg border p-2.5 ${errors.optionCount ? 'border-red-500' : 'border-gray-300'}`}
                  value={formData.optionCount}
                  onChange={e => setFormData({...formData, optionCount: e.target.value})}
                />
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border p-4">
              <h2 className="font-semibold mb-4 text-gray-800">Financials (INR)</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Basket Price</label>
                  <input 
                    type="number" step="0.01"
                    className={`w-full rounded-lg border p-2.5 ${errors.basketPrice ? 'border-red-500' : 'border-gray-300'}`}
                    value={formData.basketPrice}
                    onChange={e => setFormData({...formData, basketPrice: e.target.value})}
                  />
                </div>
              </div>
            </div>
          </>
        )}

        {outboxMessage && (
            <div data-testid="outbox-status" className="text-green-600 font-bold mb-4">{outboxMessage}</div>
        )}

        <button type="submit" className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 px-4 rounded-xl flex justify-center items-center mb-4">
          <Save className="w-5 h-5 mr-2" />
          Save Observation
        </button>
      </form>
  );
}

export default function CaptureScreen() {
  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      <header className="bg-white border-b sticky top-0 z-10 px-4 py-3 flex items-center">
        <Link href="/" className="mr-4">
          <ArrowLeft className="w-6 h-6 text-gray-700" />
        </Link>
        <h1 className="text-lg font-bold">Capture Probe</h1>
      </header>
      <Suspense fallback={<div>Loading...</div>}>
         <CaptureForm />
      </Suspense>
    </div>
  )
}
