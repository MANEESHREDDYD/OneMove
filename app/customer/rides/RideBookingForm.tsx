'use client'

import { useState, useEffect } from 'react'
import { GlassCard } from '@/components/common/GlassCard'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { MapPin, Navigation, Car, Crown, AlertCircle, CreditCard, Wallet, Banknote } from 'lucide-react'
import { requestRide } from './actions'
import { calculateRideEstimate } from '@/utils/pricing'
import { SafeLeafletMap } from '@/components/maps/SafeLeafletMap'
import { generateIdempotencyKey } from '@/utils/idempotency'
import { nycLandmarks, Landmark } from '@/lib/locations/nycLandmarks'

type LocationType = Landmark

export function RideBookingForm() {
  const [pickupInput, setPickupInput] = useState('')
  const [dropoffInput, setDropoffInput] = useState('')
  
  const [pickup, setPickup] = useState<LocationType | null>(null)
  const [dropoff, setDropoff] = useState<LocationType | null>(null)
  
  const [showPickupSuggestions, setShowPickupSuggestions] = useState(false)
  const [showDropoffSuggestions, setShowDropoffSuggestions] = useState(false)

  const [selectedClass, setSelectedClass] = useState<'economy' | 'premium'>('economy')
  const [paymentMethod, setPaymentMethod] = useState<'demo_wallet' | 'mock_card' | 'cash' | 'manual'>('demo_wallet')
  
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const [idempotencyKey, setIdempotencyKey] = useState<string>('')
  
  // Generate key on mount
  useEffect(() => {
    setIdempotencyKey(generateIdempotencyKey())
  }, [])

  const pickupSuggestions = pickupInput.length > 0 ? nycLandmarks.filter(loc => loc.name.toLowerCase().includes(pickupInput.toLowerCase())) : nycLandmarks
  const dropoffSuggestions = dropoffInput.length > 0 ? nycLandmarks.filter(loc => loc.name.toLowerCase().includes(dropoffInput.toLowerCase())) : nycLandmarks

  const estimate = (pickup && dropoff) ? calculateRideEstimate(pickup.name, dropoff.name) : null

  const mapCenter: [number, number] = pickup ? [pickup.lat, pickup.lng] : [40.7128, -74.0060]
  const mapMarkers = [
    ...(pickup ? [{ position: [pickup.lat, pickup.lng] as [number, number], label: 'Pickup' }] : []),
    ...(dropoff ? [{ position: [dropoff.lat, dropoff.lng] as [number, number], label: 'Dropoff' }] : [])
  ]

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
      <GlassCard className="relative overflow-hidden hidden lg:flex flex-col items-center justify-center p-1">
        <SafeLeafletMap center={mapCenter} markers={mapMarkers} height="100%" />
        {estimate && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 px-4 py-2 bg-background/90 backdrop-blur-md rounded-full shadow-lg text-sm font-bold flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
            </span>
            Routing: {estimate.distanceMiles} mi • {estimate.durationMinutes} min
          </div>
        )}
      </GlassCard>

      {/* Booking Form */}
      <div className="flex flex-col h-full">
        <GlassCard className="p-6 flex-1 flex flex-col relative overflow-visible">
          <div className="space-y-4 mb-6">
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

          {/* Vehicle Selection & Payment */}
          <div className="flex-1 relative">
            {estimate ? (
              <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 pb-4">
                <div className="space-y-3">
                  <h3 className="font-semibold text-lg">Select a Ride</h3>
                  
                  {/* Economy */}
                  <div 
                    onClick={() => setSelectedClass('economy')}
                    className={`p-4 rounded-xl border-2 cursor-pointer transition-all flex items-center justify-between ${selectedClass === 'economy' ? 'border-primary bg-primary/10' : 'border-transparent bg-muted/50 hover:bg-muted'}`}
                  >
                    <div className="flex items-center gap-4">
                      <div className="bg-primary/20 p-2 rounded-full"><Car className="h-6 w-6 text-primary" /></div>
                      <div>
                        <p className="font-bold">OneMove Economy</p>
                        <p className="text-xs text-muted-foreground">{estimate.durationMinutes} mins away</p>
                      </div>
                    </div>
                    <p className="font-bold text-lg">${estimate.prices.economy.toFixed(2)}</p>
                  </div>

                  {/* Premium */}
                  <div 
                    onClick={() => setSelectedClass('premium')}
                    className={`p-4 rounded-xl border-2 cursor-pointer transition-all flex items-center justify-between ${selectedClass === 'premium' ? 'border-primary bg-primary/10' : 'border-transparent bg-muted/50 hover:bg-muted'}`}
                  >
                    <div className="flex items-center gap-4">
                      <div className="bg-purple-500/20 p-2 rounded-full"><Crown className="h-6 w-6 text-purple-500" /></div>
                      <div>
                        <p className="font-bold">OneMove Premium</p>
                        <p className="text-xs text-muted-foreground">{estimate.durationMinutes + 2} mins away</p>
                      </div>
                    </div>
                    <p className="font-bold text-lg">${estimate.prices.premium.toFixed(2)}</p>
                  </div>
                </div>

                <div className="space-y-3">
                  <h3 className="font-semibold text-lg">Payment Method</h3>
                  <div className="grid grid-cols-2 gap-2">
                    <Button type="button" variant={paymentMethod === 'demo_wallet' ? 'default' : 'outline'} className="justify-start text-xs" onClick={() => setPaymentMethod('demo_wallet')}>
                      <Wallet className="w-4 h-4 mr-2" /> Demo Wallet
                    </Button>
                    <Button type="button" variant={paymentMethod === 'mock_card' ? 'default' : 'outline'} className="justify-start text-xs" onClick={() => setPaymentMethod('mock_card')}>
                      <CreditCard className="w-4 h-4 mr-2" /> Mock Card
                    </Button>
                    <Button type="button" variant={paymentMethod === 'cash' ? 'default' : 'outline'} className="justify-start text-xs" onClick={() => setPaymentMethod('cash')}>
                      <Banknote className="w-4 h-4 mr-2" /> Cash
                    </Button>
                    <Button type="button" variant={paymentMethod === 'manual' ? 'default' : 'outline'} className="justify-start text-xs" onClick={() => setPaymentMethod('manual')}>
                      <AlertCircle className="w-4 h-4 mr-2" /> Manual
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-6 text-muted-foreground border-2 border-dashed rounded-xl border-border">
                <Navigation className="h-8 w-8 mb-4 opacity-50" />
                <p>Select your pickup and dropoff locations to see live estimates.</p>
              </div>
            )}
          </div>

          <div className="mt-6 pt-6 border-t">
            <Button 
              onClick={handleAction} 
              size="lg" 
              className="w-full text-lg h-14 rounded-xl"
              disabled={!estimate || loading || !pickup || !dropoff}
            >
              {loading ? 'Booking...' : (estimate ? `Confirm ${selectedClass === 'economy' ? 'Economy' : 'Premium'}` : 'Enter Destinations')}
            </Button>
          </div>
        </GlassCard>
      </div>
    </div>
  )
}
