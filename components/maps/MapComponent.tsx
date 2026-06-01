'use client'

import { useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Circle } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'

// Fix Leaflet's default icon path issues in Next.js
// eslint-disable-next-line @typescript-eslint/no-explicit-any
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const createIcon = (color: string) => {
  return new L.Icon({
    iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${color}.png`,
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
  });
}

const driverIcon = createIcon('blue');
const merchantIcon = createIcon('red');
const orderIcon = createIcon('green');

export default function MapComponent({ 
  orders = [], 
  merchants = [] 
}: { 
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  orders?: any[], 
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  merchants?: any[] 
}) {
  const [position] = useState<[number, number]>([40.7128, -74.0060]) // Default NY

  const drivers = Array.from({ length: 15 }).map((_, i) => ({
    id: `drv-${i}`,
    lat: 40.7128 + ((i % 10) - 5) * 0.005,
    lng: -74.0060 + (((i+5) % 10) - 5) * 0.005,
    status: (i % 2 === 0) ? 'online' : 'busy'
  }))

  return (
    <div style={{ height: '100%', width: '100%', minHeight: '400px' }}>
      <MapContainer center={position} zoom={13} style={{ height: '100%', width: '100%' }} zoomControl={false}>
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
        {merchants.map((m, i) => (
          <Marker key={m.id} position={[40.7128 + ((i % 10) - 5) * 0.004, -74.0060 + (((i+3) % 10) - 5) * 0.004]} icon={merchantIcon}>
            <Popup>{m.name} ({m.category})</Popup>
          </Marker>
        ))}

        {/* Active Orders */}
        {orders.map((o, i) => (
          <Marker key={o.id} position={[40.7128 + ((i % 10) - 5) * 0.003, -74.0060 + (((i+2) % 10) - 5) * 0.003]} icon={orderIcon}>
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
