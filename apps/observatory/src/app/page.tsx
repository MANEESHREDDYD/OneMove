import { CheckCircle2, Clock, MapPin, Search } from "lucide-react";

export default function ObserverHome() {
  // Mock data for initial skeleton
  const participantRole = "OBSERVER";
  const assignments = [
    {
      id: "a1",
      protocol: "ANCHOR",
      zone: "Gachibowli",
      platform: "Food Delivery A",
      intent: "MERCHANT_SEARCH",
      scheduledTime: "12:00 PM",
      captureWindow: "12:00 PM - 12:05 PM",
      status: "OPEN"
    },
    {
      id: "a2",
      protocol: "BURST",
      zone: "Madhapur",
      platform: "Food Delivery B",
      intent: "CHECKOUT_PROBE",
      scheduledTime: "1:00 PM",
      captureWindow: "1:00 PM - 1:02 PM",
      status: "UPCOMING"
    }
  ];

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <header className="mb-6">
        <h1 className="text-2xl font-bold">ZonePilot Observatory</h1>
        <p className="text-sm text-gray-600">Role: {participantRole}</p>
      </header>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Current Assignment</h2>
        {assignments.filter(a => a.status === 'OPEN').map(assignment => (
          <div key={assignment.id} className="bg-white rounded-xl shadow-sm border border-blue-200 p-4">
            <div className="flex justify-between items-start mb-3">
              <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded">
                {assignment.protocol}
              </span>
              <span className="text-blue-600 font-medium text-sm flex items-center">
                <Clock className="w-4 h-4 mr-1" />
                {assignment.captureWindow}
              </span>
            </div>
            
            <h3 className="text-lg font-bold mb-1">{assignment.platform}</h3>
            <p className="text-gray-600 text-sm mb-4">{assignment.intent}</p>
            
            <div className="flex items-center text-sm text-gray-500 mb-4">
              <MapPin className="w-4 h-4 mr-1" />
              Zone: {assignment.zone}
            </div>

            <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg flex justify-center items-center">
              <Search className="w-5 h-5 mr-2" />
              Capture Evidence
            </button>
          </div>
        ))}
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-4">Upcoming Schedule</h2>
        <div className="space-y-3">
          {assignments.filter(a => a.status === 'UPCOMING').map(assignment => (
            <div key={assignment.id} className="bg-white rounded-xl border border-gray-200 p-4 opacity-75">
              <div className="flex justify-between items-center mb-2">
                <span className="font-semibold">{assignment.scheduledTime}</span>
                <span className="bg-gray-100 text-gray-800 text-xs font-semibold px-2.5 py-0.5 rounded">
                  {assignment.protocol}
                </span>
              </div>
              <p className="text-sm font-medium">{assignment.platform} - {assignment.intent}</p>
              <p className="text-xs text-gray-500 mt-1">Zone: {assignment.zone}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
