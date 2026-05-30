import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { SetupRequired } from "@/components/common/SetupRequired"
import { GroceryCartClient } from './GroceryCartClient'

const MOCK_GROCERY_INVENTORY = {
  "groc-200": {
    name: "Fresh Market Plus",
    inventory: [
      { id: "g-1", name: "Organic Honeycrisp Apples", category: "Produce", price: 1.25, unit: "ea" },
      { id: "g-2", name: "Hass Avocados", category: "Produce", price: 2.50, unit: "ea" },
      { id: "g-3", name: "Cage-Free Large Eggs", category: "Dairy & Eggs", price: 5.99, unit: "doz" },
      { id: "g-4", name: "Whole Milk", category: "Dairy & Eggs", price: 4.49, unit: "gal" },
      { id: "g-5", name: "Sourdough Loaf", category: "Bakery", price: 6.99, unit: "loaf" },
      { id: "g-6", name: "Ground Turkey (93/7)", category: "Meat", price: 7.99, unit: "lb" },
    ]
  },
  "groc-201": {
    name: "City Supermarket",
    inventory: [
      { id: "g-7", name: "Bananas", category: "Produce", price: 0.50, unit: "lb" },
      { id: "g-8", name: "Chicken Breast", category: "Meat", price: 4.99, unit: "lb" },
      { id: "g-9", name: "Cheddar Cheese Block", category: "Dairy", price: 3.99, unit: "ea" },
      { id: "g-10", name: "White Bread", category: "Bakery", price: 2.49, unit: "loaf" },
      { id: "g-11", name: "Bottled Water (24 pk)", category: "Beverages", price: 5.99, unit: "case" },
    ]
  },
  "groc-202": {
    name: "Corner Deli & Mart",
    inventory: [
      { id: "g-12", name: "Potato Chips", category: "Snacks", price: 2.99, unit: "bag" },
      { id: "g-13", name: "Cola (2L)", category: "Beverages", price: 2.49, unit: "btl" },
      { id: "g-14", name: "Ice Cream Pint", category: "Frozen", price: 5.49, unit: "pint" },
      { id: "g-15", name: "Paper Towels", category: "Household", price: 3.49, unit: "roll" },
    ]
  }
}

export default async function GroceryStorePage({ params }: { params: { id: string } }) {
  const supabase = await createClient()
  if (!supabase) {
    return <SetupRequired />
  }
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  const store = MOCK_GROCERY_INVENTORY[params.id as keyof typeof MOCK_GROCERY_INVENTORY]

  if (!store) {
    redirect('/customer/grocery')
  }

  return (
    <GroceryCartClient 
      storeId={params.id} 
      storeName={store.name} 
      inventory={store.inventory} 
    />
  )
}
