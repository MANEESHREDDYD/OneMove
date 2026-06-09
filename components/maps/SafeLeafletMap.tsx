'use client'

import { useEffect, useState } from 'react'
import dynamic from 'next/dynamic'
import { MapPin, AlertCircle } from 'lucide-react'
import 'leaflet/dist/leaflet.css'

// Only load Leaflet on the client side to avoid _leaflet_pos runtime crashes during SSR
const MapContainer = dynamic(
  () => import('react-leaflet').then((mod) => mod.MapContainer),
  { ssr: false }
)
const TileLayer = dynamic(
  () => import('react-leaflet').then((mod) => mod.TileLayer),
  { ssr: false }
)
const Marker = dynamic(
  () => import('react-leaflet').then((mod) => mod.Marker),
  { ssr: false }
)
const Polyline = dynamic(
  () => import('react-leaflet').then((mod) => mod.Polyline),
  { ssr: false }
)

const ResizeMapOnMount = dynamic(
  () => import('react-leaflet').then(mod => {
    return function ResizeMapOnMount() {
      const map = mod.useMap()
      useEffect(() => {
        const timeout = setTimeout(() => {
          map.invalidateSize()
        }, 150)
        return () => clearTimeout(timeout)
      }, [map])
      return null
    }
  }),
  { ssr: false }
)

type SafeLeafletMapProps = {
  center: [number, number]
  zoom?: number
  markers?: Array<{ position: [number, number]; label?: string }>
  polyline?: [number, number][]
  height?: string
}

export function SafeLeafletMap({ center, zoom = 13, markers = [], polyline, height = '400px' }: SafeLeafletMapProps) {
  const [mounted, setMounted] = useState(false)
  const [mapError, setMapError] = useState(false)

  useEffect(() => {
    setMounted(true)
    // Safely configure Leaflet icons on the client side
    import('leaflet').then((L) => {
      delete (L.Icon.Default.prototype as any)._getIconUrl
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
      })
    }).catch(e => {
      console.error('Failed to load Leaflet', e)
      setMapError(true)
    })
  }, [])

  if (!mounted) {
    return (
      <div 
        style={{ height }} 
        className="w-full bg-muted/50 rounded-xl flex items-center justify-center border border-primary/10 animate-pulse"
      >
        <MapPin className="w-8 h-8 text-muted-foreground opacity-50" />
      </div>
    )
  }

  if (mapError) {
    return (
      <div 
        style={{ height }} 
        className="w-full bg-muted/50 rounded-xl flex flex-col items-center justify-center border border-destructive/20 text-muted-foreground p-6 text-center"
      >
        <AlertCircle className="w-8 h-8 text-destructive mb-2 opacity-50" />
        <p className="text-sm">Map rendering failed. Operating in fallback mode.</p>
      </div>
    )
  }

  // Ensure coordinates are valid numbers to prevent leaflet crashes
  const validCenter = (typeof center[0] === 'number' && typeof center[1] === 'number' && !isNaN(center[0]) && !isNaN(center[1])) 
    ? center 
    : [40.7128, -74.0060] as [number, number]

  const validMarkers = markers.filter(m => 
    typeof m.position[0] === 'number' && typeof m.position[1] === 'number' && 
    !isNaN(m.position[0]) && !isNaN(m.position[1])
  )

  return (
    <div style={{ height }} className="w-full rounded-xl overflow-hidden border border-primary/20 relative z-0">
      <style dangerouslySetInnerHTML={{__html: `
        .leaflet-container { width: 100%; height: 100%; z-index: 1; }
        .leaflet-pane { z-index: 1; }
        .leaflet-top, .leaflet-bottom { z-index: 10; }
      `}} />
      <MapContainer 
        center={validCenter} 
        zoom={zoom} 
        scrollWheelZoom={false}
        className="w-full h-full"
      >
        <ResizeMapOnMount />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        />
        {validMarkers.map((marker, i) => (
          <Marker key={i} position={marker.position} />
        ))}
        {polyline && polyline.length > 0 && (
          <Polyline positions={polyline} color="#2563eb" weight={4} opacity={0.7} />
        )}
      </MapContainer>
    </div>
  )
}
