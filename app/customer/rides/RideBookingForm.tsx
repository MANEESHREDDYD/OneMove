'use client'

import { useState } from 'react'
import { GlassCard } from '@/components/common/GlassCard'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { MapPin, Navigation, Car, Crown, AlertCircle } from 'lucide-react'
import { requestRide } from './actions'
import { calculateRideEstimate } from '@/utils/pricing'

export function RideBookingForm() {
  const [pickup, setPickup] = useState('')
  const [dropoff, setDropoff] = useState('')
  const [selectedClass, setSelectedClass] = useState<'economy' | 'premium'>('economy')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Compute dynamically during render
  const estimate = (pickup.trim().length > 3 && dropoff.trim().length > 3) 
    ? calculateRideEstimate(pickup, dropoff) 
    : null

  async function handleAction(formData: FormData) {
    if (!estimate) return
    setError(null)
    setLoading(true)
    
    try {
      const result = await requestRide(formData)
      // The action either redirects on success or returns an error object
      if (result?.error) {
        setError(result.error)
      }
    } catch (err) {
      console.error(err)
      setError('An unexpected error occurred while booking your ride. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid lg:grid-cols-2 gap-8 h-[calc(100vh-12rem)]">
      {/* Map Placeholder */}
      <GlassCard className="relative overflow-hidden hidden lg:flex flex-col items-center justify-center bg-primary/5 border border-primary/20 shadow-[0_0_40px_-15px_rgba(255,255,255,0.1)]">
        <div className="absolute inset-0 bg-[url('https://maps.gstatic.com/mapfiles/transparent.png')] opacity-10 bg-repeat" />
        <div className="relative z-10 flex flex-col items-center p-8 bg-background/80 backdrop-blur-md rounded-2xl border text-center">
          <MapPin className="h-12 w-12 text-primary animate-bounce mb-4 drop-shadow-lg" />
          <h3 className="font-bold text-xl mb-2">Live Map Interface</h3>
          <p className="text-muted-foreground font-medium max-w-[250px]">
            Map preview rendering is mocked in this MVP build.
          </p>
          {estimate && (
            <div className="mt-4 px-4 py-2 bg-primary/20 text-primary rounded-full text-sm font-bold flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
              </span>
              Routing: {estimate.distanceMiles} mi • {estimate.durationMinutes} min
            </div>
          )}
        </div>
      </GlassCard>

      {/* Booking Form */}
      <div className="flex flex-col h-full overflow-hidden">
        <GlassCard className="p-6 flex-1 flex flex-col relative">
          <form action={handleAction} className="flex-1 flex flex-col">
            <div className="space-y-4 mb-8">
              <div className="space-y-2">
                <Label htmlFor="pickup">Pickup Location</Label>
                <div className="relative">
                  <MapPin className="absolute left-3 top-3 h-4 w-4 text-primary" />
                  <Input 
                    id="pickup" 
                    name="pickup"
                    className="pl-9 bg-background/50 h-12" 
                    placeholder="Enter pickup address" 
                    value={pickup}
                    onChange={(e) => {
                      setPickup(e.target.value)
                      setError(null)
                    }}
                    required 
                    autoComplete="off"
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
                    className="pl-9 bg-background/50 h-12" 
                    placeholder="Enter destination" 
                    value={dropoff}
                    onChange={(e) => {
                      setDropoff(e.target.value)
                      setError(null)
                    }}
                    required 
                    autoComplete="off"
                  />
                </div>
              </div>
            </div>

            {error && (
              <div className="mb-4 p-3 bg-destructive/10 border border-destructive text-destructive rounded-lg flex items-start gap-2 text-sm animate-in fade-in">
                <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                <p>{error}</p>
              </div>
            )}

            {/* Vehicle Selection & Estimate */}
            <div className="flex-1 relative">
              {estimate ? (
                <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4">
                  <h3 className="font-semibold text-lg">Select a Ride</h3>
                  
                  <div className="grid gap-3">
                    <input type="hidden" name="serviceClass" value={selectedClass} />
                    
                    {/* Economy */}
                    <div 
                      onClick={() => setSelectedClass('economy')}
                      className={`p-4 rounded-xl border-2 cursor-pointer transition-all flex items-center justify-between ${selectedClass === 'economy' ? 'border-primary bg-primary/10 scale-[1.02]' : 'border-transparent bg-white/5 hover:bg-white/10'}`}
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
                      className={`p-4 rounded-xl border-2 cursor-pointer transition-all flex items-center justify-between ${selectedClass === 'premium' ? 'border-primary bg-primary/10 scale-[1.02]' : 'border-transparent bg-white/5 hover:bg-white/10'}`}
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
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-6 text-muted-foreground border-2 border-dashed rounded-xl border-white/10">
                  <Navigation className="h-8 w-8 mb-4 opacity-50" />
                  <p>Enter your pickup and dropoff locations to see live estimates.</p>
                </div>
              )}
            </div>

            <div className="mt-6 pt-6 border-t border-white/10">
              <Button 
                type="submit" 
                size="lg" 
                className="w-full text-lg h-14 rounded-xl relative overflow-hidden transition-all"
                disabled={!estimate || loading}
              >
                <span className={`transition-opacity duration-200 ${loading ? 'opacity-0' : 'opacity-100'}`}>
                  {estimate ? `Confirm ${selectedClass === 'economy' ? 'Economy' : 'Premium'}` : 'Enter Destination'}
                </span>
                {loading && (
                  <div className="absolute inset-0 flex items-center justify-center bg-primary">
                    <span className="flex items-center gap-2">
                      <span className="h-4 w-4 border-2 border-white/20 border-t-white rounded-full animate-spin"></span>
                      Booking...
                    </span>
                  </div>
                )}
              </Button>
            </div>
          </form>
        </GlassCard>
      </div>
    </div>
  )
}
