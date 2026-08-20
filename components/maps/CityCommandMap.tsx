"use client"

import React, { useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Circle } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { MapMarkerLegend } from './MapMarkerLegend'

/**
 * City command map.
 *
 * This component previously synthesised its own contents: 19 markers (drivers, rides,
 * eats/grocery/courier jobs) were placed at `Math.random()` offsets around NYC and three
 * demand zones were hard-coded, so an operator would have read fabricated fleet positions
 * as live ones. It is now purely presentational — it renders only what a caller supplies
 * from a real source, and states plainly when it has been given nothing.
 */

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

export type FleetMarkerType = keyof typeof icons

export type FleetMarker = {
  id: string
  position: [number, number]
  type: FleetMarkerType
  label: string
}

export type DemandZone = {
  id: string
  center: [number, number]
  /** metres */
  radius: number
  /** 0-1 fill opacity, must come from a measured demand figure */
  intensity: number
}

export type CityCommandMapProps = {
  /** Live entity positions from a real source. Omit when no source is connected. */
  markers?: FleetMarker[]
  /** Measured demand zones from a real source. Omit when no source is connected. */
  demandZones?: DemandZone[]
  center?: [number, number]
  zoom?: number
}

export default function CityCommandMap({
  markers,
  demandZones,
  center = NYC_CENTER,
  zoom = 13,
}: CityCommandMapProps) {
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

  const hasLiveData = markers !== undefined || demandZones !== undefined

  return (
    <div className="relative w-full h-full rounded-xl overflow-hidden border">
      <MapContainer
        center={center}
        zoom={zoom}
        style={{ height: '100%', width: '100%', zIndex: 10 }}
        zoomControl={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {demandZones?.map((zone) => (
          <Circle
            key={zone.id}
            center={zone.center}
            radius={zone.radius}
            pathOptions={{
              color: '#ef4444',
              fillColor: '#ef4444',
              fillOpacity: zone.intensity,
              weight: 0,
            }}
          />
        ))}

        {markers?.map((marker) => (
          <Marker key={marker.id} position={marker.position} icon={icons[marker.type]}>
            <Popup>{marker.label}</Popup>
          </Marker>
        ))}
      </MapContainer>

      {!hasLiveData && (
        <div className="absolute inset-0 z-[500] flex items-center justify-center bg-background/80 backdrop-blur-sm text-center p-6">
          <div className="space-y-1">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">
              Live Positions Unavailable
            </p>
            <p className="text-sm text-muted-foreground max-w-xs">
              No fleet telemetry source is connected to this map.
            </p>
          </div>
        </div>
      )}

      <MapMarkerLegend />
    </div>
  )
}
