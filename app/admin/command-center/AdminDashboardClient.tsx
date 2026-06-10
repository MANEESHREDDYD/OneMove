'use client'

import { GlassCard } from "@/components/common/GlassCard"
import { Database } from "@/types/database.types"
import { Shield, Activity, DollarSign, Users, Globe, CheckCircle, Clock, RefreshCw } from "lucide-react"
import { LiveCityPreview } from "@/components/maps/LiveCityPreview"
import { useRouter } from "next/navigation"
import { useState } from "react"

type Order = Database['public']['Tables']['orders']['Row']

function formatUtcDateTime(value: string) {
  return `${new Date(value).toISOString().slice(0, 16).replace('T', ' ')} UTC`
}

export function AdminDashboardClient({ 
  globalOrders,
  merchants,
  metrics
}: { 
  globalOrders: Order[],
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  merchants: any[],
  metrics: { 
    gmv: number, 
    totalOrders: number, 
    activeCustomers: number,
    completionRate: number
  }
}) {
  const router = useRouter()
  const [isRefreshing, setIsRefreshing] = useState(false)

  const handleRefresh = () => {
    setIsRefreshing(true)
    router.refresh()
    setTimeout(() => setIsRefreshing(false), 500)
  }

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Map Section */}
      <div className="w-full h-[400px] rounded-xl overflow-hidden border bg-muted mb-8 relative">
        <LiveCityPreview orders={globalOrders} merchants={merchants} />
      </div>
      
      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <GlassCard className="p-4 flex flex-col justify-center border-t-2 border-t-emerald-500">
          <div className="flex justify-between items-start mb-2">
            <p className="text-xs text-muted-foreground uppercase font-bold tracking-wider">Platform GMV</p>
            <DollarSign className="w-4 h-4 text-emerald-500" />
          </div>
          <p className="text-2xl font-black text-emerald-500">${metrics.gmv.toFixed(2)}</p>
        </GlassCard>
        
        <GlassCard className="p-4 flex flex-col justify-center border-t-2 border-t-blue-500">
          <div className="flex justify-between items-start mb-2">
            <p className="text-xs text-muted-foreground uppercase font-bold tracking-wider">Total Volume</p>
            <Globe className="w-4 h-4 text-blue-500" />
          </div>
          <p className="text-2xl font-black text-blue-500">{metrics.totalOrders}</p>
        </GlassCard>
        
        <GlassCard className="p-4 flex flex-col justify-center border-t-2 border-t-purple-500">
          <div className="flex justify-between items-start mb-2">
            <p className="text-xs text-muted-foreground uppercase font-bold tracking-wider">Active Customers</p>
            <Users className="w-4 h-4 text-purple-500" />
          </div>
          <p className="text-2xl font-black text-purple-500">{metrics.activeCustomers}</p>
        </GlassCard>
        
        <GlassCard className="p-4 flex flex-col justify-center border-t-2 border-t-orange-500">
          <div className="flex justify-between items-start mb-2">
            <p className="text-xs text-muted-foreground uppercase font-bold tracking-wider">Completion Rate</p>
            <Activity className="w-4 h-4 text-orange-500" />
          </div>
          <p className="text-2xl font-black text-orange-500">{metrics.completionRate.toFixed(1)}%</p>
        </GlassCard>
      </div>

      {/* Global Order Feed */}
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-bold flex items-center gap-2">
            <Shield className="w-5 h-5 text-primary" /> Live Global Feed
          </h2>
          <button 
            onClick={handleRefresh}
            className="flex items-center gap-2 text-xs font-bold bg-primary/10 text-primary px-3 py-1.5 rounded-full hover:bg-primary/20 transition-colors"
          >
            <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
            Force Sync
          </button>
        </div>
        
        <GlassCard className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-muted-foreground uppercase bg-primary/5">
                <tr>
                  <th className="px-6 py-4 font-bold">Order ID</th>
                  <th className="px-6 py-4 font-bold">Service</th>
                  <th className="px-6 py-4 font-bold">Status</th>
                  <th className="px-6 py-4 font-bold">Amount</th>
                  <th className="px-6 py-4 font-bold">Created</th>
                  <th className="px-6 py-4 font-bold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-primary/10">
                {globalOrders.map((order) => (
                  <tr key={order.id} className="hover:bg-primary/5 transition-colors">
                    <td className="px-6 py-4 font-mono text-xs">{order.id.split('-')[0]}</td>
                    <td className="px-6 py-4 font-bold capitalize text-primary">{order.service_type}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1.5">
                        {order.status === 'completed' ? (
                          <CheckCircle className="w-3 h-3 text-emerald-500" />
                        ) : (
                          <Clock className="w-3 h-3 text-orange-500" />
                        )}
                        <span className="capitalize">{order.status.replace('_', ' ')}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 font-bold">${order.total_amount?.toFixed(2)}</td>
                    <td className="px-6 py-4 text-muted-foreground text-xs">
                      {formatUtcDateTime(order.created_at)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <a href={`/admin/orders/${order.id}`} className="text-xs font-bold text-primary hover:underline">
                        View Details -&gt;
                      </a>
                    </td>
                  </tr>
                ))}
                {globalOrders.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-muted-foreground">
                      No platform activity yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </GlassCard>
      </div>

    </div>
  )
}
