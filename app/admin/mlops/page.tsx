import { createClient } from '@/utils/supabase/server'
import { SetupRequired } from '@/components/common/SetupRequired'
import { Activity, Clock, CheckCircle, RefreshCw, XCircle } from 'lucide-react'

function formatUtcDateTime(value: string) {
  return `${new Date(value).toISOString().slice(0, 16).replace('T', ' ')} UTC`
}

export default async function MLOpsPage() {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />

  const { data: runs } = await supabase
    .from('ml_pipeline_runs')
    .select('*')
    .order('started_at', { ascending: false })
    .limit(50)

  // Calculate some aggregate stats
  const totalRuns = runs?.length || 0
  const totalErrors = runs?.reduce((acc, run) => acc + (run.error_count || 0), 0) || 0
  const totalProcessed = runs?.reduce((acc, run) => acc + (run.input_row_count || 0) + (run.output_row_count || 0), 0) || 0

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-8">
        <div className="flex min-w-0 items-center">
          <Activity className="w-8 h-8 text-teal-600 mr-3 shrink-0" />
          <div className="min-w-0">
            <h1 className="text-2xl md:text-3xl font-bold leading-tight">MLOps Dashboard</h1>
            <p className="text-gray-500">Monitoring for deterministic pipelines and scoring models.</p>
          </div>
        </div>
        <form action="/admin/mlops/actions" method="POST" className="w-full sm:w-auto">
          <input type="hidden" name="action" value="score_all" />
          <button className="flex w-full items-center justify-center bg-teal-600 text-white px-4 py-2 rounded shadow text-sm font-medium hover:bg-teal-700 sm:w-auto">
            <RefreshCw className="w-4 h-4 mr-2" />
            Rerun All Pipelines
          </button>
        </form>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <h3 className="text-gray-500 text-sm font-medium uppercase tracking-wide">Total Runs (Recent)</h3>
          <p className="text-3xl font-bold text-gray-900 mt-2">{totalRuns}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <h3 className="text-gray-500 text-sm font-medium uppercase tracking-wide">Errors Detected</h3>
          <p className={`text-3xl font-bold mt-2 ${totalErrors > 0 ? 'text-red-600' : 'text-green-600'}`}>
            {totalErrors}
          </p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <h3 className="text-gray-500 text-sm font-medium uppercase tracking-wide">Rows Processed</h3>
          <p className="text-3xl font-bold text-gray-900 mt-2">{totalProcessed}</p>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden border border-gray-200">
        <div className="px-4 py-4 md:px-6 border-b border-gray-200 bg-gray-50">
          <h2 className="text-lg font-semibold text-gray-800">Pipeline Execution History</h2>
        </div>
        
        <div className="w-full overflow-x-auto">
          <table className="min-w-[760px] divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Run Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Family</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Started</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Duration</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Errors</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {runs?.map((run: { id: string; status: string; run_name: string; model_family: string; started_at: string; duration_ms: number; error_count: number }) => (
                <tr key={run.id} className="hover:bg-gray-50">
                  <td className="px-4 py-4 whitespace-nowrap">
                    {run.status === 'SUCCESS' ? (
                      <CheckCircle className="w-5 h-5 text-green-500" />
                    ) : (
                      <XCircle className="w-5 h-5 text-red-500" />
                    )}
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {run.run_name}
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 uppercase tracking-wider">
                    {run.model_family}
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                    <div className="flex items-center">
                      <Clock className="w-4 h-4 mr-1 text-gray-400" />
                      {formatUtcDateTime(run.started_at)}
                    </div>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                    {run.duration_ms} ms
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm font-medium">
                    {run.error_count > 0 ? (
                      <span className="text-red-600">{run.error_count}</span>
                    ) : (
                      <span className="text-green-600">0</span>
                    )}
                  </td>
                </tr>
              ))}
              {(!runs || runs.length === 0) && (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                    No pipeline runs recorded.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
