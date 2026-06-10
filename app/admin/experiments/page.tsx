import { createClient } from '@/utils/supabase/server'
import { SetupRequired } from '@/components/common/SetupRequired'
import { Beaker, TrendingUp, Users, RefreshCw } from 'lucide-react'

export default async function AdminExperimentsPage() {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />

  const { data: experiments } = await supabase
    .from('experiments')
    .select('id, name, description, status, created_at')
    .order('created_at', { ascending: false })

  const { data: metrics } = await supabase
    .from('experiment_metrics')
    .select(`
      *,
      variant:experiment_variants(name, allocation_percentage)
    `)
    .order('variant_id', { ascending: true })

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center">
          <Beaker className="w-8 h-8 text-purple-600 mr-3" />
          <div>
            <h1 className="text-3xl font-bold">A/B Experiments Platform</h1>
            <p className="text-gray-500">MVP directional experiment readout; not a production statistical inference engine.</p>
          </div>
        </div>
        <form action="/admin/experiments/actions" method="POST">
          <input type="hidden" name="action" value="simulate" />
          <button className="flex items-center bg-purple-600 text-white px-4 py-2 rounded shadow text-sm font-medium hover:bg-purple-700">
            <RefreshCw className="w-4 h-4 mr-2" />
            Simulate Traffic
          </button>
        </form>
      </div>

      <div className="space-y-8">
        {experiments?.map(exp => {
          const expMetrics = metrics?.filter(m => m.experiment_id === exp.id) || []
          
          return (
            <div key={exp.id} className="bg-white rounded-lg shadow overflow-hidden border border-gray-200">
              <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">{exp.name}</h2>
                  <p className="text-sm text-gray-500">{exp.description}</p>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                  exp.status === 'ACTIVE' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                }`}>
                  {exp.status}
                </span>
              </div>
              
              {expMetrics.length > 0 ? (
                <div className="p-6">
                  <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                    {expMetrics.map(m => (
                      <div key={m.id} className={`p-4 rounded-lg border ${
                        m.recommendation === 'continue (winning)' ? 'bg-green-50 border-green-200' :
                        m.recommendation === 'stop (underperforming)' ? 'bg-red-50 border-red-200' :
                        'bg-gray-50 border-gray-200'
                      }`}>
                        <div className="flex justify-between items-center mb-2">
                          <h3 className="font-bold text-gray-900">{m.variant?.name || 'Unknown Variant'}</h3>
                          <span className="text-xs text-gray-500">{m.variant?.allocation_percentage}% Alloc</span>
                        </div>
                        <div className="space-y-2 mt-4">
                          <div className="flex justify-between text-sm">
                            <span className="text-gray-500">Impressions</span>
                            <span className="font-medium text-gray-900">{m.impressions}</span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span className="text-gray-500">Conversions</span>
                            <span className="font-medium text-gray-900">{m.conversions}</span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span className="text-gray-500">Conv. Rate</span>
                            <span className="font-bold text-purple-600">{Number(m.conversion_rate).toFixed(1)}%</span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span className="text-gray-500">Revenue</span>
                            <span className="font-medium text-gray-900">${Number(m.revenue).toFixed(2)}</span>
                          </div>
                        </div>
                        <div className="mt-4 pt-3 border-t border-gray-200/50">
                          <div className="text-xs font-semibold text-center uppercase tracking-wider text-gray-600">
                            {m.recommendation}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="p-8 text-center text-gray-500">
                  <p>No metrics collected yet. Click &quot;Simulate Traffic&quot; to generate data.</p>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
