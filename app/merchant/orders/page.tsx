import { PageHeader } from "@/components/common/PageHeader"
import { createClient } from "@/utils/supabase/server"
import { SetupRequired } from "@/components/common/SetupRequired"
import { redirect } from "next/navigation"
import { OrdersClient } from "./OrdersClient"

export const dynamic = "force-dynamic"

export default async function OrderHistoryPage() {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />

  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/auth/login')

  const { data: merchants } = await supabase
    .from('merchants')
    .select('id')
    .eq('owner_id', user.id)

  const merchantIds = merchants?.map(m => m.id) || []

  let orders: any[] = []
  if (merchantIds.length > 0) {
    const { data } = await supabase
      .from('orders')
      .select('*')
      .in('merchant_id', merchantIds)
      .in('status', ['pending', 'accepted', 'preparing', 'ready', 'in_transit'])
      .order('created_at', { ascending: false })
    orders = data || []
  }

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader 
        title="Live Orders" 
        description="Manage incoming orders for your store"
      />
      <OrdersClient orders={orders} />
    </div>
  )
}
