'use client'

import { useState } from 'react'
import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { Button } from "@/components/ui/button"
import { AlertCircle, Package, MapPin, Truck } from "lucide-react"
import { requestCourierOrder } from './actions'
import { useRouter } from 'next/navigation'

export function CourierFormClient() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  async function handleSubmit(formData: FormData) {
    setLoading(true)
    setError(null)

    const res = await requestCourierOrder(formData)

    if (res.error) {
      setError(res.error)
      setLoading(false)
    } else if (res.success) {
      router.push(`/customer/orders/${res.orderId}`)
    }
  }

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader
        title="Send a Package"
        description="Fast, secure peer-to-peer courier service."
      />

      <GlassCard className="p-6">
        <form action={handleSubmit} className="space-y-6">
          {/*
            Submission failure is announced (role="alert") and is also wired to
            the two address fields via aria-describedby / aria-invalid below, so
            a user who tabs back into the form hears why it was rejected instead
            of finding a silently unchanged form.
          */}
          {error && (
            <div id="courier-form-error" role="alert" className="p-3 bg-destructive/10 border border-destructive text-destructive rounded-lg flex items-start gap-2 text-sm">
              <AlertCircle aria-hidden="true" focusable="false" className="h-5 w-5 shrink-0" />
              <p>{error}</p>
            </div>
          )}

          <div className="space-y-4 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-primary/20 before:to-transparent">
            {/* Pickup */}
            <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
              <div aria-hidden="true" className="flex items-center justify-center w-10 h-10 rounded-full border border-primary/30 bg-background text-primary shrink-0 z-10 shadow-lg">
                <MapPin className="h-5 w-5" />
              </div>
              <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] pl-4 md:pl-0 md:pr-4">
                <label htmlFor="courier-pickup" className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1 block">Pickup Address</label>
                <input
                  id="courier-pickup"
                  type="text"
                  name="pickupAddress"
                  autoComplete="street-address"
                  placeholder="Where should we pick it up?"
                  aria-invalid={error ? true : undefined}
                  aria-describedby={error ? 'courier-form-error' : undefined}
                  className="w-full bg-background/50 border border-primary/20 rounded-xl py-3 px-4 focus:outline-none focus:ring-2 focus:ring-primary/50 text-foreground"
                  required
                />
              </div>
            </div>

            {/* Dropoff */}
            <div className="relative flex items-center justify-between md:justify-normal group is-active">
              <div aria-hidden="true" className="flex items-center justify-center w-10 h-10 rounded-full border border-primary/30 bg-primary/10 text-primary shrink-0 z-10 shadow-lg">
                <Truck className="h-5 w-5" />
              </div>
              <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] pl-4">
                <label htmlFor="courier-dropoff" className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1 block">Dropoff Address</label>
                <input
                  id="courier-dropoff"
                  type="text"
                  name="dropoffAddress"
                  autoComplete="street-address"
                  placeholder="Where is it going?"
                  aria-invalid={error ? true : undefined}
                  aria-describedby={error ? 'courier-form-error' : undefined}
                  className="w-full bg-background/50 border border-primary/20 rounded-xl py-3 px-4 focus:outline-none focus:ring-2 focus:ring-primary/50 text-foreground"
                  required
                />
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-primary/10 space-y-4">
            <h2 className="font-bold flex items-center gap-2">
              <Package className="h-5 w-5 text-primary" />
              Package Details
            </h2>

            {/*
              The radios were a bare grid of labels. A radio group needs a group
              name of its own, otherwise each option announces in isolation with
              no indication of what is being chosen.
            */}
            <fieldset className="border-0 p-0 m-0">
              <legend className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">Package size</legend>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {['Small', 'Medium', 'Large', 'Extra Large'].map(size => (
                <label key={size} className="cursor-pointer">
                  <input type="radio" name="packageSize" value={size} className="peer sr-only focus-visible:outline focus-visible:outline-2" required defaultChecked={size === 'Small'} />
                  <div className="p-4 rounded-xl border border-primary/20 bg-background/50 text-center hover:bg-primary/5 peer-checked:bg-primary/10 peer-checked:border-primary peer-checked:ring-1 peer-checked:ring-primary transition-all">
                    <span className="block font-bold text-sm">{size}</span>
                    <span className="block text-xs text-muted-foreground mt-1">
                      {size === 'Small' && 'Keys, Documents'}
                      {size === 'Medium' && 'Shoebox size'}
                      {size === 'Large' && 'Microwave size'}
                      {size === 'Extra Large' && 'Furniture piece'}
                    </span>
                  </div>
                </label>
              ))}
              </div>
            </fieldset>

            <div>
               <label htmlFor="courier-details" className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1 block">Description &amp; Instructions (Optional)</label>
               <textarea
                  id="courier-details"
                  name="packageDetails"
                  placeholder="e.g. Fragile glass inside, leave at front desk."
                  className="w-full bg-background/50 border border-primary/20 rounded-xl py-3 px-4 focus:outline-none focus:ring-2 focus:ring-primary/50 text-foreground min-h-[100px] resize-none"
               />
            </div>
          </div>

          <Button
            type="submit"
            className="w-full h-14 text-lg font-bold"
            disabled={loading}
          >
            {loading ? 'Calculating Route...' : 'Request Courier'}
          </Button>
          {/* Announces the in-flight state, which is otherwise only visible as button text. */}
          <div role="status" aria-live="polite" className="sr-only">
            {loading ? 'Calculating route. Submitting your courier request.' : ''}
          </div>
        </form>
      </GlassCard>
    </div>
  )
}
