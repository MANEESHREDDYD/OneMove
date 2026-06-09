'use client'

import { useState, useEffect } from 'react'
import { GlassCard } from '@/components/common/GlassCard'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { MapPin, Navigation, Car, Crown, AlertCircle, CreditCard, Wallet, Banknote, ShieldCheck, Leaf, Clock, TrendingUp, Info } from 'lucide-react'
import { requestRide } from './actions'
import { calculateRideEstimate, RideEstimate } from '@/utils/pricing'
import { SafeLeafletMap } from '@/components/maps/SafeLeafletMap'
import { generateIdempotencyKey } from '@/utils/idempotency'
import { nycLandmarks, Landmark } from '@/lib/locations/nycLandmarks'
import { useRouter } from 'next/navigation'

type LocationType = Landmark

export function RideBookingForm() {
  const router = useRouter()
  const [pickupInput, setPickupInput] = useState('')
  const [dropoffInput, setDropoffInput] = useState('')
  
  const [pickup, setPickup] = useState<LocationType | null>(null)
  const [dropoff, setDropoff] = useState<LocationType | null>(null)
  
  const [showPickupSuggestions, setShowPickupSuggestions] = useState(false)
  const [showDropoffSuggestions, setShowDropoffSuggestions] = useState(false)

  const [selectedClass, setSelectedClass] = useState<'economy' | 'comfort' | 'xl' | 'premium'>('economy')
  const [paymentMethod, setPaymentMethod] = useState<'demo_wallet' | 'mock_card' | 'cash' | 'manual'>('demo_wallet')
  
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  
  const [idempotencyKey, setIdempotencyKey] = useState<string>('')
  
  useEffect(() => {
    setIdempotencyKey(generateIdempotencyKey())
  }, [])

  const pickupSuggestions = pickupInput.length > 0 ? nycLandmarks.filter(loc => loc.name.toLowerCase().includes(pickupInput.toLowerCase())) : nycLandmarks
  const dropoffSuggestions = dropoffInput.length > 0 ? nycLandmarks.filter(loc => loc.name.toLowerCase().includes(dropoffInput.toLowerCase())) : nycLandmarks

  const estimate: RideEstimate | null = (pickup && dropoff) ? calculateRideEstimate(pickup.name, dropoff.name, pickup.zone) : null

  const mapCenter: [number, number] = pickup ? [pickup.lat, pickup.lng] : [40.7128, -74.0060]
  const mapMarkers = [
    ...(pickup ? [{ position: [pickup.lat, pickup.lng] as [number, number], label: 'Pickup' }] : []),
    ...(dropoff ? [{ position: [dropoff.lat, dropoff.lng] as [number, number], label: 'Dropoff' }] : [])
  ]
  const polyline: [number, number][] | undefined = (pickup && dropoff) ? [[pickup.lat, pickup.lng], [dropoff.lat, dropoff.lng]] : undefined

  async function handleAction() {
    if (!pickup || !dropoff || !estimate) return
    setError(null)
    setLoading(true)
    
    try {
      const formData = new FormData()
      formData.append('pickup', JSON.stringify({ address: pickup.name, lat: pickup.lat, lng: pickup.lng }))
      formData.append('dropoff', JSON.stringify({ address: dropoff.name, lat: dropoff.lat, lng: dropoff.lng }))
      formData.append('serviceClass', selectedClass)
      formData.append('paymentMethod', paymentMethod)
      formData.append('idempotencyKey', idempotencyKey)

      const result = await requestRide(formData)
      if (result?.error) {
        setError(result.error)
      } else if (result?.id) {
        setSuccess('Ride booked successfully! Redirecting...')
        setTimeout(() => {
          router.push(`/customer/rides/${result.id}`)
        }, 1500)
      }
    } catch (err) {
      console.error(err)
      setError('An unexpected error occurred while booking your ride. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid lg:grid-cols-2 gap-8 min-h-[calc(100vh-12rem)] pb-10">
      {/* Map Section */}
      <GlassCard className="relative overflow-hidden flex flex-col items-center justify-center p-1 h-[300px] lg:h-auto order-1 lg:order-none">
        <SafeLeafletMap center={mapCenter} markers={mapMarkers} polyline={polyline} height="100%" />
        {estimate && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 px-4 py-2 bg-background/90 backdrop-blur-md rounded-full shadow-lg text-sm font-bold flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
            </span>
            Routing: {estimate.distanceMiles} mi • ETA {estimate.durationMinutes} min
          </div>
        )}
      </GlassCard>

      {/* Booking Form */}
      <div className="flex flex-col h-full order-2 lg:order-none">
        <GlassCard className="p-6 flex-1 flex flex-col relative overflow-visible">
          <div className="space-y-4 mb-6">
            <div className="flex justify-between items-center mb-2">
              <h3 className="font-bold">Where to?</h3>
              <div className="text-xs text-muted-foreground flex gap-2">
                <span className="cursor-pointer hover:text-primary">Home</span>
                <span>•</span>
                <span className="cursor-pointer hover:text-primary">Work</span>
                <span>•</span>
                <span className="cursor-pointer hover:text-primary">Airport</span>
              </div>
            </div>

            {/* Pickup */}
            <div className="space-y-2 relative">
              <Label>Pickup Location</Label>
              <div className="relative">
                <MapPin className="absolute left-3 top-3 h-4 w-4 text-primary" />
                <Input 
                  className="pl-9 bg-background/50 h-12" 
                  placeholder="Where from? (e.g. JFK Airport)" 
                  value={pickupInput}
                  onChange={(e) => {
                    setPickupInput(e.target.value)
                    setPickup(null)
                    setShowPickupSuggestions(true)
                  }}
                  onFocus={() => setShowPickupSuggestions(true)}
                  onBlur={() => setTimeout(() => setShowPickupSuggestions(false), 200)}
                />
              </div>
              {showPickupSuggestions && pickupSuggestions.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-background border rounded-lg shadow-xl z-50 max-h-48 overflow-y-auto">
                  {pickupSuggestions.map(loc => (
                    <div 
                      key={loc.name}
                      className="p-3 hover:bg-muted cursor-pointer text-sm flex items-center gap-2"
                      onClick={() => {
                        setPickup(loc)
                        setPickupInput(loc.name)
                        setShowPickupSuggestions(false)
                      }}
                    >
                      <MapPin className="h-3 w-3 text-muted-foreground" /> {loc.name}
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            {/* Dropoff */}
            <div className="space-y-2 relative">
              <Label>Dropoff Location</Label>
              <div className="relative">
                <Navigation className="absolute left-3 top-3 h-4 w-4 text-destructive" />
                <Input 
                  className="pl-9 bg-background/50 h-12" 
                  placeholder="Where to? (e.g. Times Square)" 
                  value={dropoffInput}
                  onChange={(e) => {
                    setDropoffInput(e.target.value)
                    setDropoff(null)
                    setShowDropoffSuggestions(true)
                  }}
                  onFocus={() => setShowDropoffSuggestions(true)}
                  onBlur={() => setTimeout(() => setShowDropoffSuggestions(false), 200)}
                />
              </div>
              {showDropoffSuggestions && dropoffSuggestions.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-background border rounded-lg shadow-xl z-50 max-h-48 overflow-y-auto">
                  {dropoffSuggestions.map(loc => (
                    <div 
                      key={loc.name}
                      className="p-3 hover:bg-muted cursor-pointer text-sm flex items-center gap-2"
                      onClick={() => {
                        setDropoff(loc)
                        setDropoffInput(loc.name)
                        setShowDropoffSuggestions(false)
                      }}
                    >
                      <Navigation className="h-3 w-3 text-muted-foreground" /> {loc.name}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-destructive/10 border border-destructive text-destructive rounded-lg flex items-start gap-2 text-sm">
              <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
              <p>{error}</p>
            </div>
          )}

          {success && (
            <div className="mb-4 p-3 bg-green-500/10 border border-green-500 text-green-700 dark:text-green-400 rounded-lg flex items-start gap-2 text-sm">
              <ShieldCheck className="h-4 w-4 mt-0.5 shrink-0" />
              <p>{success}</p>
            </div>
          )}

          {/* Vehicle Selection & Intelligence */}
          <div className="flex-1 relative">
            {estimate ? (
              <div className="space-y-6 animate-in fade-in pb-4">
                {/* Advanced Intelligence Indicators */}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-primary/5 p-2 rounded-lg flex items-start gap-2 border border-primary/10">
                    <TrendingUp className="h-4 w-4 text-blue-500 mt-0.5" />
                    <div>
                      <p className="font-semibold text-foreground">Demand Score: {estimate.surgeMultiplier}x</p>
                      <p className="text-muted-foreground line-clamp-2">{estimate.fareExplanation}</p>
                    </div>
                  </div>
                  <div className="bg-primary/5 p-2 rounded-lg flex items-start gap-2 border border-primary/10">
                    <Clock className="h-4 w-4 text-green-500 mt-0.5" />
                    <div>
                      <p className="font-semibold text-foreground">Partner ETA: {estimate.nearestPartnerMinutes} min</p>
                      <p className="text-muted-foreground">Confidence: {estimate.confidenceScore}%</p>
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wider">Select a Ride</h3>
                  
                  {/* Vehicle Options */}
                  <div className="grid gap-3">
                    {[
                      { id: 'economy', name: 'Economy', icon: <Car className="h-5 w-5" />, color: 'bg-primary/20 text-primary', offset: 0 },
                      { id: 'comfort', name: 'Comfort', icon: <Car className="h-5 w-5" />, color: 'bg-blue-500/20 text-blue-500', offset: 2 },
                      { id: 'xl', name: 'XL (6 Seats)', icon: <Car className="h-5 w-5" />, color: 'bg-orange-500/20 text-orange-500', offset: 4 },
                      { id: 'premium', name: 'Premium', icon: <Crown className="h-5 w-5" />, color: 'bg-purple-500/20 text-purple-500', offset: 5 }
                    ].map(tier => {
                      const tierData = estimate.prices[tier.id as keyof typeof estimate.prices]
                      return (
                        <div 
                          key={tier.id}
                          onClick={() => setSelectedClass(tier.id as any)}
                          className={`p-3 rounded-xl border-2 cursor-pointer transition-all flex items-center justify-between ${selectedClass === tier.id ? 'border-primary bg-primary/5 shadow-sm' : 'border-border bg-muted/20 hover:bg-muted/50'}`}
                        >
                          <div className="flex items-center gap-3">
                            <div className={`p-2 rounded-full ${tier.color}`}>{tier.icon}</div>
                            <div>
                              <p className="font-bold leading-tight">{tier.name}</p>
                              <div className="text-xs text-muted-foreground flex items-center gap-1">
                                <span>{estimate.durationMinutes + tier.offset} mins away</span>
                                {tier.id === 'economy' && <span className="flex items-center text-green-600 dark:text-green-400 ml-1"><Leaf className="h-3 w-3 mr-0.5" /> {estimate.carbonEstimateKg}kg CO₂</span>}
                              </div>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="font-bold text-lg">${tierData.total.toFixed(2)}</p>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Fare Breakdown details */}
                <div className="bg-muted/30 p-3 rounded-lg border text-xs text-muted-foreground">
                  <div className="flex justify-between font-semibold mb-1 text-foreground"><span className="flex items-center"><Info className="h-3 w-3 mr-1" /> Fare Breakdown ({selectedClass})</span></div>
                  <div className="flex justify-between"><span>Base:</span> <span>${estimate.prices[selectedClass].base.toFixed(2)}</span></div>
                  <div className="flex justify-between"><span>Distance ({estimate.distanceMiles}mi):</span> <span>${estimate.prices[selectedClass].distance.toFixed(2)}</span></div>
                  <div className="flex justify-between"><span>Time ({estimate.durationMinutes}m):</span> <span>${estimate.prices[selectedClass].time.toFixed(2)}</span></div>
                  <div className="flex justify-between"><span>Platform Fee:</span> <span>${estimate.prices[selectedClass].platform.toFixed(2)}</span></div>
                  <div className="flex justify-between border-t border-border mt-1 pt-1"><span>Tax:</span> <span>${estimate.prices[selectedClass].tax.toFixed(2)}</span></div>
                </div>

                <div className="space-y-3">
                  <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wider">Payment</h3>
                  <div className="grid grid-cols-2 gap-2">
                    <Button type="button" variant={paymentMethod === 'demo_wallet' ? 'default' : 'outline'} className="justify-start text-xs" onClick={() => setPaymentMethod('demo_wallet')}>
                      <Wallet className="w-4 h-4 mr-2" /> Demo Wallet
                    </Button>
                    <Button type="button" variant={paymentMethod === 'mock_card' ? 'default' : 'outline'} className="justify-start text-xs" onClick={() => setPaymentMethod('mock_card')}>
                      <CreditCard className="w-4 h-4 mr-2" /> Mock Card
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-6 text-muted-foreground border-2 border-dashed rounded-xl border-border">
                <Navigation className="h-8 w-8 mb-4 opacity-50" />
                <p>Select your pickup and dropoff locations to see live estimates and vehicle options.</p>
              </div>
            )}
          </div>

          <div className="mt-4 pt-4 border-t bg-background">
            <Button 
              onClick={handleAction} 
              size="lg" 
              className="w-full text-lg h-14 rounded-xl shadow-lg"
              disabled={!estimate || loading || !pickup || !dropoff || !!success}
            >
              {loading ? 'Confirming...' : success ? 'Redirecting...' : (estimate ? `Request ${selectedClass.charAt(0).toUpperCase() + selectedClass.slice(1)}` : 'Enter Destinations')}
            </Button>
            <div className="text-center mt-3 text-xs text-muted-foreground flex items-center justify-center gap-1">
              <ShieldCheck className="h-3 w-3" /> All partners pass strict safety checks.
            </div>
          </div>
        </GlassCard>
      </div>
    </div>
  )
}
