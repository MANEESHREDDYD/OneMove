'use client'

import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { Button } from "@/components/ui/button"
import { Plus, Minus, ShoppingCart } from "lucide-react"
import { useRouter } from 'next/navigation'
import { useCartStore } from "@/store/cartStore"
import { useEffect, useState } from "react"

interface MenuItem {
  id: string
  name: string
  description: string
  price: number
  image_url?: string
}

export function EatsMenuClient({ 
  restaurantId, 
  restaurantName, 
  menu 
}: { 
  restaurantId: string
  restaurantName: string
  menu: MenuItem[] 
}) {
  const router = useRouter()
  const cartStore = useCartStore()
  // Hydration fix for Zustand
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  const handleCheckout = () => {
    router.push('/customer/checkout')
  }

  if (!mounted) return null;

  // Only consider items from THIS restaurant
  const isDiffMerchant = cartStore.getMerchantId() !== null && cartStore.getMerchantId() !== restaurantId;
  const items = cartStore.items.filter(i => i.merchant_id === restaurantId);
  const subtotal = items.reduce((sum, i) => sum + (i.price * i.quantity), 0);

  return (
    <div className="space-y-8 pb-32 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader 
        title={restaurantName} 
        description="Select items to add to your order"
      />

      {isDiffMerchant && (
        <div className="p-3 bg-destructive/10 text-destructive text-sm rounded-lg">
          You have items from another store in your cart. Adding an item here will clear your existing cart.
        </div>
      )}

      <div className="grid gap-4">
        {menu.map(item => {
          const cartItem = items.find(i => i.id === item.id);
          const quantity = cartItem?.quantity || 0;

          return (
            <GlassCard key={item.id} className="p-4 flex justify-between items-center group hover:bg-white/5 transition-colors">
              <div className="pr-4">
                <h3 className="font-bold text-base">{item.name}</h3>
                <p className="text-sm text-muted-foreground line-clamp-2">{item.description}</p>
                <p className="font-semibold mt-1">${item.price.toFixed(2)}</p>
              </div>
              
              <div className="flex items-center gap-3 bg-primary/10 rounded-full p-1 border border-primary/20 shrink-0">
                {quantity > 0 ? (
                  <>
                    <button 
                      onClick={() => cartStore.updateQuantity(item.id, -1)}
                      className="h-8 w-8 rounded-full bg-background flex items-center justify-center hover:bg-destructive hover:text-destructive-foreground transition-colors"
                    >
                      <Minus className="h-4 w-4" />
                    </button>
                    <span className="font-bold w-4 text-center">{quantity}</span>
                  </>
                ) : null}
                <button 
                  onClick={() => cartStore.addItem({...item, merchant_id: restaurantId, service_type: 'eats'})}
                  className="h-8 w-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/80 transition-colors"
                >
                  <Plus className="h-4 w-4" />
                </button>
              </div>
            </GlassCard>
          )
        })}
      </div>

      {/* Floating Checkout Bar */}
      {items.length > 0 && (
        <div className="fixed bottom-20 left-0 right-0 p-4 z-50 animate-in slide-in-from-bottom-10">
          <div className="max-w-2xl mx-auto">
            <GlassCard className="p-4 flex justify-between items-center border-primary/30 shadow-2xl bg-background/95 backdrop-blur-xl">
              <div>
                <p className="text-sm text-muted-foreground">{items.length} items</p>
                <p className="text-xl font-black">${subtotal.toFixed(2)}</p>
              </div>
              <Button 
                size="lg" 
                className="font-bold h-12 px-8"
                onClick={handleCheckout}
              >
                <ShoppingCart className="w-5 h-5 mr-2" />
                Go to Checkout
              </Button>
            </GlassCard>
          </div>
        </div>
      )}
    </div>
  )
}
