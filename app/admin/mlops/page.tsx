import { createClient } from '@/utils/supabase/server'
import { SetupRequired } from '@/components/common/SetupRequired'
import { Activity, Clock, CheckCircle, XCircle } from 'lucide-react'

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
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center">
          <Activity className="w-8 h-8 text-teal-600 mr-3" />
          <div>
            <h1 className="text-3xl font-bold">MLOps Dashboard</h1>
            <p className="text-gray-500">Monitoring for deterministic pipelines and scoring models.</p>
          </div>
        </div>
        <form action="/admin/mlops/actions" method="POST">
          <input type="hidden" name="action" value="score_all" />
          <button className="flex items-center bg-teal-600 text-white px-4 py-2 rounded shadow text-sm font-medium hover:bg-teal-700">
            <RefreshCwIcon />
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
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
          <h2 className="text-lg font-semibold text-gray-800">Pipeline Execution History</h2>
        </div>
        
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Run Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Family</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Started</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Duration</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Errors</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {runs?.map((run: any) => (
              <tr key={run.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  {run.status === 'SUCCESS' ? (
                    <CheckCircle className="w-5 h-5 text-green-500" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-500" />
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {run.run_name}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 uppercase tracking-wider">
                  {run.model_family}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  <div className="flex items-center">
                    <Clock className="w-4 h-4 mr-1 text-gray-400" />
                    {new Date(run.started_at).toLocaleString()}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {run.duration_ms} ms
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
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
  )
}

function RefreshCwIcon() {
  return (
    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  )
}
