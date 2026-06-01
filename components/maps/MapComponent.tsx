'use client'

import { useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Circle } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'

// Fix missing marker icons
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Custom DivIcons
const createIcon = (color: string) => new L.DivIcon({
  className: 'custom-div-icon',
  html: `<div style="background-color: ${color}; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 4px rgba(0,0,0,0.5);"></div>`,
  iconSize: [14, 14],
  iconAnchor: [7, 7]
})

const driverIcon = createIcon('#3b82f6') // Blue
const orderIcon = createIcon('#10b981')  // Green
const merchantIcon = createIcon('#f59e0b') // Orange

export default function MapComponent({ 
  orders = [], 
  merchants = [] 
}: { 
  orders?: any[],
  merchants?: any[]
}) {
  const center: [number, number] = [40.7128, -74.0060] // NYC
  
  // Create some simulated driver markers near NYC
  const drivers = Array.from({ length: 15 }).map((_, i) => ({
    id: `drv-${i}`,
    lat: 40.7128 + (Math.random() - 0.5) * 0.05,
    lng: -74.0060 + (Math.random() - 0.5) * 0.05,
    status: Math.random() > 0.5 ? 'online' : 'busy'
  }))

  return (
    <div style={{ height: '100%', width: '100%', minHeight: '400px' }}>
      <MapContainer center={center} zoom={13} style={{ height: '100%', width: '100%' }} zoomControl={false}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/">OSM</a>'
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        />
        
        {/* Demand Zones */}
        <Circle center={[40.7580, -73.9855]} radius={800} pathOptions={{ color: '#ef4444', fillColor: '#ef4444', fillOpacity: 0.2 }} />
        <Circle center={[40.7128, -74.0060]} radius={500} pathOptions={{ color: '#f97316', fillColor: '#f97316', fillOpacity: 0.2 }} />

        {/* Drivers */}
        {drivers.map(drv => (
          <Marker key={drv.id} position={[drv.lat, drv.lng]} icon={driverIcon}>
            <Popup>Driver {drv.id.split('-')[1]} ({drv.status})</Popup>
          </Marker>
        ))}

        {/* Merchants */}
        {merchants.slice(0, 20).map(m => (
          <Marker key={m.id} position={[40.7128 + (Math.random() - 0.5) * 0.04, -74.0060 + (Math.random() - 0.5) * 0.04]} icon={merchantIcon}>
            <Popup>{m.name} ({m.category})</Popup>
          </Marker>
        ))}

        {/* Active Orders */}
        {orders.filter(o => o.status !== 'completed' && o.status !== 'cancelled').slice(0, 10).map((o, i) => (
          <Marker key={o.id} position={[40.7128 + (Math.random() - 0.5) * 0.03, -74.0060 + (Math.random() - 0.5) * 0.03]} icon={orderIcon}>
            <Popup>Order: {o.service_type}<br/>Status: {o.status}</Popup>
          </Marker>
        ))}
        
      </MapContainer>
      
      {/* Legend */}
      <div className="absolute bottom-4 right-4 bg-background/90 backdrop-blur p-3 rounded-lg border shadow-lg z-[1000] text-xs">
        <div className="flex items-center gap-2 mb-1">
           <div className="w-3 h-3 rounded-full bg-blue-500 border border-white shadow-sm"></div>
           <span>Active Driver</span>
        </div>
        <div className="flex items-center gap-2 mb-1">
           <div className="w-3 h-3 rounded-full bg-green-500 border border-white shadow-sm"></div>
           <span>Live Order</span>
        </div>
        <div className="flex items-center gap-2 mb-1">
           <div className="w-3 h-3 rounded-full bg-orange-500 border border-white shadow-sm"></div>
           <span>Merchant</span>
        </div>
        <div className="flex items-center gap-2">
           <div className="w-3 h-3 rounded-full bg-red-500 opacity-40"></div>
           <span>High Demand</span>
        </div>
      </div>
    </div>
  )
}
