import { createClient } from '@/utils/supabase/server'
import { SetupRequired } from '@/components/common/SetupRequired'
import { Headphones, AlertTriangle, Search, CheckCircle2 } from 'lucide-react'

export default async function AdminSupportDeskPage() {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />

  const { data: tickets } = await supabase
    .from('support_tickets')
    .select(`
      *,
      customer:profiles!customer_id(full_name, email)
    `)
    .order('created_at', { ascending: false })

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex items-center mb-8">
        <Headphones className="w-8 h-8 text-indigo-600 mr-3" />
        <div>
          <h1 className="text-3xl font-bold">AI Support Desk</h1>
          <p className="text-gray-500">MVP deterministic rule-based ticket routing, priority assignment, and resolution paths.</p>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-800">Inbound Support Tickets</h2>
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input 
              type="text" 
              placeholder="Search tickets..." 
              className="pl-9 pr-4 py-2 border border-gray-300 rounded text-sm w-64 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
        </div>

        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Priority</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Customer</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category & Desc</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">AI Analysis</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Recommended Action</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {tickets?.map((ticket: { id: string; priority: string; escalation_required?: boolean; customer?: { full_name?: string; email?: string } | null; category: string; description: string; order_id?: string | null; assistant_explanation?: string; refund_eligibility?: boolean; recommended_action?: string; status: string }) => (
              <tr key={ticket.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    ticket.priority === 'CRITICAL' ? 'bg-red-100 text-red-800' :
                    ticket.priority === 'HIGH' ? 'bg-orange-100 text-orange-800' :
                    ticket.priority === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-green-100 text-green-800'
                  }`}>
                    {ticket.priority}
                  </span>
                  {ticket.escalation_required && (
                    <div className="mt-2 text-xs text-red-600 font-bold flex items-center">
                      <AlertTriangle className="w-3 h-3 mr-1" /> ESCALATED
                    </div>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">{ticket.customer?.full_name || 'Unknown'}</div>
                  <div className="text-xs text-gray-500">{ticket.customer?.email}</div>
                  <div className="text-xs text-gray-400 mt-1 font-mono">Tkt: {ticket.id.slice(0,8)}</div>
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm font-bold text-gray-900 uppercase mb-1">{ticket.category}</div>
                  <div className="text-sm text-gray-600 max-w-xs truncate" title={ticket.description}>
                    &quot;{ticket.description}&quot;
                  </div>
                  {ticket.order_id && (
                    <div className="text-xs text-indigo-600 font-mono mt-1">Order: {ticket.order_id.slice(0,8)}</div>
                  )}
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm text-gray-800 bg-gray-50 p-2 border border-gray-200 rounded">
                    {ticket.assistant_explanation}
                  </div>
                  {ticket.refund_eligibility && (
                    <div className="mt-2 text-xs text-green-600 font-bold flex items-center">
                      <CheckCircle2 className="w-3 h-3 mr-1" /> Eligible for Auto-Refund
                    </div>
                  )}
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm text-gray-900 font-medium">{ticket.recommended_action}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button className="text-indigo-600 hover:text-indigo-900 block mb-2 text-right w-full">Review</button>
                  {ticket.status === 'OPEN' && (
                    <button className="text-green-600 hover:text-green-900 block text-right w-full">Resolve</button>
                  )}
                </td>
              </tr>
            ))}
            {(!tickets || tickets.length === 0) && (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                  No support tickets found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
