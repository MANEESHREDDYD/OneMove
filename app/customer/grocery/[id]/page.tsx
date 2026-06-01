import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { SetupRequired } from "@/components/common/SetupRequired"
import { GroceryCartClient } from './GroceryCartClient'

export const dynamic = "force-dynamic";

export default async function GroceryStorePage({ params }: { params: Promise<{ id: string }> }) {
  const supabase = await createClient()
  if (!supabase) {
    return <SetupRequired />
  }

  const resolvedParams = await params;

  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  const { data: merchant, error: merchError } = await supabase
    .from('merchants')
    .select('*')
    .eq('id', resolvedParams.id)
    .single()

  if (merchError || !merchant) {
    redirect('/customer/grocery')
  }

  const { data: products } = await supabase
    .from('products')
    .select('*')
    .eq('merchant_id', merchant.id)

  const inventory = products?.map(p => ({
    id: p.id,
    name: p.name,
    category: p.category || 'General',
    price: Number(p.price),
    unit: 'ea' // placeholder for demo
  })) || []

  return (
    <>
      {inventory.length === 0 && process.env.NODE_ENV === 'development' && (
        <div className="p-4 bg-destructive/20 text-destructive rounded-lg mb-4">
          No products found for merchant_id = {merchant.id}
        </div>
      )}
      <GroceryCartClient 
        storeId={merchant.id} 
        storeName={merchant.name} 
        inventory={inventory} 
      />
    </>
  )
}
