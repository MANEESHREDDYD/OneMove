import { createClient } from '@/utils/supabase/server'
import { SetupRequired } from '@/components/common/SetupRequired'
import { LifeBuoy, AlertCircle, Clock } from 'lucide-react'

export default async function CustomerSupportPage() {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />

  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return <div className="p-8">Please log in to access support.</div>

  const { data: tickets } = await supabase
    .from('support_tickets')
    .select('*')
    .eq('customer_id', user.id)
    .order('created_at', { ascending: false })

  const { data: recentOrders } = await supabase
    .from('orders')
    .select('id, total_amount, status, created_at')
    .eq('customer_id', user.id)
    .order('created_at', { ascending: false })
    .limit(5)

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center mb-8">
        <LifeBuoy className="w-8 h-8 text-blue-600 mr-3" />
        <div>
          <h1 className="text-3xl font-bold">Help & Support</h1>
          <p className="text-gray-500">MVP deterministic rule-based intelligence, not a production LLM or trained ML model.</p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
          <h2 className="text-xl font-semibold mb-4">Create a Ticket</h2>
          <form action="/customer/support/actions" method="POST" className="space-y-4">
            <input type="hidden" name="action" value="create_ticket" />
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Related Order (Optional)</label>
              <select name="order_id" className="w-full border-gray-300 rounded shadow-sm py-2 px-3 border">
                <option value="">None / General Inquiry</option>
                {recentOrders?.map(order => (
                  <option key={order.id} value={order.id}>
                    Order {order.id.slice(0,8)} - ${order.total_amount} - {new Date(order.created_at).toLocaleDateString()}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">How can we help?</label>
              <textarea 
                name="description" 
                rows={4} 
                required 
                className="w-full border-gray-300 rounded shadow-sm py-2 px-3 border"
                placeholder="E.g., My item was missing, my food arrived late..."
              ></textarea>
            </div>

            <button type="submit" className="w-full bg-blue-600 text-white font-medium py-2 px-4 rounded shadow hover:bg-blue-700">
              Submit Ticket
            </button>
          </form>
        </div>

        <div>
          <h2 className="text-xl font-semibold mb-4">Your Recent Tickets</h2>
          {tickets && tickets.length > 0 ? (
            <div className="space-y-4">
              {tickets.map((ticket: any) => (
                <div key={ticket.id} className="bg-white rounded-lg shadow border border-gray-200 p-4">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-sm font-semibold uppercase text-gray-600">{ticket.category}</span>
                    <span className={`px-2 py-0.5 text-xs font-bold rounded ${
                      ticket.status === 'OPEN' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {ticket.status}
                    </span>
                  </div>
                  <p className="text-gray-800 text-sm mb-3">"{ticket.description}"</p>
                  
                  {ticket.assistant_explanation && (
                    <div className="bg-blue-50 text-blue-800 p-2 text-xs rounded mb-2 border border-blue-100">
                      <strong>AI Review:</strong> {ticket.assistant_explanation}
                    </div>
                  )}

                  <div className="flex items-center text-xs text-gray-400">
                    <Clock className="w-3 h-3 mr-1" />
                    {new Date(ticket.created_at).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-gray-500 border border-dashed border-gray-300 rounded-lg p-8 text-center">
              No recent support tickets.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
