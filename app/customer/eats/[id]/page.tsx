import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { SetupRequired } from "@/components/common/SetupRequired"
import { EatsMenuClient } from './EatsMenuClient'

export const dynamic = "force-dynamic";

export default async function EatsRestaurantPage({ params }: { params: { id: string } }) {
  const supabase = await createClient()
  if (!supabase) {
    return <SetupRequired />
  }
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  const { data: merchant, error: merchError } = await supabase
    .from('merchants')
    .select('*')
    .eq('id', params.id)
    .single()

  if (merchError || !merchant) {
    redirect('/customer/eats')
  }

  const { data: products } = await supabase
    .from('products')
    .select('*')
    .eq('merchant_id', merchant.id)

  const menuItems = products?.map(p => ({
    id: p.id,
    name: p.name,
    description: p.description,
    price: Number(p.price)
  })) || []

  return (
    <EatsMenuClient 
      restaurantId={merchant.id} 
      restaurantName={merchant.name} 
      menu={menuItems} 
    />
  )
}
