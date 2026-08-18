import Link from "next/link";
import { ArrowLeft, TriangleAlert } from "lucide-react";

export const metadata = {
  title: "Study operations QC · ZonePilot Observatory",
};

/**
 * Study operations QC.
 *
 * This screen previously rendered hardcoded counts (expected/received/missing,
 * per-participant completion, collector status) as though they were live
 * telemetry. No QC endpoint exists: the ZonePilot API exposes zones, network
 * snapshots, map layers, datasets, data-health, evidence and version, and
 * nothing that reports study operations. Displaying invented numbers on a page
 * captioned "real-time" is worse than displaying nothing, because a reader
 * cannot tell the difference between a fabricated 142 and a measured one.
 *
 * Until a QC endpoint exists this route states, explicitly, that the capability
 * is not available. It renders no counts at all.
 */

const UNAVAILABLE_MEASURES = [
  {
    group: "Probe collection",
    measures: ["Expected", "Received", "Missing", "Late", "Duplicates", "Rejected", "Superseded"],
  },
  { group: "Inter-rater reliability", measures: ["Paired assignments", "Agreement"] },
  { group: "Participant completion", measures: ["Per-participant completion rate"] },
  { group: "Environmental collectors", measures: ["Per-provider run status and recency"] },
];

export default function OwnerQCScreen() {
  return (
    <main className="min-h-screen bg-slate-100 px-4 py-6 text-slate-950 sm:px-6 lg:px-8" id="main-content">
      <div className="mx-auto max-w-4xl">
        <header className="border-b border-slate-300 pb-6">
          <Link
            className="inline-flex min-h-11 items-center gap-2 rounded-lg px-2 text-sm font-semibold text-blue-800 hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
            href="/"
          >
            <ArrowLeft aria-hidden="true" className="h-4 w-4" /> Observatory
          </Link>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Study operations QC</h1>
          <p className="mt-2 text-sm text-slate-700">
            Collection completeness and inter-rater reliability for the pilot study.
          </p>
        </header>

        <section aria-labelledby="qc-status-title" className="mt-8">
          <div className="rounded-xl border border-amber-300 bg-amber-50 p-5 text-amber-950" role="status">
            <div className="flex items-start gap-3">
              <TriangleAlert aria-hidden="true" className="mt-0.5 h-6 w-6 shrink-0" />
              <div>
                <p className="text-xs font-bold uppercase tracking-wide">QC telemetry unavailable</p>
                <h2 className="mt-1 text-lg font-semibold" id="qc-status-title">
                  No study operations data is being reported
                </h2>
                <p className="mt-2 text-sm leading-6">
                  The ZonePilot API does not yet expose a study operations endpoint, so there are no
                  measured QC counts to display. This screen intentionally shows no figures rather
                  than placeholder ones: every number here would be invented, and an invented count
                  is indistinguishable from a real one once it is on the page.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section aria-labelledby="qc-pending-title" className="mt-10">
          <h2 className="text-xl font-semibold" id="qc-pending-title">
            Measures this screen will report
          </h2>
          <p className="mt-1 text-sm text-slate-700">
            Listed so the gap is legible. None of these are currently measured.
          </p>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[32rem] border-collapse text-left">
              <caption className="sr-only">
                Planned study operations QC measures, all currently unavailable.
              </caption>
              <thead>
                <tr className="border-b border-slate-300 bg-slate-50">
                  <th className="px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-700" scope="col">
                    Group
                  </th>
                  <th className="px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-700" scope="col">
                    Measures
                  </th>
                  <th className="px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-700" scope="col">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody>
                {UNAVAILABLE_MEASURES.map((row) => (
                  <tr className="border-b border-slate-200 bg-white last:border-0" key={row.group}>
                    <th className="px-4 py-3 text-sm font-semibold" scope="row">
                      {row.group}
                    </th>
                    <td className="px-4 py-3 text-sm text-slate-700">{row.measures.join(", ")}</td>
                    <td className="px-4 py-3">
                      <span className="inline-block whitespace-nowrap rounded-full bg-slate-200 px-2 py-1 text-[0.65rem] font-bold text-slate-800">
                        NOT MEASURED
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}
