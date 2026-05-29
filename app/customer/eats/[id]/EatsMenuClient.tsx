'use client'

import { useState } from 'react'
import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { Button } from "@/components/ui/button"
import { Plus, Minus, ShoppingCart, AlertCircle } from "lucide-react"
import { placeEatsOrder } from './actions'
import { useRouter } from 'next/navigation'

interface MenuItem {
  id: string
  name: string
  description: string
  price: number
}

interface CartItem extends MenuItem {
  quantity: number
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
  const [cart, setCart] = useState<CartItem[]>([])
  const [isCheckingOut, setIsCheckingOut] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  const addToCart = (item: MenuItem) => {
    setCart(prev => {
      const existing = prev.find(i => i.id === item.id)
      if (existing) {
        return prev.map(i => i.id === item.id ? { ...i, quantity: i.quantity + 1 } : i)
      }
      return [...prev, { ...item, quantity: 1 }]
    })
  }

  const removeFromCart = (itemId: string) => {
    setCart(prev => {
      const existing = prev.find(i => i.id === itemId)
      if (existing && existing.quantity > 1) {
        return prev.map(i => i.id === itemId ? { ...i, quantity: i.quantity - 1 } : i)
      }
      return prev.filter(i => i.id !== itemId)
    })
  }

  const getQuantity = (itemId: string) => cart.find(i => i.id === itemId)?.quantity || 0

  const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0)
  const fee = subtotal > 0 ? 2.99 : 0
  const total = subtotal + fee

  async function handleCheckout() {
    if (cart.length === 0) return
    setIsCheckingOut(true)
    setError(null)
    
    const res = await placeEatsOrder(restaurantId, restaurantName, cart, total)
    if (res.error) {
      setError(res.error)
      setIsCheckingOut(false)
    } else if (res.success) {
      router.push(`/customer/orders/${res.orderId}`)
    }
  }

  return (
    <div className="space-y-8 pb-32 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader 
        title={restaurantName} 
        description="Select items to add to your order"
      />

      <div className="grid gap-4">
        {menu.map(item => (
          <GlassCard key={item.id} className="p-4 flex justify-between items-center group hover:bg-white/5 transition-colors">
            <div className="pr-4">
              <h3 className="font-bold text-base">{item.name}</h3>
              <p className="text-sm text-muted-foreground line-clamp-2">{item.description}</p>
              <p className="font-semibold mt-1">${item.price.toFixed(2)}</p>
            </div>
            
            <div className="flex items-center gap-3 bg-primary/10 rounded-full p-1 border border-primary/20 shrink-0">
              {getQuantity(item.id) > 0 ? (
                <>
                  <button 
                    onClick={() => removeFromCart(item.id)}
                    className="h-8 w-8 rounded-full bg-background flex items-center justify-center hover:bg-destructive hover:text-destructive-foreground transition-colors"
                  >
                    <Minus className="h-4 w-4" />
                  </button>
                  <span className="font-bold w-4 text-center">{getQuantity(item.id)}</span>
                </>
              ) : null}
              <button 
                onClick={() => addToCart(item)}
                className="h-8 w-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/80 transition-colors"
              >
                <Plus className="h-4 w-4" />
              </button>
            </div>
          </GlassCard>
        ))}
      </div>

      {/* Floating Checkout Bar */}
      {cart.length > 0 && (
        <div className="fixed bottom-20 left-0 right-0 p-4 z-50 animate-in slide-in-from-bottom-10">
          <div className="max-w-2xl mx-auto">
            <GlassCard className="p-4 flex flex-col gap-3 border-primary/30 shadow-2xl bg-background/95 backdrop-blur-xl">
              {error && (
                <div className="p-2 bg-destructive/10 border border-destructive text-destructive rounded-lg flex items-start gap-2 text-xs">
                  <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                  <p>{error}</p>
                </div>
              )}
              <div className="flex justify-between items-end mb-2">
                <div>
                  <p className="text-sm text-muted-foreground">Subtotal: ${subtotal.toFixed(2)}</p>
                  <p className="text-sm text-muted-foreground">Fee: ${fee.toFixed(2)}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs font-bold text-primary uppercase tracking-wider mb-1">Total</p>
                  <p className="text-2xl font-black">${total.toFixed(2)}</p>
                </div>
              </div>
              <Button 
                size="lg" 
                className="w-full font-bold text-lg h-14"
                onClick={handleCheckout}
                disabled={isCheckingOut}
              >
                <ShoppingCart className="w-5 h-5 mr-2" />
                {isCheckingOut ? 'Processing Order...' : 'Checkout'}
              </Button>
            </GlassCard>
          </div>
        </div>
      )}
    </div>
  )
}
