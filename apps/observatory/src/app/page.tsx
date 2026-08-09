"use client";

import { useEffect, useState } from "react";
import { Clock, MapPin, Search } from "lucide-react";
import Link from "next/link";

export default function ObserverHome() {
  const [zones, setZones] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Generate a quick mock token just for frontend UI development 
    // Usually this would come from a real login context
    const mockToken = "REDACTED_CREDENTIAL_TOKEN"; // A pre-signed HS256 token with "REDACTED_SYNTHETIC_TEST_SECRET"

    fetch("http://localhost:8000/api/v1/zones", {
      headers: {
        "Authorization": `Bearer ${mockToken}`
      }
    })
      .then(res => {
        if (!res.ok) throw new Error("Failed to fetch zones");
        return res.json();
      })
      .then(json => {
        setZones(json.data || []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setError(err.message);
        setLoading(false);
      });
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <header className="mb-6">
        <h1 className="text-2xl font-bold">ZonePilot Observatory</h1>
        <p className="text-sm text-gray-600">Role: OBSERVER</p>
      </header>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Active Pilot Zones</h2>
        {loading && <p>Loading real map zones...</p>}
        {error && <p className="text-red-500">Error: {error}</p>}
        
        {!loading && !error && zones.length === 0 && (
          <div className="p-8 text-center bg-gray-100 rounded-lg border border-gray-300">
            <h3 className="text-xl font-bold text-gray-700">NETWORK DATA UNAVAILABLE</h3>
            <p className="text-gray-500 mt-2">The API did not return any active pilot zones.</p>
          </div>
        )}
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {!loading && zones.slice(0, 50).map((zone, idx) => (
            <div key={idx} className="bg-white rounded-xl shadow-sm border border-blue-200 p-4">
              <div className="flex justify-between items-start mb-3">
                <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded">
                  H3-R{zone.resolution}
                </span>
              </div>
              
              <h3 className="text-lg font-bold mb-1 font-mono">{zone.zone_id}</h3>
              <p className="text-gray-600 text-sm mb-4">Boundary points: {zone.boundary?.length}</p>
              
              <Link href={`/capture?zone_id=${zone.zone_id}`}>
                <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg flex justify-center items-center">
                  <Search className="w-5 h-5 mr-2" />
                  Capture Evidence
                </button>
              </Link>
            </div>
          ))}
          {!loading && zones.length > 50 && (
            <div className="p-4 text-gray-500 text-sm text-center col-span-full">
              + {zones.length - 50} more zones not displayed.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
