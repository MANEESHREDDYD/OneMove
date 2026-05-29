'use client'

import { useState } from 'react'
import { GlassCard } from "@/components/common/GlassCard"
import { Button } from "@/components/ui/button"
import { Store, Clock, Utensils, History, CheckCircle, XCircle, Power } from "lucide-react"
import { MerchantActionButtons } from "./MerchantActionButtons"
import { Database } from "@/types/database.types"

type Order = Database['public']['Tables']['orders']['Row']

export function MerchantDashboardClient({ 
  activeOrders, 
  historyOrders,
  metrics
}: { 
  activeOrders: Order[],
  historyOrders: Order[],
  metrics: { totalRevenue: number, totalOrders: number, completedOrders: number }
}) {
  const [activeTab, setActiveTab] = useState<'active' | 'history' | 'settings'>('active')
  const [storeOpen, setStoreOpen] = useState(true)

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <GlassCard className="p-4 flex flex-col justify-center border-t-2 border-t-blue-500">
          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Today&apos;s Revenue</p>
          <p className="text-2xl font-black text-blue-500">${metrics.totalRevenue.toFixed(2)}</p>
        </GlassCard>
        <GlassCard className="p-4 flex flex-col justify-center border-t-2 border-t-green-500">
          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Active Orders</p>
          <p className="text-2xl font-black text-green-500">{activeOrders.length}</p>
        </GlassCard>
        <GlassCard className="p-4 flex flex-col justify-center border-t-2 border-t-orange-500">
          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Total Orders</p>
          <p className="text-2xl font-black text-orange-500">{metrics.totalOrders}</p>
        </GlassCard>
        <GlassCard className="p-4 flex flex-col justify-center border-t-2 border-t-primary">
          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Store Status</p>
          <div className="flex items-center gap-2">
            <span className={`h-3 w-3 rounded-full ${storeOpen ? 'bg-green-500 animate-pulse' : 'bg-destructive'}`}></span>
            <p className="text-lg font-bold">{storeOpen ? 'Accepting' : 'Paused'}</p>
          </div>
        </GlassCard>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 overflow-x-auto pb-2 hide-scrollbar">
        <Button 
          variant={activeTab === 'active' ? 'default' : 'secondary'} 
          onClick={() => setActiveTab('active')}
          className="rounded-full"
        >
          <Clock className="w-4 h-4 mr-2" /> Live Queue
        </Button>
        <Button 
          variant={activeTab === 'history' ? 'default' : 'secondary'} 
          onClick={() => setActiveTab('history')}
          className="rounded-full"
        >
          <History className="w-4 h-4 mr-2" /> History
        </Button>
        <Button 
          variant={activeTab === 'settings' ? 'default' : 'secondary'} 
          onClick={() => setActiveTab('settings')}
          className="rounded-full"
        >
          <Store className="w-4 h-4 mr-2" /> Store Settings
        </Button>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {/* ACTIVE TAB */}
        {activeTab === 'active' && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {activeOrders.length === 0 ? (
              <GlassCard className="col-span-full p-12 text-center border-dashed border-primary/20">
                <Utensils className="h-12 w-12 text-muted-foreground mx-auto mb-4 opacity-50" />
                <p className="font-semibold text-lg">Queue is empty</p>
                <p className="text-muted-foreground mt-1">Waiting for customers to order...</p>
              </GlassCard>
            ) : (
              activeOrders.map((order) => {
                const orderData = order as unknown;
                const items = (orderData as { metadata?: { items?: { name: string, quantity: number }[] } })?.metadata?.items || []
                
                return (
                  <GlassCard key={order.id} className="p-5 flex flex-col justify-between h-full border-t-4 border-t-orange-500">
                    <div>
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <p className="text-xs text-muted-foreground uppercase font-bold tracking-wider mb-1">
                            Order #{order.id.split('-')[0]}
                          </p>
                          <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-bold bg-primary/10 text-primary">
                            <Clock className="w-3 h-3" />
                            {order.status.replace('_', ' ')}
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="font-bold text-lg">${order.total_amount?.toFixed(2)}</p>
                          <p className="text-xs text-muted-foreground uppercase">{order.service_type}</p>
                        </div>
                      </div>

                      <div className="space-y-2 mb-4 bg-background/50 p-3 rounded-lg border border-primary/10">
                        <h4 className="text-xs font-bold uppercase text-muted-foreground mb-2 flex items-center gap-1">
                          <Utensils className="w-3 h-3" /> Items to Prepare
                        </h4>
                        {items.map((item, idx) => (
                          <div key={idx} className="flex justify-between text-sm">
                            <span className="font-medium"><span className="text-orange-500 mr-2">{item.quantity}x</span> {item.name}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <MerchantActionButtons orderId={order.id} currentStatus={order.status} />
                  </GlassCard>
                )
              })
            )}
          </div>
        )}

        {/* HISTORY TAB */}
        {activeTab === 'history' && (
          <div className="space-y-4">
            {historyOrders.length === 0 ? (
              <GlassCard className="p-12 text-center border-dashed border-primary/20">
                <History className="h-12 w-12 text-muted-foreground mx-auto mb-4 opacity-50" />
                <p className="font-semibold text-lg">No history yet</p>
              </GlassCard>
            ) : (
              <div className="grid gap-3">
                {historyOrders.map(order => (
                  <GlassCard key={order.id} className="p-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`p-2 rounded-full ${order.status === 'completed' ? 'bg-green-500/20 text-green-500' : 'bg-destructive/20 text-destructive'}`}>
                        {order.status === 'completed' ? <CheckCircle className="h-5 w-5" /> : <XCircle className="h-5 w-5" />}
                      </div>
                      <div>
                        <p className="font-bold">Order #{order.id.split('-')[0]}</p>
                        <p className="text-xs text-muted-foreground">{new Date(order.created_at).toLocaleString()}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-lg">${order.total_amount?.toFixed(2)}</p>
                      <p className="text-xs text-muted-foreground capitalize">{order.service_type}</p>
                    </div>
                  </GlassCard>
                ))}
              </div>
            )}
          </div>
        )}

        {/* SETTINGS TAB */}
        {activeTab === 'settings' && (
          <div className="max-w-md">
            <GlassCard className="p-6 space-y-6">
              <div>
                <h3 className="text-lg font-bold flex items-center gap-2 mb-1">
                  <Power className="w-5 h-5 text-primary" /> Store Master Switch
                </h3>
                <p className="text-sm text-muted-foreground mb-4">Temporarily pause incoming orders if your kitchen is too busy.</p>
                <Button 
                  size="lg" 
                  className={`w-full font-bold ${storeOpen ? 'bg-destructive hover:bg-destructive/90 text-white' : 'bg-green-600 hover:bg-green-700 text-white'}`}
                  onClick={() => setStoreOpen(!storeOpen)}
                >
                  {storeOpen ? 'Pause Incoming Orders' : 'Resume Accepting Orders'}
                </Button>
              </div>
            </GlassCard>
          </div>
        )}
      </div>
    </div>
  )
}
