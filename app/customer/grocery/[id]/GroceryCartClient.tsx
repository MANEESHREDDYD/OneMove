'use client'

import { useState } from 'react'
import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { Button } from "@/components/ui/button"
import { Plus, Minus, ShoppingCart, AlertCircle, Search } from "lucide-react"
import { placeGroceryOrder } from './actions'
import { useRouter } from 'next/navigation'

interface GroceryItem {
  id: string
  name: string
  category: string
  price: number
  unit: string
}

interface CartItem extends GroceryItem {
  quantity: number
}

export function GroceryCartClient({ 
  storeId, 
  storeName, 
  inventory 
}: { 
  storeId: string
  storeName: string
  inventory: GroceryItem[] 
}) {
  const [cart, setCart] = useState<CartItem[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [isCheckingOut, setIsCheckingOut] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  const addToCart = (item: GroceryItem) => {
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
  const fee = subtotal > 0 ? 5.99 : 0
  const total = subtotal + fee

  const filteredInventory = inventory.filter(item => 
    item.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
    item.category.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // Group by category for nicer UI
  const categories = Array.from(new Set(filteredInventory.map(i => i.category)))

  async function handleCheckout() {
    if (cart.length === 0) return
    setIsCheckingOut(true)
    setError(null)
    
    const res = await placeGroceryOrder(storeId, storeName, cart, total)
    if (res.error) {
      setError(res.error)
      setIsCheckingOut(false)
    } else if (res.success) {
      router.push(`/customer/orders/${res.orderId}`)
    }
  }

  return (
    <div className="space-y-6 pb-32 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader 
        title={storeName} 
        description="Aisles of fresh ingredients"
      />

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
        <input 
          type="text" 
          placeholder="Search items or categories..." 
          className="w-full bg-background/50 border border-primary/20 rounded-xl py-3 pl-10 pr-4 focus:outline-none focus:ring-2 focus:ring-primary/50 text-foreground"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      <div className="space-y-8">
        {categories.map(category => (
          <div key={category} className="space-y-3">
            <h2 className="text-lg font-bold tracking-tight border-b border-primary/10 pb-2">{category}</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {filteredInventory.filter(i => i.category === category).map(item => (
                <GlassCard key={item.id} className="p-3 flex justify-between items-center group">
                  <div className="pr-4">
                    <h3 className="font-semibold text-sm">{item.name}</h3>
                    <p className="text-xs text-muted-foreground mb-1">per {item.unit}</p>
                    <p className="font-bold">${item.price.toFixed(2)}</p>
                  </div>
                  
                  <div className="flex flex-col items-center gap-2 bg-primary/5 rounded-lg p-1 border border-primary/10 shrink-0">
                    <button 
                      onClick={() => addToCart(item)}
                      className="h-7 w-7 rounded bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/80 transition-colors"
                    >
                      <Plus className="h-4 w-4" />
                    </button>
                    {getQuantity(item.id) > 0 && (
                      <>
                        <span className="font-bold text-sm w-full text-center">{getQuantity(item.id)}</span>
                        <button 
                          onClick={() => removeFromCart(item.id)}
                          className="h-7 w-7 rounded bg-background flex items-center justify-center hover:bg-destructive hover:text-destructive-foreground transition-colors"
                        >
                          <Minus className="h-4 w-4" />
                        </button>
                      </>
                    )}
                  </div>
                </GlassCard>
              ))}
            </div>
          </div>
        ))}
        {categories.length === 0 && (
          <div className="text-center py-10 text-muted-foreground">
            No items found matching &quot;{searchQuery}&quot;.
          </div>
        )}
      </div>

      {/* Floating Checkout Bar */}
      {cart.length > 0 && (
        <div className="fixed bottom-20 left-0 right-0 p-4 z-50 animate-in slide-in-from-bottom-10">
          <div className="max-w-2xl mx-auto">
            <GlassCard className="p-4 flex flex-col gap-3 border-green-500/30 shadow-2xl bg-background/95 backdrop-blur-xl ring-1 ring-green-500/20">
              {error && (
                <div className="p-2 bg-destructive/10 border border-destructive text-destructive rounded-lg flex items-start gap-2 text-xs">
                  <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                  <p>{error}</p>
                </div>
              )}
              <div className="flex justify-between items-end mb-2">
                <div>
                  <p className="text-sm text-muted-foreground"><span className="font-bold text-foreground">{cart.reduce((s, i) => s + i.quantity, 0)}</span> items</p>
                  <p className="text-xs text-muted-foreground">Delivery fee: ${fee.toFixed(2)}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs font-bold text-green-500 uppercase tracking-wider mb-1">Grocery Total</p>
                  <p className="text-2xl font-black">${total.toFixed(2)}</p>
                </div>
              </div>
              <Button 
                size="lg" 
                className="w-full font-bold text-lg h-14 bg-green-600 hover:bg-green-700 text-white"
                onClick={handleCheckout}
                disabled={isCheckingOut}
              >
                <ShoppingCart className="w-5 h-5 mr-2" />
                {isCheckingOut ? 'Securing Order...' : 'Checkout Groceries'}
              </Button>
            </GlassCard>
          </div>
        </div>
      )}
    </div>
  )
}
