import React from "react";
import { Activity, AlertTriangle, CheckCircle, Clock, Copy, ListX } from "lucide-react";

interface StatCardProps {
  title: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  colorClass: string;
}

function StatCard({ title, value, icon: Icon, colorClass }: StatCardProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border p-4 flex flex-col items-center justify-center text-center">
      <Icon className={`w-8 h-8 mb-2 ${colorClass}`} />
      <div className="text-2xl font-bold text-gray-800">{value}</div>
      <div className="text-xs text-gray-500 uppercase tracking-wide font-medium mt-1">{title}</div>
    </div>
  );
}

export default function OwnerQCScreen() {
  const stats = {
    expected: 150,
    received: 142,
    missing: 8,
    late: 12,
    duplicates: 2,
    rejected: 4,
    superseded: 6,
    interRaterPairs: 15
  };

  const participantCompletion = [
    { id: "P-101", completion: "100%" },
    { id: "P-102", completion: "92%" },
    { id: "P-103", completion: "45%" }
  ];

  const collectorHealth = [
    { provider: "Open-Meteo", status: "HEALTHY", lastRun: "2 mins ago" },
    { provider: "TomTom (Disabled)", status: "OFFLINE", lastRun: "N/A" }
  ];

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <header className="mb-6">
        <h1 className="text-2xl font-bold">Study Operations QC</h1>
        <p className="text-sm text-gray-600">Real-time observational telemetry</p>
      </header>

      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-4 text-gray-800">Probe Collection Status</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <StatCard title="Expected" value={stats.expected} icon={Activity} colorClass="text-blue-500" />
          <StatCard title="Received" value={stats.received} icon={CheckCircle} colorClass="text-green-500" />
          <StatCard title="Missing" value={stats.missing} icon={ListX} colorClass="text-red-500" />
          <StatCard title="Late" value={stats.late} icon={Clock} colorClass="text-orange-500" />
          <StatCard title="Duplicates" value={stats.duplicates} icon={Copy} colorClass="text-purple-500" />
          <StatCard title="Rejected" value={stats.rejected} icon={AlertTriangle} colorClass="text-red-600" />
          <StatCard title="Superseded" value={stats.superseded} icon={Clock} colorClass="text-gray-500" />
          <StatCard title="IRR Pairs" value={stats.interRaterPairs} icon={Activity} colorClass="text-teal-500" />
        </div>
      </section>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <section className="bg-white rounded-xl shadow-sm border p-4">
          <h2 className="text-lg font-semibold mb-4 text-gray-800">Participant Completion</h2>
          <div className="space-y-3">
            {participantCompletion.map(p => (
              <div key={p.id} className="flex justify-between items-center border-b pb-2 last:border-0">
                <span className="font-medium">{p.id}</span>
                <span className="bg-blue-50 text-blue-800 text-sm font-semibold px-2.5 py-0.5 rounded">
                  {p.completion}
                </span>
              </div>
            ))}
          </div>
        </section>

        <section className="bg-white rounded-xl shadow-sm border p-4">
          <h2 className="text-lg font-semibold mb-4 text-gray-800">Environmental Collectors</h2>
          <div className="space-y-3">
            {collectorHealth.map(c => (
              <div key={c.provider} className="flex flex-col border-b pb-2 last:border-0">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-medium">{c.provider}</span>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded ${c.status === 'HEALTHY' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                    {c.status}
                  </span>
                </div>
                <span className="text-xs text-gray-500">Last run: {c.lastRun}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
