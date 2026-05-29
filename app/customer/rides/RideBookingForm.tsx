'use client'

import { useState } from 'react'
import { GlassCard } from '@/components/common/GlassCard'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { MapPin, Navigation, Car, Crown } from 'lucide-react'
import { requestRide } from './actions'
import { calculateRideEstimate } from '@/utils/pricing'

export function RideBookingForm() {
  const [pickup, setPickup] = useState('')
  const [dropoff, setDropoff] = useState('')
  const [selectedClass, setSelectedClass] = useState<'economy' | 'premium'>('economy')
  const [loading, setLoading] = useState(false)

  // Compute dynamically during render
  const estimate = (pickup.length > 3 && dropoff.length > 3) 
    ? calculateRideEstimate(pickup, dropoff) 
    : null

  async function handleAction(formData: FormData) {
    setLoading(true)
    try {
      await requestRide(formData)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid lg:grid-cols-2 gap-8 h-[calc(100vh-12rem)]">
      {/* Map Placeholder */}
      <GlassCard className="relative overflow-hidden hidden lg:flex flex-col items-center justify-center bg-primary/5">
        <div className="absolute inset-0 bg-[url('https://maps.gstatic.com/mapfiles/transparent.png')] opacity-10 bg-repeat" />
        <MapPin className="h-12 w-12 text-primary animate-bounce mb-4" />
        <p className="text-muted-foreground font-medium z-10">Live Map View Unavailable in MVP</p>
      </GlassCard>

      {/* Booking Form */}
      <div className="flex flex-col h-full overflow-hidden">
        <GlassCard className="p-6 flex-1 flex flex-col">
          <form action={handleAction} className="flex-1 flex flex-col">
            <div className="space-y-4 mb-8">
              <div className="space-y-2">
                <Label htmlFor="pickup">Pickup Location</Label>
                <div className="relative">
                  <MapPin className="absolute left-3 top-3 h-4 w-4 text-primary" />
                  <Input 
                    id="pickup" 
                    name="pickup"
                    className="pl-9 bg-background/50" 
                    placeholder="Where are you?" 
                    value={pickup}
                    onChange={(e) => setPickup(e.target.value)}
                    required 
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="dropoff">Dropoff Location</Label>
                <div className="relative">
                  <Navigation className="absolute left-3 top-3 h-4 w-4 text-destructive" />
                  <Input 
                    id="dropoff" 
                    name="dropoff"
                    className="pl-9 bg-background/50" 
                    placeholder="Where to?" 
                    value={dropoff}
                    onChange={(e) => setDropoff(e.target.value)}
                    required 
                  />
                </div>
              </div>
            </div>

            {/* Vehicle Selection & Estimate */}
            {estimate && (
              <div className="flex-1 space-y-4 animate-in fade-in slide-in-from-bottom-4">
                <h3 className="font-semibold text-lg">Select a Ride</h3>
                
                <div className="grid gap-3">
                  <input type="hidden" name="serviceClass" value={selectedClass} />
                  
                  {/* Economy */}
                  <div 
                    onClick={() => setSelectedClass('economy')}
                    className={`p-4 rounded-xl border-2 cursor-pointer transition-all flex items-center justify-between ${selectedClass === 'economy' ? 'border-primary bg-primary/10' : 'border-transparent bg-white/5 hover:bg-white/10'}`}
                  >
                    <div className="flex items-center gap-4">
                      <div className="bg-primary/20 p-2 rounded-full"><Car className="h-6 w-6 text-primary" /></div>
                      <div>
                        <p className="font-bold">OneMove Economy</p>
                        <p className="text-xs text-muted-foreground">{estimate.durationMinutes} mins away • 1-4 seats</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-lg">${estimate.prices.economy.toFixed(2)}</p>
                    </div>
                  </div>

                  {/* Premium */}
                  <div 
                    onClick={() => setSelectedClass('premium')}
                    className={`p-4 rounded-xl border-2 cursor-pointer transition-all flex items-center justify-between ${selectedClass === 'premium' ? 'border-primary bg-primary/10' : 'border-transparent bg-white/5 hover:bg-white/10'}`}
                  >
                    <div className="flex items-center gap-4">
                      <div className="bg-purple-500/20 p-2 rounded-full"><Crown className="h-6 w-6 text-purple-500" /></div>
                      <div>
                        <p className="font-bold">OneMove Premium</p>
                        <p className="text-xs text-muted-foreground">{estimate.durationMinutes + 2} mins away • Luxury</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-lg">${estimate.prices.premium.toFixed(2)}</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div className="mt-auto pt-6">
              <Button 
                type="submit" 
                size="lg" 
                className="w-full text-lg h-14 rounded-xl"
                disabled={!estimate || loading}
              >
                {loading ? 'Requesting...' : (estimate ? 'Confirm Ride' : 'Enter Destination')}
              </Button>
            </div>
          </form>
        </GlassCard>
      </div>
    </div>
  )
}
