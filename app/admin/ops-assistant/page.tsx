import { createClient } from '@/utils/supabase/server'
import { SetupRequired } from '@/components/common/SetupRequired'
import { getActiveOpsInsights } from '@/lib/ai/adminOpsAssistant'
import { Brain, CheckCircle, AlertTriangle, AlertCircle, Info } from 'lucide-react'

export default async function OpsAssistantPage() {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />

  const insights = await getActiveOpsInsights(supabase)

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex items-center mb-8">
        <Brain className="w-8 h-8 text-blue-600 mr-3" />
        <div>
          <h1 className="text-3xl font-bold">Admin Ops Assistant</h1>
          <p className="text-gray-500">MVP deterministic rule-based intelligence, not a production LLM or trained ML model.</p>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-800">Prioritized Action Items ({insights.length})</h2>
          <form action="/admin/ops-assistant/actions" method="POST">
            <input type="hidden" name="action" value="generate" />
            <button className="bg-blue-600 text-white px-4 py-2 rounded shadow text-sm font-medium hover:bg-blue-700">
              Refresh Insights
            </button>
          </form>
        </div>

        {insights.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
            <p className="text-lg">All caught up! No critical operational issues detected.</p>
          </div>
        ) : (
          <ul className="divide-y divide-gray-200">
            {insights.map((insight: { id: string; severity: string; category: string; explanation: string; recommended_action: string; source_table: string; source_id?: string }) => (
              <li key={insight.id} className="p-6 flex flex-col md:flex-row gap-4 items-start hover:bg-gray-50">
                <div className="flex-shrink-0 mt-1">
                  {insight.severity === 'HIGH' && <AlertCircle className="w-6 h-6 text-red-500" />}
                  {insight.severity === 'MEDIUM' && <AlertTriangle className="w-6 h-6 text-yellow-500" />}
                  {insight.severity === 'LOW' && <Info className="w-6 h-6 text-blue-500" />}
                </div>
                <div className="flex-grow">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2 py-0.5 text-xs font-bold rounded ${
                      insight.severity === 'HIGH' ? 'bg-red-100 text-red-800' :
                      insight.severity === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-blue-100 text-blue-800'
                    }`}>
                      {insight.severity}
                    </span>
                    <span className="text-sm font-medium text-gray-500 uppercase tracking-wider">{insight.category.replace(/_/g, ' ')}</span>
                  </div>
                  <p className="text-gray-900 font-medium text-lg mb-2">{insight.explanation}</p>
                  <div className="bg-blue-50 text-blue-800 p-3 rounded text-sm mb-3 border border-blue-100">
                    <span className="font-semibold">Recommended Action:</span> {insight.recommended_action}
                  </div>
                  <div className="text-xs text-gray-400 font-mono">
                    Source: {insight.source_table} | ID: {insight.source_id?.slice(0,8) || 'N/A'}
                  </div>
                </div>
                <div className="md:ml-auto flex-shrink-0">
                  <form action="/admin/ops-assistant/actions" method="POST">
                    <input type="hidden" name="action" value="mark_reviewed" />
                    <input type="hidden" name="insight_id" value={insight.id} />
                    <button className="text-gray-500 hover:text-green-600 border border-gray-300 hover:border-green-600 px-3 py-1.5 rounded text-sm font-medium transition-colors">
                      Mark Reviewed
                    </button>
                  </form>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
