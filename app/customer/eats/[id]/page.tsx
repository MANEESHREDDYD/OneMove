import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { EatsMenuClient } from './EatsMenuClient'

// Hardcoded mock data to simulate restaurant database
const MOCK_RESTAURANTS = {
  "rest-100": {
    name: "Burger Forge",
    menu: [
      { id: "item-1", name: "The Classic Forge Burger", description: "Double smash patty, American cheese, house sauce, brioche bun.", price: 12.99 },
      { id: "item-2", name: "Truffle Fries", description: "Crispy shoestring fries tossed in truffle oil and parmesan.", price: 6.99 },
      { id: "item-3", name: "Vanilla Bean Shake", description: "Hand-spun thick vanilla milkshake.", price: 5.49 },
    ]
  },
  "rest-101": {
    name: "Tokyo Sushi Express",
    menu: [
      { id: "item-4", name: "Spicy Tuna Roll", description: "Fresh tuna, spicy mayo, cucumber.", price: 8.99 },
      { id: "item-5", name: "Dragon Roll", description: "Eel, cucumber, topped with avocado and unagi sauce.", price: 14.99 },
      { id: "item-6", name: "Miso Soup", description: "Traditional miso broth with tofu and seaweed.", price: 3.99 },
    ]
  },
  "rest-102": {
    name: "Pizza Napoli",
    menu: [
      { id: "item-7", name: "Margherita Pizza", description: "San Marzano tomato sauce, fresh mozzarella, basil.", price: 16.99 },
      { id: "item-8", name: "Pepperoni Classic", description: "Crispy cup pepperoni, mozzarella, oregano.", price: 18.99 },
      { id: "item-9", name: "Garlic Knots", description: "Oven-baked dough knots with garlic butter and parmesan.", price: 5.99 },
    ]
  },
  "rest-103": {
    name: "Green Bowl Co.",
    menu: [
      { id: "item-10", name: "Quinoa Power Bowl", description: "Quinoa, roasted sweet potato, kale, tahini dressing.", price: 13.99 },
      { id: "item-11", name: "Avocado Toast", description: "Smashed avocado, chili flakes, sourdough.", price: 9.99 },
      { id: "item-12", name: "Green Detox Smoothie", description: "Spinach, apple, ginger, lemon.", price: 7.49 },
    ]
  }
}

export default async function EatsRestaurantPage({ params }: { params: { id: string } }) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  const restaurant = MOCK_RESTAURANTS[params.id as keyof typeof MOCK_RESTAURANTS]

  if (!restaurant) {
    redirect('/customer/eats')
  }

  return (
    <EatsMenuClient 
      restaurantId={params.id} 
      restaurantName={restaurant.name} 
      menu={restaurant.menu} 
    />
  )
}
