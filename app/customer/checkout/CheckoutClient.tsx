'use client'

import { useState, useEffect } from "react"
import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { Button } from "@/components/ui/button"
import { useRouter } from 'next/navigation'
import { useCartStore } from "@/store/cartStore"
import { CreditCard, Wallet, Coins, MapPin, Receipt, ArrowRight, Loader2 } from "lucide-react"
import { placeMarketplaceOrder } from "./actions"
import { generateIdempotencyKey } from "@/utils/idempotency"

export function CheckoutClient({ 
  userId, 
  userName,
  userPhone 
}: { 
  userId: string
  userName: string
  userPhone: string
}) {
  const router = useRouter()
  const cartStore = useCartStore()
  const [mounted, setMounted] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [paymentMethod, setPaymentMethod] = useState<'card' | 'wallet' | 'cash' | 'manual'>('card')
  const [address, setAddress] = useState("123 Demo Street, New York, NY")
  const [instructions, setInstructions] = useState("")
  const [tipAmount, setTipAmount] = useState(3.00)
  const [idempotencyKey, setIdempotencyKey] = useState<string>('')

   
  useEffect(() => {
    // Client-only initialization (mount flag + idempotency key) to avoid
    // hydration mismatch from a server-rendered random value.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true)
    setIdempotencyKey(generateIdempotencyKey())
  }, [])

  if (!mounted) return null;

  const items = cartStore.items;
  if (items.length === 0) {
    return (
      <div className="space-y-8 animate-in fade-in">
        <PageHeader title="Checkout" description="Your cart is empty" />
        <Button onClick={() => router.push('/customer')}>Back to Home</Button>
      </div>
    )
  }

  const merchantId = cartStore.getMerchantId()
  const serviceType = cartStore.getServiceType() || 'eats'
  const subtotal = cartStore.getSubtotal()
  
  const deliveryFee = 2.99
  const serviceFee = subtotal * 0.10 // 10%
  const smallOrderFee = subtotal < 10 ? 2.00 : 0
  const tax = subtotal * 0.08875 // NY tax roughly
  const total = subtotal + deliveryFee + serviceFee + smallOrderFee + tax + tipAmount

  const handlePlaceOrder = async () => {
    setIsSubmitting(true)
    setError(null)
    
    try {
      const res = await placeMarketplaceOrder({
        merchantId,
        serviceType,
        items,
        totalAmount: total,
        paymentMethod,
        address,
        instructions,
        idempotencyKey
      })
      
      if (res.error) {
        setError(res.error)
        setIsSubmitting(false)
      } else if (res.orderId) {
        cartStore.clearCart()
        router.push(`/customer/orders/${res.orderId}`)
      }
    } catch (err) {
      setError("An unexpected error occurred.")
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-6 pb-32 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-2xl mx-auto">
      <PageHeader 
        title="Checkout" 
        description="Review your order and complete payment"
      />

      {error && (
        <div className="p-4 bg-destructive/10 text-destructive border border-destructive/20 rounded-xl">
          {error}
        </div>
      )}

      {/* Delivery Details */}
      <GlassCard className="p-5 space-y-4">
        <h2 className="font-bold text-lg flex items-center gap-2">
          <MapPin className="w-5 h-5 text-primary" /> Delivery Details
        </h2>
        <div>
          <label className="text-sm text-muted-foreground mb-1 block">Delivery Address</label>
          <input 
            type="text" 
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            className="w-full bg-background/50 border border-primary/20 rounded-lg p-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
        </div>
        <div>
          <label className="text-sm text-muted-foreground mb-1 block">Instructions for Driver</label>
          <input 
            type="text" 
            placeholder="e.g. Leave at door, ring bell..."
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            className="w-full bg-background/50 border border-primary/20 rounded-lg p-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
        </div>
      </GlassCard>

      {/* Order Summary */}
      <GlassCard className="p-5 space-y-4">
        <h2 className="font-bold text-lg flex items-center gap-2">
          <Receipt className="w-5 h-5 text-primary" /> Order Summary
        </h2>
        <div className="space-y-3 divide-y divide-primary/10">
          {items.map(item => (
            <div key={item.id} className="flex justify-between items-start pt-3 first:pt-0 text-sm">
              <div className="flex gap-3">
                <span className="bg-primary/20 text-primary font-bold px-2 py-0.5 rounded-md h-fit">
                  {item.quantity}x
                </span>
                <span>{item.name}</span>
              </div>
              <span className="font-medium">${(item.price * item.quantity).toFixed(2)}</span>
            </div>
          ))}
        </div>
        
        <div className="pt-4 space-y-2 text-sm text-muted-foreground">
          <div className="flex justify-between">
            <span>Subtotal</span>
            <span>${subtotal.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span>Delivery Fee</span>
            <span>${deliveryFee.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span>Service Fee</span>
            <span>${serviceFee.toFixed(2)}</span>
          </div>
          {smallOrderFee > 0 && (
            <div className="flex justify-between text-orange-500">
              <span>Small Order Fee</span>
              <span>${smallOrderFee.toFixed(2)}</span>
            </div>
          )}
          <div className="flex justify-between">
            <span>Estimated Tax</span>
            <span>${tax.toFixed(2)}</span>
          </div>
        </div>

        {/* Tip Selector */}
        <div className="pt-4 border-t border-primary/10">
          <label className="text-sm font-medium mb-2 block">Driver Tip</label>
          <div className="flex gap-2">
            {[2, 3, 5, 10].map(tip => (
              <button
                key={tip}
                onClick={() => setTipAmount(tip)}
                className={`flex-1 py-2 rounded-lg text-sm font-bold border transition-colors ${
                  tipAmount === tip 
                    ? 'bg-primary text-primary-foreground border-primary' 
                    : 'bg-background/50 border-primary/20 hover:border-primary/50 text-foreground'
                }`}
              >
                ${tip}
              </button>
            ))}
          </div>
        </div>
      </GlassCard>

      {/* Payment Method */}
      <GlassCard className="p-5 space-y-4">
        <h2 className="font-bold text-lg">Payment Method</h2>
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={() => setPaymentMethod('card')}
            className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${
              paymentMethod === 'card' 
                ? 'bg-primary/10 border-primary text-primary ring-2 ring-primary/20' 
                : 'bg-background/50 border-primary/20 text-muted-foreground hover:border-primary/50'
            }`}
          >
            <CreditCard className="w-6 h-6" />
            <span className="text-sm font-medium">Mock Card</span>
          </button>
          
          <button
            onClick={() => setPaymentMethod('wallet')}
            className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${
              paymentMethod === 'wallet' 
                ? 'bg-primary/10 border-primary text-primary ring-2 ring-primary/20' 
                : 'bg-background/50 border-primary/20 text-muted-foreground hover:border-primary/50'
            }`}
          >
            <Wallet className="w-6 h-6" />
            <span className="text-sm font-medium">Demo Wallet</span>
          </button>
          
          <button
            onClick={() => setPaymentMethod('cash')}
            className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${
              paymentMethod === 'cash' 
                ? 'bg-primary/10 border-primary text-primary ring-2 ring-primary/20' 
                : 'bg-background/50 border-primary/20 text-muted-foreground hover:border-primary/50'
            }`}
          >
            <Coins className="w-6 h-6" />
            <span className="text-sm font-medium">Cash</span>
          </button>
          <button
            onClick={() => setPaymentMethod('manual')}
            className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${
              paymentMethod === 'manual' 
                ? 'bg-primary/10 border-primary text-primary ring-2 ring-primary/20' 
                : 'bg-background/50 border-primary/20 text-muted-foreground hover:border-primary/50'
            }`}
          >
            <Receipt className="w-6 h-6" />
            <span className="text-sm font-medium">Manual Pay</span>
          </button>
        </div>
      </GlassCard>

      {/* Action Bar */}
      <div className="fixed bottom-0 left-0 right-0 p-4 z-50 bg-background/80 backdrop-blur-xl border-t border-primary/20">
        <div className="max-w-2xl mx-auto flex items-center gap-6">
          <div className="flex-1">
            <p className="text-sm text-muted-foreground uppercase tracking-wider font-bold mb-1">Total</p>
            <p className="text-3xl font-black">${total.toFixed(2)}</p>
          </div>
          <Button 
            size="lg" 
            className="flex-1 h-14 font-bold text-lg shadow-xl shadow-primary/20 group"
            onClick={handlePlaceOrder}
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Processing...</>
            ) : (
              <>Place Order <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" /></>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
