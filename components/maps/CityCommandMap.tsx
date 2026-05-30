"use client"

import React, { useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Circle } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { MapMarkerLegend } from './MapMarkerLegend'

// NYC Coordinates
const NYC_CENTER: [number, number] = [40.7128, -74.0060]

// Create colored SVG marker icons
const createIcon = (color: string) => {
  return L.divIcon({
    className: 'custom-div-icon',
    html: `<div style="background-color: ${color}; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  })
}

const icons = {
  driver: createIcon('#3b82f6'), // blue-500
  ride: createIcon('#22c55e'),   // green-500
  eats: createIcon('#f97316'),   // orange-500
  grocery: createIcon('#a855f7'), // purple-500
  courier: createIcon('#06b6d4'), // cyan-500
  merchant: createIcon('#333333'), // dark
}

// Generate some random nearby coordinates
const getRandomOffset = () => (Math.random() - 0.5) * 0.04
const generateMarkers = (count: number, type: string) => {
  return Array.from({ length: count }).map((_, i) => ({
    id: `${type}-${i}`,
    position: [NYC_CENTER[0] + getRandomOffset(), NYC_CENTER[1] + getRandomOffset()] as [number, number],
    type
  }))
}

const activeDrivers = generateMarkers(8, 'driver')
const activeRides = generateMarkers(3, 'ride')
const eatsOrders = generateMarkers(4, 'eats')
const groceryOrders = generateMarkers(2, 'grocery')
const courierJobs = generateMarkers(2, 'courier')

const demandZones = [
  { center: [40.7580, -73.9855] as [number, number], radius: 800, intensity: 0.5 }, // Times Square
  { center: [40.7128, -74.0060] as [number, number], radius: 600, intensity: 0.3 }, // Financial District
  { center: [40.7306, -73.9866] as [number, number], radius: 1000, intensity: 0.4 }, // East Village
]

export default function CityCommandMap() {
  // Fix Leaflet's default icon path issues in React
  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore
    delete L.Icon.Default.prototype._getIconUrl
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
      iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
      shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    })
  }, [])

  return (
    <div className="relative w-full h-full rounded-xl overflow-hidden border">
      <MapContainer 
        center={NYC_CENTER} 
        zoom={13} 
        style={{ height: '100%', width: '100%', zIndex: 10 }}
        zoomControl={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        {/* Demand Zones */}
        {demandZones.map((zone, i) => (
          <Circle 
            key={`zone-${i}`}
            center={zone.center} 
            radius={zone.radius} 
            pathOptions={{ color: '#ef4444', fillColor: '#ef4444', fillOpacity: zone.intensity, weight: 0 }} 
          />
        ))}

        {/* Drivers */}
        {activeDrivers.map(marker => (
          <Marker key={marker.id} position={marker.position} icon={icons.driver}>
            <Popup>Active Driver</Popup>
          </Marker>
        ))}

        {/* Rides */}
        {activeRides.map(marker => (
          <Marker key={marker.id} position={marker.position} icon={icons.ride}>
            <Popup>Active Ride</Popup>
          </Marker>
        ))}

        {/* Eats */}
        {eatsOrders.map(marker => (
          <Marker key={marker.id} position={marker.position} icon={icons.eats}>
            <Popup>Eats Order</Popup>
          </Marker>
        ))}

        {/* Grocery */}
        {groceryOrders.map(marker => (
          <Marker key={marker.id} position={marker.position} icon={icons.grocery}>
            <Popup>Grocery Order</Popup>
          </Marker>
        ))}

        {/* Courier */}
        {courierJobs.map(marker => (
          <Marker key={marker.id} position={marker.position} icon={icons.courier}>
            <Popup>Courier Job</Popup>
          </Marker>
        ))}
      </MapContainer>
      
      <MapMarkerLegend />
    </div>
  )
}
